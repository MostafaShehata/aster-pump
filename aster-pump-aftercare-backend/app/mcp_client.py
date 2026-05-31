"""Compatibility imports for older code paths.

New code should import `AftercareMcpClient` from `app.mcp.client`.
"""

from app.mcp.client import AftercareMcpClient


_client = AftercareMcpClient()


async def analyze_image(filename: str, content: bytes, content_type: str | None) -> list[str]:
    return await _client.analyze_image(filename, content, content_type)


async def create_ticket(customer_email: str, description: str, detected_objects: list[str]) -> dict:
    return await _client.create_ticket(customer_email, description, detected_objects)


async def update_technical_steps(ticket_id: int, technical_steps: str) -> dict:
    return await _client.update_technical_steps(ticket_id, technical_steps)


async def send_customer_email(ticket_id: int, to: str, subject: str, body: str) -> bool:
    return await _client.send_customer_email(ticket_id, to, subject, body)


async def get_ticket(ticket_id: int) -> dict | None:
    return await _client.get_ticket(ticket_id)


async def get_latest_ticket_for_customer(customer_email: str) -> dict | None:
    return await _client.get_latest_ticket_for_customer(customer_email)
