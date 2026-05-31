from typing import TypedDict


class AftercareState(TypedDict, total=False):
    """Shared state passed between the three LangGraph agents."""

    customer_email: str
    description: str
    image_filename: str
    image_content_type: str
    image_bytes: bytes
    detected_objects: list[str]
    detected_error_code: str | None
    ticket_id: int
    technical_steps: str
    reply_subject: str
    reply_body: str
    email_sent: bool
    status: str

