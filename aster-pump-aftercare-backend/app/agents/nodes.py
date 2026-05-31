import logging
import json
import re
from typing import Any

import httpx

from app.agents.state import AftercareState
from app.config import settings
from app.mcp.client import AftercareMcpClient
from app.rag.service import rag_service


def advance_workflow_step(state: AftercareState, node_name: str) -> AftercareState:
    """Increment workflow step counters and stop runaway graphs."""

    step_count = state.get("workflow_step_count", 0) + 1
    if step_count > settings.max_workflow_steps:
        raise ValueError(
            f"Workflow stopped after exceeding max steps "
            f"({settings.max_workflow_steps}). Trace: {state.get('workflow_trace', [])}"
        )

    trace = [*state.get("workflow_trace", []), node_name]
    logging.info(
        "workflow-guard | step=%s/%s node=%s trace=%s",
        step_count,
        settings.max_workflow_steps,
        node_name,
        trace,
    )
    return {**state, "workflow_step_count": step_count, "workflow_trace": trace}


ALLOWED_AGENT_TOOLS = {
    "image_customer_service": {"analyze_image", "create_ticket"},
    "text_customer_service": {"create_ticket"},
    "technical_assistant": {"rag_search", "update_technical_steps"},
    "reply_agent": {"send_customer_email"},
}


