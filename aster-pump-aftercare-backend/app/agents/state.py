from typing import Any, Literal, TypedDict


class AftercareState(TypedDict, total=False):
    """Shared state passed between planner, validator, and worker agents."""

    customer_email: str
    description: str
    intake_route: Literal["image_intake", "text_intake"]
    model_plan: dict[str, Any]
    planned_steps: list[str]
    planned_tools: list[str]
    plan_reason: str
    planner_source: str
    plan_validation_status: str
    image_filename: str
    image_content_type: str
    image_bytes: bytes
    has_image: bool
    has_text: bool
    workflow_step_count: int
    supervisor_route_count: int
    workflow_trace: list[str]
    detected_objects: list[str]
    detected_error_code: str | None
    ticket_id: int
    technical_steps: str
    reply_subject: str
    reply_body: str
    email_sent: bool
    status: str
