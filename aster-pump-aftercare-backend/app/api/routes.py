import json
import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.agents.workflow import aftercare_workflow
from app.mcp.client import AftercareMcpClient
from app.model.chat_client import OllamaChatService
from app.schemas import ChatMessage, ChatRequest, ChatResponse, TicketResponse, TicketStatusResponse


router = APIRouter(prefix="/api")
chat_service = OllamaChatService()
mcp_client = AftercareMcpClient()


@router.get("/health")
async def health() -> dict[str, str]:
    """Simple health endpoint for Docker and manual checks."""

    return {"status": "ok", "service": "backend"}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a chat request to the local model with optional RAG context."""

    logging.info(
        "story.chat | received chat request use_rag=%s history_items=%s message=%r history=%s",
        request.use_rag,
        len(request.history),
        request.message,
        [{"role": item.role, "content": item.content} for item in request.history],
    )
    try:
        response = await chat_service.chat(request)
        logging.info(
            "story.chat | completed chat request model=%s used_rag=%s sources=%s reply=%r",
            response.model,
            response.used_rag,
            response.sources,
            response.reply,
        )
        return response
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/chat/upload", response_model=ChatResponse)
async def chat_with_optional_upload(
    message: str = Form(...),
    customer_email: str = Form(""),
    history: str = Form("[]"),
    use_rag: bool = Form(False),
    photo: UploadFile | None = File(None),
) -> ChatResponse:
    """Send one chat message plus an optional image through the LLM MCP agent."""

    try:
        raw_history = json.loads(history)
        chat_history = [ChatMessage.model_validate(item) for item in raw_history]
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="History must be a JSON array of chat messages.") from exc

    image_bytes = await photo.read() if photo is not None else b""
    if photo is not None and not image_bytes:
        raise HTTPException(status_code=400, detail="Photo file is empty.")

    normalized_message = merge_customer_email_into_tool_message(
        message=message.strip(),
        customer_email=customer_email.strip(),
        has_image=bool(image_bytes),
    )
    request = ChatRequest(message=normalized_message, history=chat_history, use_rag=use_rag)
    logging.info(
        "story.chat-upload | received chat request use_rag=%s history_items=%s customer_email=%s message=%r image_filename=%s image_bytes=%s image_content_type=%s history=%s",
        request.use_rag,
        len(request.history),
        customer_email.strip(),
        request.message,
        photo.filename if photo is not None else "",
        len(image_bytes),
        photo.content_type if photo is not None else "",
        [{"role": item.role, "content": item.content} for item in request.history],
    )
    try:
        response = await chat_service.chat_with_optional_image(
            request,
            image_filename=(photo.filename if photo is not None else "") or "uploaded-photo",
            image_bytes=image_bytes,
            image_content_type=(photo.content_type if photo is not None else None) or "application/octet-stream",
        )
        logging.info(
            "story.chat-upload | completed chat request model=%s used_rag=%s sources=%s reply=%r",
            response.model,
            response.used_rag,
            response.sources,
            response.reply,
        )
        return response
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/support/tickets", response_model=TicketResponse)
async def create_support_ticket(
    customer_email: str = Form(...),
    description: str = Form(""),
    photo: UploadFile | None = File(None),
) -> TicketResponse:
    """Start the after-purchase LangGraph workflow from image, text, or both."""

    image_bytes = await photo.read() if photo is not None else b""
    description = description.strip()
    if photo is not None and not image_bytes:
        raise HTTPException(status_code=400, detail="Photo file is empty.")
    if not image_bytes and not description:
        raise HTTPException(status_code=400, detail="Provide an error photo, a text description, or both.")

    logging.info(
        "story.ticket | received support request email=%s description=%r image_filename=%s image_bytes=%s image_content_type=%s",
        customer_email,
        description,
        photo.filename if photo is not None else "",
        len(image_bytes),
        photo.content_type if photo is not None else "",
    )
    try:
        final_state = await aftercare_workflow.run(
            customer_email=customer_email,
            description=description,
            image_filename=(photo.filename if photo is not None else "") or "uploaded-photo",
            image_content_type=(photo.content_type if photo is not None else None) or "application/octet-stream",
            image_bytes=image_bytes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logging.info(
        "story.ticket | completed support request ticket_id=%s status=%s detected_objects=%s error_code=%s technical_steps=%r reply_subject=%r reply_body=%r email_sent=%s",
        final_state["ticket_id"],
        final_state["status"],
        final_state.get("detected_objects", []),
        final_state.get("detected_error_code"),
        final_state.get("technical_steps", ""),
        final_state.get("reply_subject", ""),
        final_state.get("reply_body", ""),
        bool(final_state.get("email_sent")),
    )
    return TicketResponse(
        ticket_id=final_state["ticket_id"],
        customer_email=final_state["customer_email"],
        status=final_state["status"],
        detected_objects=final_state.get("detected_objects", []),
        detected_error_code=final_state.get("detected_error_code"),
        technical_steps=final_state.get("technical_steps", ""),
        reply_subject=final_state.get("reply_subject", ""),
        reply_body=final_state.get("reply_body", ""),
        email_sent=bool(final_state.get("email_sent")),
    )


@router.get("/support/tickets/{ticket_id}", response_model=TicketStatusResponse)
async def get_ticket_status(ticket_id: int) -> TicketStatusResponse:
    """Return ticket status by ticket ID."""

    logging.info("story.ticket-status | looking up ticket_id=%s", ticket_id)
    ticket = await mcp_client.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found.")

    return map_ticket_status(ticket)


@router.get("/support/tickets", response_model=TicketStatusResponse)
async def get_latest_ticket_for_email(email: str) -> TicketStatusResponse:
    """Return the latest support ticket for a customer email."""

    logging.info("story.ticket-status | looking up latest ticket email=%s", email)
    ticket = await mcp_client.get_latest_ticket_for_customer(email)
    if ticket is None:
        raise HTTPException(status_code=404, detail="No ticket found for email.")

    return map_ticket_status(ticket)


def map_ticket_status(ticket: dict) -> TicketStatusResponse:
    """Translate the MCP ticket dictionary into the public API response model."""

    return TicketStatusResponse(
        ticket_id=ticket["id"],
        customer_email=ticket["customer_email"],
        status=ticket["status"],
        detected_error_code=ticket.get("detected_error_code"),
        technical_steps=ticket.get("technical_steps"),
        email_sent=ticket["email_sent"],
    )


def merge_customer_email_into_tool_message(message: str, customer_email: str, has_image: bool) -> str:
    """Attach page-level email to ticket-related chat text before LLM planning."""

    if not customer_email or "@" in message:
        return message

    lowered = message.lower()
    ticket_related = has_image or any(
        word in lowered
        for word in [
            "ticket",
            "status",
            "request",
            "issue",
            "problem",
            "error",
            "display",
            "screen",
            "list",
            "latest",
            "last",
        ]
    )
    if not ticket_related:
        return message

    return f"{message}\nCustomer email: {customer_email}"
