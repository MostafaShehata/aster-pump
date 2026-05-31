from pydantic import BaseModel, EmailStr


class CreateTicketRequest(BaseModel):
    """Input for creating a support ticket."""

    customer_email: EmailStr
    description: str = ""
    detected_objects: list[str]


class UpdateTechnicalStepsRequest(BaseModel):
    """Input for storing generated troubleshooting steps."""

    ticket_id: int
    technical_steps: str


class SendEmailRequest(BaseModel):
    """Input for the simulated email-sending tool."""

    to: EmailStr
    subject: str
    body: str
    ticket_id: int


class LatestTicketRequest(BaseModel):
    """Input for latest-ticket lookup by customer email."""

    customer_email: EmailStr
