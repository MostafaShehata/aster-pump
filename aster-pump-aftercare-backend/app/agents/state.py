from typing import Literal, TypedDict


class AftercareState(TypedDict, total=False):
    """Shared state passed between the supervisor and worker agents."""

    customer_email: str
    description: str
    intake_route: Literal["image_intake", "text_intake"]
    image_filename: str
    image_content_type: str
    image_bytes: bytes
    has_image: bool
    has_text: bool
    detected_objects: list[str]
    detected_error_code: str | None
    ticket_id: int
    technical_steps: str
    reply_subject: str
    reply_body: str
    email_sent: bool
    status: str