class ModelPlannerAgent:
    """Uses the local model to propose a workflow plan as JSON."""

    async def __call__(self, state: AftercareState) -> AftercareState:
        state = advance_workflow_step(state, "model_planner")
        description = state.get("description", "").strip()
        has_image = bool(state.get("image_bytes"))
        has_text = bool(description)

        if not has_image and not has_text:
            raise ValueError("Request must include an image, text description, or both.")

        logging.info(
            "story.planner | start model planning has_image=%s has_text=%s description=%r image_filename=%s image_bytes=%s image_content_type=%s",
            has_image,
            has_text,
            description,
            state.get("image_filename", ""),
            len(state.get("image_bytes", b"")),
            state.get("image_content_type", ""),
        )
        plan = await self.request_model_plan(
            description=description,
            has_image=has_image,
            has_text=has_text,
        )
        logging.info(
            "story.planner | model plan normalized intent=%s plan_id=%s steps=%s reason=%r full_plan=%s",
            plan.get("intent"),
            plan.get("plan_id"),
            [step.get("agent") for step in plan.get("steps", []) if isinstance(step, dict)],
            plan.get("reason", ""),
            json.dumps(plan),
        )
        return {
            **state,
            "model_plan": plan,
            "planner_source": "ollama",
            "has_image": has_image,
            "has_text": has_text,
            "status": "planned",
        }

    async def request_model_plan(self, description: str, has_image: bool, has_text: bool) -> dict[str, Any]:
        """Ask Ollama to choose a workflow plan, then normalize it."""

        selected_plan_id = "image_ticket" if has_image else "text_ticket"
        logging.info(
            "story.planner | selected expected plan id before model call selected_plan_id=%s description=%r",
            selected_plan_id,
            description,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a workflow planner for an aftercare support system. "
                    "Return JSON only. Do not use markdown. "
                    "Your job is to choose exactly one approved plan_id from the backend catalog. "
                    "Do not invent plan ids, agents, or tools. "
                    "Return only this shape: "
                    "{\"intent\":\"open_ticket\",\"plan_id\":\"image_ticket or text_ticket\",\"reason\":\"short reason\"}."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task": "Create a workflow plan for opening one aftercare ticket.",
                        "has_image": has_image,
                        "has_text": has_text,
                        "description": description,
                        "valid_plan_ids": {
                            "image_ticket": "Use when the request includes an image. The backend will analyze the image, create a ticket, retrieve RAG steps, and send email.",
                            "text_ticket": "Use when the request has text and no image. The backend will create a ticket from text, retrieve RAG steps, and send email.",
                        },
                        "selected_plan_id_to_return": selected_plan_id,
                    }
                ),
            },
        ]

        model_request = {
            "model": settings.model_name,
            "stream": False,
            "think": False,
            "format": "json",
            "options": {
                "temperature": 0,
                "num_predict": 256,
                "num_ctx": 2048,
            },
            "messages": messages,
        }
        logging.info(
            "story.planner | sending request to Ollama url=%s model=%s payload=%s",
            f"{settings.model_base_url}/api/chat",
            settings.model_name,
            json.dumps(model_request),
        )

        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                response = await client.post(f"{settings.model_base_url}/api/chat", json=model_request)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"Planner model returned HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Planner model is unavailable: {exc}") from exc

        content = response.json().get("message", {}).get("content", "")
        logging.info("story.planner | Ollama replied with raw plan content=%r", content)
        return self.parse_plan_json(content, has_image=has_image)

    def parse_plan_json(self, content: str, has_image: bool) -> dict[str, Any]:
        """Parse strict JSON, with a small fallback for accidental surrounding text."""

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise ValueError("Planner model did not return JSON.")
            parsed = json.loads(content[start : end + 1])

        if not isinstance(parsed, dict):
            raise ValueError("Planner model returned JSON that is not an object.")
        logging.info("story.planner | parsed model JSON=%s", json.dumps(parsed))
        return self.normalize_model_plan(parsed, has_image=has_image)

    def normalize_model_plan(self, parsed: dict[str, Any], has_image: bool) -> dict[str, Any]:
        """Convert a model-selected plan id into a canonical backend plan."""

        nested_plan = parsed.get("selected_plan_to_return")
        if isinstance(nested_plan, dict):
            logging.info("story.planner | model returned nested selected_plan_to_return=%s", json.dumps(nested_plan))
            parsed = nested_plan

        if isinstance(parsed.get("steps"), list):
            logging.info("story.planner | model returned executable steps directly=%s", json.dumps(parsed))
            return parsed

        plan_id = parsed.get("plan_id") or parsed.get("selected_plan_id_to_return")
        if plan_id not in {"image_ticket", "text_ticket"} and parsed.get("intent") == "open_ticket":
            plan_id = "image_ticket" if has_image else "text_ticket"

        if plan_id not in {"image_ticket", "text_ticket"}:
            raise ValueError(f"Planner model returned unsupported plan_id: {plan_id}")

        expected_plan_id = "image_ticket" if has_image else "text_ticket"
        if plan_id != expected_plan_id:
            raise ValueError(f"Planner model selected {plan_id}, expected {expected_plan_id}.")

        canonical = self.canonical_plan(plan_id=plan_id, reason=str(parsed.get("reason", "")))
        logging.info("story.planner | expanded plan_id=%s to canonical_plan=%s", plan_id, json.dumps(canonical))
        return canonical

    def canonical_plan(self, plan_id: str, reason: str) -> dict[str, Any]:
        """Return the exact executable plan template for an approved plan id."""

        if plan_id == "image_ticket":
            return {
                "intent": "open_ticket",
                "plan_id": plan_id,
                "reason": reason or "The request includes an image, so image analysis is required.",
                "steps": [
                    {"agent": "image_customer_service", "tools": ["analyze_image", "create_ticket"]},
                    {"agent": "technical_assistant", "tools": ["rag_search", "update_technical_steps"]},
                    {"agent": "reply_agent", "tools": ["send_customer_email"]},
                ],
            }

        return {
            "intent": "open_ticket",
            "plan_id": plan_id,
            "reason": reason or "The request has text and no image, so text intake is enough.",
            "steps": [
                {"agent": "text_customer_service", "tools": ["create_ticket"]},
                {"agent": "technical_assistant", "tools": ["rag_search", "update_technical_steps"]},
                {"agent": "reply_agent", "tools": ["send_customer_email"]},
            ],
        }


