import base64
import contextlib
from datetime import datetime, timezone
import json
import logging
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from app.database import TicketRepository
from app.image_tool import ImageAnalyzerTool
from app.logging_config import configure_logging


configure_logging()
LOG_PATH = Path("/tmp/aftercare-email-log.jsonl")
CONFIG_PATH = Path(__file__).resolve().parent.parent / "mcp-config.json"

ticket_repository = TicketRepository()
image_analyzer_tool = ImageAnalyzerTool()

# This is the official MCP server. Streamable HTTP is the current recommended
# transport for production-style HTTP deployments, and JSON responses make this
# simple for service-to-service calls inside Docker Compose.
mcp = FastMCP(
    name="Aster Pump Aftercare MCP Server",
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
async def analyze_image(
    filename: str,
    content_base64: str,
    content_type: str = "application/octet-stream",
) -> dict:
    """Send an image to the Image AI service and return detected objects."""

    content = base64.b64decode(content_base64)
    if not content:
        raise ValueError("Uploaded file is empty.")

    logging.info(
        "story.mcp.tool.analyze_image | received image filename=%s image_bytes=%s content_type=%s",
        filename,
        len(content),
        content_type,
    )
    objects = await image_analyzer_tool.analyze(
        filename=filename or "uploaded-photo",
        content=content,
        content_type=content_type,
    )
    logging.info("story.mcp.tool.analyze_image | image service replied objects=%s", objects)
    return {"objects": objects}


@mcp.tool()
def create_ticket(
    customer_email: str,
    description: str,
    detected_objects: list,
) -> dict:
    """Insert analyzed support-ticket information into PostgreSQL."""

    logging.info(
        "story.mcp.tool.create_ticket | inserting ticket email=%s description=%r detected_objects=%s",
        customer_email,
        description,
        detected_objects,
    )
    ticket = ticket_repository.create_ticket(
        customer_email=customer_email,
        description=description,
        detected_objects=detected_objects,
    )
    logging.info("story.mcp.tool.create_ticket | created ticket=%s", ticket)
    return ticket


@mcp.tool()
def update_technical_steps(ticket_id: int, technical_steps: str) -> dict:
    """Store generated troubleshooting steps on an existing ticket."""

    logging.info(
        "story.mcp.tool.update_technical_steps | updating ticket_id=%s technical_steps=%r",
        ticket_id,
        technical_steps,
    )
    ticket = ticket_repository.attach_technical_steps(
        ticket_id=ticket_id,
        technical_steps=technical_steps,
    )
    if ticket is None:
        raise ValueError("Ticket not found.")
    logging.info("story.mcp.tool.update_technical_steps | updated ticket=%s", ticket)
    return ticket


@mcp.tool()
def send_customer_email(ticket_id: int, to: str, subject: str, body: str) -> dict:
    """Simulate sending a customer email and mark the ticket completed."""

    timestamp = datetime.now(timezone.utc).isoformat()
    logging.info(
        "story.mcp.tool.send_customer_email | sending ticket_id=%s to=%s subject=%r body=%r",
        ticket_id,
        to,
        subject,
        body,
    )
    record = {
        "timestamp": timestamp,
        "ticket_id": ticket_id,
        "to": to,
        "subject": subject,
        "body": body,
        "status": "sent",
    }

    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(record) + "\n")

    ticket_repository.mark_email_sent(ticket_id, subject, body)
    logging.info("story.mcp.tool.send_customer_email | sent ticket_id=%s log_path=%s", ticket_id, LOG_PATH)
    return {"status": "sent", "sent_at": timestamp, "ticket_id": ticket_id}


@mcp.tool()
def get_ticket(ticket_id: int):
    """Return one ticket by ID, or null when it does not exist."""

    logging.info("story.mcp.tool.get_ticket | ticket_id=%s", ticket_id)
    ticket = ticket_repository.get_ticket(ticket_id)
    logging.info("story.mcp.tool.get_ticket | result=%s", ticket)
    return ticket


@mcp.tool()
def get_latest_ticket_for_customer(customer_email: str):
    """Return the most recent support ticket for a customer email."""

    logging.info("story.mcp.tool.get_latest_ticket_for_customer | email=%s", customer_email)
    ticket = ticket_repository.latest_ticket_for_email(customer_email)
    logging.info("story.mcp.tool.get_latest_ticket_for_customer | result=%s", ticket)
    return ticket


@mcp.tool()
def get_tickets_for_customer(customer_email: str):
    """Return all support tickets for a customer email, newest first."""

    logging.info("story.mcp.tool.get_tickets_for_customer | email=%s", customer_email)
    tickets = ticket_repository.list_tickets_for_email(customer_email)
    logging.info("story.mcp.tool.get_tickets_for_customer | count=%s result=%s", len(tickets), tickets)
    return {"tickets": tickets, "count": len(tickets), "customer_email": customer_email}


@mcp.resource("config://mcp")
def read_tool_manifest() -> str:
    """Return the local tool manifest documentation as a resource."""

    return CONFIG_PATH.read_text(encoding="utf-8")


async def health(_: object) -> JSONResponse:
    """Small HTTP health endpoint for Docker health checks."""

    return JSONResponse({"status": "ok", "service": "mcp-server", "protocol": "mcp"})


@contextlib.asynccontextmanager
async def lifespan(_: Starlette):
    """Start the MCP session manager when Uvicorn starts the ASGI app."""

    logging.info("story.mcp.startup | official MCP Streamable HTTP server starting")
    async with mcp.session_manager.run():
        logging.info("story.mcp.startup | mcp session manager ready")
        yield
    logging.info("story.mcp.shutdown | mcp session manager stopped")


app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        Mount("/", app=mcp.streamable_http_app()),
    ],
    lifespan=lifespan,
)
