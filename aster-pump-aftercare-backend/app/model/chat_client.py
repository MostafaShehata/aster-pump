import json
import logging
import re
from typing import Any

import httpx

from app.config import settings
from app.mcp.client import AftercareMcpClient
from app.rag.service import rag_service
from app.schemas import ChatRequest, ChatResponse


EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
TICKET_ID_PATTERN = re.compile(r"(?:ticket|#)\s*#?(\d+)", re.IGNORECASE)


class OllamaClient:
    """Small client for calling the local Ollama chat API."""

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        response_format: str | None = None,
        num_predict: int = 512,
    ) -> str:
        """Send messages to Ollama and return assistant text."""

        payload: dict[str, Any] = {
            "model": settings.model_name,
            "stream": False,
            "think": False,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
                "num_ctx": 4096,
            },
            "messages": messages,
        }
        if response_format is not None:
            payload["format"] = response_format

        logging.info(
            "story.llm-agent.ollama | sending request url=%s model=%s payload=%s",
            f"{settings.model_base_url}/api/chat",
            settings.model_name,
            payload,
        )
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                response = await client.post(f"{settings.model_base_url}/api/chat", json=payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"Model service returned HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Model service is unavailable: {exc}") from exc

        data = response.json()
        content = data.get("message", {}).get("content", "").strip()
        logging.info("story.llm-agent.ollama | received raw_response=%s content=%r", data, content)
        return content


class ChatToolPlanner:
    """Uses the LLM to decide whether chat needs an MCP tool."""

    TOOL_CATALOG = {
        "get_ticket": {
            "description": "Return one support ticket by ticket_id.",
            "arguments": {"ticket_id": "integer"},
        },
        "get_latest_ticket_for_customer": {
            "description": "Return the latest support ticket for a customer email.",
            "arguments": {"customer_email": "email string"},
        },
        "get_tickets_for_customer": {
            "description": "Return all support tickets for a customer email.",
            "arguments": {"customer_email": "email string"},
        },
    }

    def __init__(self, ollama_client: OllamaClient) -> None:
        self.ollama_client = ollama_client

    async def plan(self, request: ChatRequest) -> dict[str, Any]:
        """Ask the LLM for either a direct answer action or an MCP tool call."""

        detected_email = self.extract_email(request.message)
        detected_ticket_id = self.extract_ticket_id(request.message)
        tool_hint = self.build_tool_hint(request.message, detected_email, detected_ticket_id)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an LLM agent for Aster Pump Aftercare chat. "
                    "You can either answer directly or request one approved MCP tool. "
                    "Return JSON only. Do not use markdown. "
                    "Allowed actions: answer, tool_call. "
                    "Allowed MCP tools: get_ticket, get_latest_ticket_for_customer, get_tickets_for_customer. "
                    "Never invent tools. If a required email or ticket id is missing, use action=answer and ask the user for it."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "user_message": request.message,
                        "history": [{"role": item.role, "content": item.content} for item in request.history[-6:]],
                        "use_rag": request.use_rag,
                        "detected_email": detected_email,
                        "detected_ticket_id": detected_ticket_id,
                        "tool_catalog": self.TOOL_CATALOG,
                        "tool_hint": tool_hint,
                        "required_json_shape": {
                            "action": "answer or tool_call",
                            "answer": "short answer when action is answer",
                            "tool_name": "tool name when action is tool_call",
                            "arguments": {"name": "value"},
                            "reason": "short reason",
                        },
                    }
                ),
            },
        ]
        logging.info("story.llm-agent.planner | start planning message=%r tool_hint=%s", request.message, tool_hint)
        content = await self.ollama_client.chat(
            messages,
            temperature=0,
            response_format="json",
            num_predict=256,
        )
        decision = self.parse_decision(content)
        logging.info("story.llm-agent.planner | LLM returned decision=%s", decision)
        return self.normalize_decision(decision, request.message, detected_email, detected_ticket_id)

    def parse_decision(self, content: str) -> dict[str, Any]:
        """Parse the planner JSON, tolerating accidental surrounding text."""

        try:
            decision = json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return {"action": "answer", "answer": content, "reason": "Model returned non-JSON text."}
            decision = json.loads(content[start : end + 1])

        if not isinstance(decision, dict):
            return {"action": "answer", "answer": str(decision), "reason": "Model returned non-object JSON."}
        return decision

    def normalize_decision(
        self,
        decision: dict[str, Any],
        message: str,
        detected_email: str | None,
        detected_ticket_id: int | None,
    ) -> dict[str, Any]:
        """Validate the model decision and fill obvious extracted arguments."""

        action = decision.get("action")
        if action != "tool_call":
            answer = str(decision.get("answer") or "")
            if not answer and self.looks_like_ticket_list_request(message) and detected_email is None:
                answer = "Please provide your email address so I can look up your tickets."
            return {"action": "answer", "answer": answer, "reason": str(decision.get("reason", ""))}

        tool_name = str(decision.get("tool_name", ""))
        arguments = decision.get("arguments") if isinstance(decision.get("arguments"), dict) else {}
        if tool_name not in self.TOOL_CATALOG:
            raise ValueError(f"LLM requested unsupported MCP tool: {tool_name}")

        if tool_name in {"get_latest_ticket_for_customer", "get_tickets_for_customer"}:
            customer_email = str(arguments.get("customer_email") or detected_email or "")
            if not customer_email:
                return {
                    "action": "answer",
                    "answer": "Please provide your email address so I can look up your tickets.",
                    "reason": "Email is required before calling the ticket lookup MCP tool.",
                }
            arguments = {"customer_email": customer_email}

        if tool_name == "get_ticket":
            raw_ticket_id = arguments.get("ticket_id") or detected_ticket_id
            if raw_ticket_id is None:
                return {
                    "action": "answer",
                    "answer": "Please provide the ticket number you want me to check.",
                    "reason": "Ticket id is required before calling the ticket lookup MCP tool.",
                }
            arguments = {"ticket_id": int(raw_ticket_id)}

        normalized = {
            "action": "tool_call",
            "tool_name": tool_name,
            "arguments": arguments,
            "reason": str(decision.get("reason", "")),
        }
        logging.info("story.llm-agent.planner | normalized decision=%s", normalized)
        return normalized

    def build_tool_hint(self, message: str, detected_email: str | None, detected_ticket_id: int | None) -> str:
        """Create a small hint so the tiny local model chooses tools reliably."""

        lowered = message.lower()
        if detected_ticket_id is not None:
            return "If the user asks about this ticket number, return tool_call get_ticket."
        if self.looks_like_ticket_list_request(message) and detected_email:
            return "Return tool_call get_tickets_for_customer with the detected customer_email."
        if "latest" in lowered and "ticket" in lowered and detected_email:
            return "Return tool_call get_latest_ticket_for_customer with the detected customer_email."
        if "ticket" in lowered and detected_email:
            return "Return tool_call get_tickets_for_customer with the detected customer_email."
        if "ticket" in lowered and not detected_email:
            return "Return answer asking the user for their email address."
        return "No MCP tool is required unless the user asks about support tickets."

    def looks_like_ticket_list_request(self, message: str) -> bool:
        """Return true when the user appears to ask for ticket history."""

        lowered = message.lower()
        return "ticket" in lowered and any(word in lowered for word in ["list", "all", "my", "status", "show", "get"])

    def extract_email(self, text: str) -> str | None:
        """Extract the first email address from text."""

        match = EMAIL_PATTERN.search(text)
        return match.group(0) if match else None

    def extract_ticket_id(self, text: str) -> int | None:
        """Extract a ticket id from phrases like ticket 12 or #12."""

        match = TICKET_ID_PATTERN.search(text)
        return int(match.group(1)) if match else None