class PlanValidatorAgent:
    """Validates the model-generated plan before any worker agent runs."""

    def __call__(self, state: AftercareState) -> AftercareState:
        state = advance_workflow_step(state, "plan_validator")
        route_count = state.get("supervisor_route_count", 0) + 1
        if route_count > settings.max_supervisor_routes:
            raise ValueError(
                f"Plan validator stopped after exceeding max route decisions "
                f"({settings.max_supervisor_routes})."
            )

        plan = state.get("model_plan", {})
        logging.info("story.validator | validating model plan=%s", json.dumps(plan) if isinstance(plan, dict) else plan)
        steps = plan.get("steps") if isinstance(plan, dict) else None
        if not isinstance(steps, list) or not steps:
            raise ValueError("Planner model returned a plan with no steps.")

        planned_steps: list[str] = []
        planned_tools: list[str] = []
        for step in steps:
            if not isinstance(step, dict):
                raise ValueError("Planner step must be an object.")
            agent = step.get("agent")
            tools = step.get("tools", [])
            if not isinstance(agent, str) or agent not in ALLOWED_AGENT_TOOLS:
                raise ValueError(f"Planner selected unsupported agent: {agent}")
            if not isinstance(tools, list) or not all(isinstance(tool, str) for tool in tools):
                raise ValueError(f"Planner selected invalid tools for agent: {agent}")
            unsupported_tools = set(tools) - ALLOWED_AGENT_TOOLS[agent]
            if unsupported_tools:
                raise ValueError(f"Planner selected unsupported tools for {agent}: {sorted(unsupported_tools)}")
            planned_steps.append(agent)
            planned_tools.extend(tools)

        required_first_agent = "image_customer_service" if state.get("has_image") else "text_customer_service"
        required_steps = [required_first_agent, "technical_assistant", "reply_agent"]
        if planned_steps != required_steps:
            raise ValueError(f"Planner selected invalid step order: {planned_steps}. Expected: {required_steps}")

        if len(planned_steps) + state.get("workflow_step_count", 0) > settings.max_workflow_steps:
            raise ValueError(
                f"Planner selected too many steps ({len(planned_steps)}) for max workflow steps "
                f"({settings.max_workflow_steps})."
            )

        route = "image_intake" if required_first_agent == "image_customer_service" else "text_intake"
        logging.info(
            "story.validator | approved route=%s steps=%s tools=%s route_count=%s/%s reason=%r",
            route,
            planned_steps,
            planned_tools,
            route_count,
            settings.max_supervisor_routes,
            plan.get("reason", "") if isinstance(plan, dict) else "",
        )
        return {
            **state,
            "intake_route": route,
            "supervisor_route_count": route_count,
            "planned_steps": planned_steps,
            "planned_tools": planned_tools,
            "plan_reason": str(plan.get("reason", "")) if isinstance(plan, dict) else "",
            "plan_validation_status": "approved",
            "status": "routed",
        }


class CustomerServiceAgent:
    """Analyzes an uploaded image and opens the support ticket."""

    def __init__(self, mcp_client: AftercareMcpClient) -> None:
        self.mcp_client = mcp_client

    async def __call__(self, state: AftercareState) -> AftercareState:
        state = advance_workflow_step(state, "image_customer_service")
        logging.info(
            "story.image_customer_service | start image intake email=%s description=%r image_filename=%s image_bytes=%s image_content_type=%s",
            state["customer_email"],
            state.get("description", ""),
            state.get("image_filename", ""),
            len(state.get("image_bytes", b"")),
            state.get("image_content_type", ""),
        )
        detected_objects = await self.mcp_client.analyze_image(
            state["image_filename"],
            state["image_bytes"],
            state.get("image_content_type"),
        )
        logging.info("story.image_customer_service | image analyzer returned detected_objects=%s", detected_objects)
        ticket = await self.mcp_client.create_ticket(
            customer_email=state["customer_email"],
            description=state.get("description", ""),
            detected_objects=detected_objects,
        )
        logging.info(
            "story.image_customer_service | ticket created ticket_id=%s status=%s detected=%s error_code=%s description=%r",
            ticket["id"],
            ticket.get("status"),
            detected_objects,
            ticket.get("detected_error_code"),
            ticket.get("description", ""),
        )
        return {
            **state,
            "detected_objects": detected_objects,
            "detected_error_code": ticket.get("detected_error_code"),
            "ticket_id": ticket["id"],
            "status": ticket["status"],
        }


class TextCustomerServiceAgent:
    """Creates a ticket from text-only customer input without image analysis."""

    ERROR_PATTERN = re.compile(r"E-?(\d{2,3})(?!\d)", re.IGNORECASE)

    def __init__(self, mcp_client: AftercareMcpClient) -> None:
        self.mcp_client = mcp_client

    async def __call__(self, state: AftercareState) -> AftercareState:
        state = advance_workflow_step(state, "text_customer_service")
        description = state.get("description", "")
        detected_objects = self.detect_text_objects(description)
        logging.info(
            "story.text_customer_service | start text intake email=%s description=%r detected_objects=%s",
            state["customer_email"],
            description,
            detected_objects,
        )
        ticket = await self.mcp_client.create_ticket(
            customer_email=state["customer_email"],
            description=description,
            detected_objects=detected_objects,
        )
        logging.info(
            "story.text_customer_service | ticket created ticket_id=%s status=%s error_code=%s description=%r",
            ticket["id"],
            ticket.get("status"),
            ticket.get("detected_error_code"),
            ticket.get("description", ""),
        )
        return {
            **state,
            "detected_objects": detected_objects,
            "detected_error_code": ticket.get("detected_error_code"),
            "ticket_id": ticket["id"],
            "status": ticket["status"],
        }

    def detect_text_objects(self, text: str) -> list[str]:
        """Extract simple product/error labels from a text-only request."""

        objects: list[str] = []
        normalized = text.lower()
        if "asterpump" in normalized or "x17" in normalized:
            objects.append("AsterPump X17")

        for match in self.ERROR_PATTERN.finditer(text):
            digits = re.sub(r"\D", "", match.group(0))
            code = f"E-{digits}"
            if code not in objects:
                objects.append(code)

        return objects or ["text_request"]


