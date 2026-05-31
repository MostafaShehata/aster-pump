import logging

import httpx

from app.config import settings
from app.rag.service import rag_service
from app.schemas import ChatRequest, ChatResponse


class PromptBuilder:
    """Builds the message list sent to the local chat model."""

    def build_messages(self, request: ChatRequest, rag_context: str) -> list[dict[str, str]]:
        """Create system, history, and user messages for Ollama."""

        logging.info(
            "story.chat-model | building messages user_message=%r use_rag=%s rag_context=%r history=%s",
            request.message,
            request.use_rag,
            rag_context,
            [{"role": item.role, "content": item.content} for item in request.history],
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a concise local assistant running in a CPU-only PoC. "
                    "Answer clearly. Keep responses short unless the user asks for detail."
                ),
            }
        ]

        if rag_context:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Use this retrieved local context when it is relevant. "
                        "If the answer is in the context, prefer it over general knowledge.\n\n"
                        f"{rag_context}"
                    ),
                }
            )

        # Keep only a small history window so tiny CPU models remain responsive.
        for item in request.history[-6:]:
            messages.append({"role": item.role, "content": item.content})

        messages.append({"role": "user", "content": request.message})
        logging.info("story.chat-model | built Ollama messages=%s", messages)
        return messages


class OllamaChatService:
    """Application service for local model chat through Ollama."""

    def __init__(self, prompt_builder: PromptBuilder | None = None) -> None:
        self.prompt_builder = prompt_builder or PromptBuilder()

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Run optional RAG retrieval, call Ollama, and return API response."""

        rag_result = rag_service.retrieve_context(request)
        messages = self.prompt_builder.build_messages(request, rag_result.context)
        logging.info(
            "story.chat-model | sending request to Ollama model=%s used_rag=%s message_count=%s sources=%s",
            settings.model_name,
            bool(rag_result.context),
            len(messages),
            rag_result.sources,
        )

        model_request = {
            "model": settings.model_name,
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 256,
                "num_ctx": 2048,
            },
            "messages": messages,
        }
        logging.info("story.chat-model | Ollama request payload=%s", model_request)

        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                response = await client.post(f"{settings.model_base_url}/api/chat", json=model_request)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"Model service returned HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Model service is unavailable: {exc}") from exc

        data = response.json()
        reply = data.get("message", {}).get("content", "").strip()
        if not reply:
            reply = "The local model returned an empty response. Try a shorter message."

        logging.info("story.chat-model | Ollama replied raw_response=%s reply=%r", data, reply)
        return ChatResponse(
            reply=reply,
            model=settings.model_name,
            used_rag=bool(rag_result.context),
            sources=rag_result.sources,
        )