class McpToolExecutor:
    """Executes approved model-requested MCP tools."""

    def __init__(self, mcp_client: AftercareMcpClient) -> None:
        self.mcp_client = mcp_client

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Run one approved MCP tool requested by the LLM."""

        logging.info("story.llm-agent.executor | executing MCP tool tool=%s arguments=%s", tool_name, arguments)
        if tool_name == "get_ticket":
            result = await self.mcp_client.get_ticket(int(arguments["ticket_id"]))
        elif tool_name == "get_latest_ticket_for_customer":
            result = await self.mcp_client.get_latest_ticket_for_customer(str(arguments["customer_email"]))
        elif tool_name == "get_tickets_for_customer":
            result = await self.mcp_client.get_tickets_for_customer(str(arguments["customer_email"]))
        else:
            raise ValueError(f"Unsupported MCP tool: {tool_name}")

        logging.info("story.llm-agent.executor | MCP tool result tool=%s result=%s", tool_name, result)
        return result


class PromptBuilder:
    """Builds final-answer messages for the local chat model."""

    def build_direct_messages(self, request: ChatRequest, rag_context: str) -> list[dict[str, str]]:
        """Create messages for normal chat without an MCP tool result."""

        messages = [self.system_message()]
        if rag_context:
            messages.append(self.rag_message(rag_context))

        for item in request.history[-6:]:
            messages.append({"role": item.role, "content": item.content})

        messages.append({"role": "user", "content": request.message})
        logging.info("story.llm-agent.prompt | built direct messages=%s", messages)
        return messages

    def build_tool_result_messages(
        self,
        request: ChatRequest,
        decision: dict[str, Any],
        tool_result: Any,
        rag_context: str,
    ) -> list[dict[str, str]]:
        """Create messages that ask the LLM to explain an MCP tool result."""

        messages = [
            self.system_message(),
            {
                "role": "system",
                "content": (
                    "You just requested an MCP tool. Use the MCP tool result below to answer the user. "
                    "Do not claim you cannot access tickets; the tool result is the source of truth."
                ),
            },
        ]
        if rag_context:
            messages.append(self.rag_message(rag_context))

        messages.append(
            {
                "role": "system",
                "content": json.dumps(
                    {
                        "mcp_tool_name": decision["tool_name"],
                        "mcp_tool_arguments": decision["arguments"],
                        "mcp_tool_result": self.compact_tool_result(decision["tool_name"], tool_result),
                    }
                ),
            }
        )
        for item in request.history[-6:]:
            messages.append({"role": item.role, "content": item.content})
        messages.append({"role": "user", "content": request.message})
        logging.info("story.llm-agent.prompt | built tool-result messages=%s", messages)
        return messages

    def compact_tool_result(self, tool_name: str, tool_result: Any) -> Any:
        """Shrink verbose MCP results before sending them back to the tiny model."""

        if tool_name == "get_tickets_for_customer" and isinstance(tool_result, dict):
            return {
                "customer_email": tool_result.get("customer_email"),
                "count": tool_result.get("count", 0),
                "tickets": [self.compact_ticket(ticket) for ticket in tool_result.get("tickets", [])],
            }
        if tool_name in {"get_ticket", "get_latest_ticket_for_customer"} and isinstance(tool_result, dict):
            return self.compact_ticket(tool_result)
        return tool_result

    def compact_ticket(self, ticket: dict[str, Any]) -> dict[str, Any]:
        """Keep only fields useful for a chat ticket summary."""

        return {
            "id": ticket.get("id"),
            "customer_email": ticket.get("customer_email"),
            "status": ticket.get("status"),
            "detected_error_code": ticket.get("detected_error_code"),
            "email_sent": ticket.get("email_sent"),
            "created_at": ticket.get("created_at"),
            "completed_at": ticket.get("completed_at"),
        }

    def system_message(self) -> dict[str, str]:
        """Return the base assistant behavior."""

        return {
            "role": "system",
            "content": (
                "You are a concise local assistant for Aster Pump Aftercare. "
                "Answer clearly. When ticket tool results are provided, summarize them with ticket id, status, error code, and email sent state."
            ),
        }

    def rag_message(self, rag_context: str) -> dict[str, str]:
        """Return RAG context as a system message."""

        return {
            "role": "system",
            "content": (
                "Use this retrieved local context when relevant. "
                "If the answer is in the context, prefer it over general knowledge.\n\n"
                f"{rag_context}"
            ),
        }


class OllamaChatService:
    """LLM agent chat service that can request approved MCP tools."""

    def __init__(
        self,
        prompt_builder: PromptBuilder | None = None,
        ollama_client: OllamaClient | None = None,
        mcp_client: AftercareMcpClient | None = None,
    ) -> None:
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.ollama_client = ollama_client or OllamaClient()
        self.tool_planner = ChatToolPlanner(self.ollama_client)
        self.tool_executor = McpToolExecutor(mcp_client or AftercareMcpClient())

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Plan with the LLM, optionally execute MCP, and produce the final reply."""

        logging.info(
            "story.llm-agent | received chat message=%r use_rag=%s history=%s",
            request.message,
            request.use_rag,
            [{"role": item.role, "content": item.content} for item in request.history],
        )
        rag_result = rag_service.retrieve_context(request)
        decision = await self.tool_planner.plan(request)

        if decision["action"] == "tool_call":
            tool_result = await self.tool_executor.execute(decision["tool_name"], decision["arguments"])
            messages = self.prompt_builder.build_tool_result_messages(
                request=request,
                decision=decision,
                tool_result=tool_result,
                rag_context=rag_result.context,
            )
            reply = await self.ollama_client.chat(messages, temperature=0.1, num_predict=192)
            if not reply:
                reply = self.fallback_tool_reply(decision["tool_name"], tool_result)
            logging.info(
                "story.llm-agent | completed with MCP tool=%s arguments=%s reply=%r",
                decision["tool_name"],
                decision["arguments"],
                reply,
            )
        else:
            direct_answer = decision.get("answer", "")
            if direct_answer and ("provide your email" in direct_answer.lower() or "ticket number" in direct_answer.lower()):
                reply = direct_answer
                logging.info("story.llm-agent | completed planner answer without second model call reply=%r", reply)
            else:
                messages = self.prompt_builder.build_direct_messages(request, rag_result.context)
                reply = await self.ollama_client.chat(messages, temperature=0.2, num_predict=512)
                if not reply:
                    reply = direct_answer or "The local model returned an empty response. Try a shorter message."
                logging.info("story.llm-agent | completed direct answer reply=%r", reply)

        return ChatResponse(
            reply=reply,
            model=settings.model_name,
            used_rag=bool(rag_result.context),
            sources=rag_result.sources,
        )

    def fallback_tool_reply(self, tool_name: str, tool_result: Any) -> str:
        """Return a deterministic backup if the model produces an empty final answer."""

        if tool_name == "get_tickets_for_customer" and isinstance(tool_result, dict):
            tickets = tool_result.get("tickets", [])
            if not tickets:
                return f"No tickets were found for {tool_result.get('customer_email')}."
            lines = [f"I found {len(tickets)} ticket(s):"]
            for ticket in tickets:
                lines.append(
                    f"- Ticket #{ticket.get('id')}: status={ticket.get('status')}, "
                    f"error={ticket.get('detected_error_code')}, email_sent={ticket.get('email_sent')}"
                )
            return "\n".join(lines)

        return f"The MCP tool `{tool_name}` returned: {tool_result}"
