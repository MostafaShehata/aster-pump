from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single chat message sent between frontend and backend."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    """Incoming chat request from the React frontend."""

    message: str = Field(min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)
    use_rag: bool = False


class ChatResponse(BaseModel):
    """Stable response contract returned to the frontend."""

    reply: str
    model: str
    used_rag: bool
    sources: list[str] = Field(default_factory=list)


class TicketResponse(BaseModel):
    """Response returned after the LangGraph aftercare workflow finishes."""

    ticket_id: int
    customer_email: str
    status: str
    detected_objects: list[str]
    detected_error_code: str | None = None
    technical_steps: str
    reply_subject: str
    reply_body: str
    email_sent: bool


class TicketStatusResponse(BaseModel):
    """Simple ticket status lookup response."""

    ticket_id: int
    customer_email: str
    status: str
    detected_error_code: str | None = None
    technical_steps: str | None = None
    email_sent: bool