class TechnicalAssistantAgent:
    """Uses RAG to produce troubleshooting steps for the detected issue."""

    def __init__(self, mcp_client: AftercareMcpClient) -> None:
        self.mcp_client = mcp_client

    async def __call__(self, state: AftercareState) -> AftercareState:
        state = advance_workflow_step(state, "technical_assistant")
        issue_terms = ", ".join(state.get("detected_objects", []))
        logging.info(
            "story.technical_assistant | start technical lookup ticket_id=%s issue_terms=%r customer_description=%r",
            state["ticket_id"],
            issue_terms,
            state.get("description", ""),
        )
        question = (
            f"Provide after-purchase troubleshooting steps for {issue_terms}. "
            f"Customer description: {state.get('description', '')}"
        )
        logging.info("story.technical_assistant | sending RAG question=%r", question)
        rag_result = rag_service.retrieve_for_question(question)
        logging.info(
            "story.technical_assistant | RAG returned sources=%s context=%r",
            rag_result.sources,
            rag_result.context,
        )

        if rag_result.context:
            technical_steps = (
                "Based on the product manual:\n"
                f"{self.summarize_context_for_customer(rag_result.context)}"
            )
        else:
            technical_steps = (
                "No matching manual entry was found. Please confirm the displayed error code "
                "and contact Level 2 support."
            )

        await self.mcp_client.update_technical_steps(state["ticket_id"], technical_steps)
        logging.info(
            "story.technical_assistant | stored technical steps ticket_id=%s context_found=%s technical_steps=%r",
            state["ticket_id"],
            bool(rag_result.context),
            technical_steps,
        )
        return {**state, "technical_steps": technical_steps, "status": "technical_steps_added"}

    def summarize_context_for_customer(self, context: str) -> str:
        """Extract compact customer-facing steps from retrieved RAG context."""

        lines = [
            line.strip()
            for line in context.replace("---", "\n").splitlines()
            if line.strip() and not line.startswith("Source:")
        ]
        return "\n".join(f"- {line}" for line in lines[:5])


class ReplyAgent:
    """Formats and sends the final customer reply through the MCP tool server."""

    def __init__(self, mcp_client: AftercareMcpClient) -> None:
        self.mcp_client = mcp_client

    async def __call__(self, state: AftercareState) -> AftercareState:
        state = advance_workflow_step(state, "reply_agent")
        logging.info(
            "story.reply_agent | preparing customer email ticket_id=%s to=%s technical_steps=%r",
            state["ticket_id"],
            state["customer_email"],
            state.get("technical_steps", ""),
        )
        subject = f"Support ticket #{state['ticket_id']} troubleshooting steps"
        body = (
            f"Hello,\n\n"
            f"We created ticket #{state['ticket_id']} for your product issue.\n\n"
            f"Detected from your request: {', '.join(state.get('detected_objects', []))}\n\n"
            f"{state['technical_steps']}\n\n"
            "Regards,\nAftercare Support"
        )
        email_sent = await self.mcp_client.send_customer_email(
            ticket_id=state["ticket_id"],
            to=state["customer_email"],
            subject=subject,
            body=body,
        )
        logging.info(
            "story.reply_agent | email result ticket_id=%s to=%s subject=%r body=%r email_sent=%s",
            state["ticket_id"],
            state["customer_email"],
            subject,
            body,
            email_sent,
        )
        return {
            **state,
            "reply_subject": subject,
            "reply_body": body,
            "email_sent": email_sent,
            "status": "completed",
        }
