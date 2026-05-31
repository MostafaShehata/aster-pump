import logging
import re

from app.agents.state import AftercareState
from app.mcp.client import AftercareMcpClient
from app.rag.service import rag_service


class SupervisorAgent:
    """Routes the request to the correct intake agent based on available input."""

    def __call__(self, state: AftercareState) -> AftercareState:
        description = state.get("description", "").strip()
        has_image = bool(state.get("image_bytes"))
        has_text = bool(description)

        if not has_image and not has_text:
            raise ValueError("Request must include an image, text description, or both.")

        route = "image_intake" if has_image else "text_intake"
        logging.info(
            "agent.supervisor | routed request route=%s has_image=%s has_text=%s",
            route,
            has_image,
            has_text,
        )
        return {
            **state,
            "intake_route": route,
            "has_image": has_image,
            "has_text": has_text,
            "status": "routed",
        }


class CustomerServiceAgent:
    """Analyzes an uploaded image and opens the support ticket."""

    def __init__(self, mcp_client: AftercareMcpClient) -> None:
        self.mcp_client = mcp_client

    async def __call__(self, state: AftercareState) -> AftercareState:
        logging.info("agent.customer_service | analyzing uploaded image")
        detected_objects = await self.mcp_client.analyze_image(
            state["image_filename"],
            state["image_bytes"],
            state.get("image_content_type"),
        )
        ticket = await self.mcp_client.create_ticket(
            customer_email=state["customer_email"],
            description=state.get("description", ""),
            detected_objects=detected_objects,
        )
        logging.info(
            "agent.customer_service | ticket created ticket_id=%s detected=%s error_code=%s",
            ticket["id"],
            detected_objects,
            ticket.get("detected_error_code"),
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
        description = state.get("description", "")
        detected_objects = self.detect_text_objects(description)
        logging.info(
            "agent.text_customer_service | creating ticket from text detected=%s",
            detected_objects,
        )
        ticket = await self.mcp_client.create_ticket(
            customer_email=state["customer_email"],
            description=description,
            detected_objects=detected_objects,
        )
        logging.info(
            "agent.text_customer_service | ticket created ticket_id=%s error_code=%s",
            ticket["id"],
            ticket.get("detected_error_code"),
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
        issue_terms = ", ".join(state.get("detected_objects", []))
        logging.info(
            "agent.technical_assistant | retrieving manual steps ticket_id=%s issue_terms=%r",
            state["ticket_id"],
            issue_terms,
        )
        question = (
            f"Provide after-purchase troubleshooting steps for {issue_terms}. "
            f"Customer description: {state.get('description', '')}"
        )
        rag_result = rag_service.retrieve_for_question(question)

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
            "agent.technical_assistant | stored technical steps ticket_id=%s context_found=%s",
            state["ticket_id"],
            bool(rag_result.context),
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
        logging.info("agent.reply | preparing email ticket_id=%s", state["ticket_id"])
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
            "agent.reply | email result ticket_id=%s email_sent=%s",
            state["ticket_id"],
            email_sent,
        )
        return {
            **state,
            "reply_subject": subject,
            "reply_body": body,
            "email_sent": email_sent,
            "status": "completed",
        }
