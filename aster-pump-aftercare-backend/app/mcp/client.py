from __future__ import annotations

import base64
import json
import logging
from typing import Any

from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client

from app.config import settings


class McpToolResponseParser:
    """Converts MCP SDK tool responses into normal Python values."""

    def parse(self, result: types.CallToolResult) -> Any:
        """Return structured content, decoded JSON text, or plain text."""

        if result.isError:
            error_text = "; ".join(
                content.text
                for content in result.content
                if isinstance(content, types.TextContent)
            )
            raise RuntimeError(error_text or "MCP tool call failed.")

        if result.structuredContent is not None:
            return result.structuredContent

        for content in result.content:
            if isinstance(content, types.TextContent):
                try:
                    return json.loads(content.text)
                except json.JSONDecodeError:
                    return content.text

        return None


class McpSessionClient:
    """Small official MCP Streamable HTTP client wrapper."""

    def __init__(self, server_url: str, parser: McpToolResponseParser | None = None) -> None:
        self.server_url = server_url.rstrip("/")
        self.parser = parser or McpToolResponseParser()

    @property
    def endpoint_url(self) -> str:
        """Return the official MCP endpoint used by the backend."""

        return f"{self.server_url}/mcp"

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Open one MCP session, call one tool, and parse the result."""

        logging.info(
            "story.mcp-client | calling MCP tool=%s endpoint=%s arguments=%s",
            name,
            self.endpoint_url,
            self.safe_arguments_for_log(arguments),
        )
        async with streamablehttp_client(self.endpoint_url) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                logging.info("story.mcp-client | initializing MCP session for tool=%s", name)
                await session.initialize()
                logging.info("story.mcp-client | MCP session initialized; sending tool request tool=%s", name)
                result = await session.call_tool(name, arguments=arguments)
                parsed = self.parser.parse(result)
                logging.info("story.mcp-client | completed MCP tool=%s response=%s", name, parsed)
                return parsed

    def safe_arguments_for_log(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Return loggable tool arguments without raw image/base64 content."""

        safe_arguments = dict(arguments)
        content_base64 = safe_arguments.pop("content_base64", None)
        if isinstance(content_base64, str):
            safe_arguments["image_content_base64"] = "<omitted>"
            safe_arguments["image_base64_characters"] = len(content_base64)
        return safe_arguments


class AftercareMcpClient:
    """Domain-specific MCP client used by backend agents and API routes."""

    def __init__(self, session_client: McpSessionClient | None = None) -> None:
        self.session_client = session_client or McpSessionClient(settings.mcp_server_url)

    async def analyze_image(self, filename: str, content: bytes, content_type: str | None) -> list[str]:
        """Call the MCP image-analysis tool with base64 image content."""

        logging.info(
            "story.mcp-client | preparing analyze_image filename=%s image_bytes=%s content_type=%s",
            filename,
            len(content),
            content_type or "application/octet-stream",
        )
        payload = await self.session_client.call_tool(
            "analyze_image",
            {
                "filename": filename,
                "content_base64": base64.b64encode(content).decode("ascii"),
                "content_type": content_type or "application/octet-stream",
            },
        )
        logging.info("story.mcp-client | analyze_image returned objects=%s", payload.get("objects", []))
        return [str(item) for item in payload.get("objects", [])]

    async def create_ticket(self, customer_email: str, description: str, detected_objects: list[str]) -> dict:
        """Call the MCP ticket-creation tool."""

        logging.info(
            "story.mcp-client | preparing create_ticket email=%s description=%r detected_objects=%s",
            customer_email,
            description,
            detected_objects,
        )
        return await self.session_client.call_tool(
            "create_ticket",
            {
                "customer_email": customer_email,
                "description": description,
                "detected_objects": detected_objects,
            },
        )

    async def update_technical_steps(self, ticket_id: int, technical_steps: str) -> dict:
        """Call the MCP ticket-update tool."""

        logging.info(
            "story.mcp-client | preparing update_technical_steps ticket_id=%s technical_steps=%r",
            ticket_id,
            technical_steps,
        )
        return await self.session_client.call_tool(
            "update_technical_steps",
            {
                "ticket_id": ticket_id,
                "technical_steps": technical_steps,
            },
        )

    async def send_customer_email(self, ticket_id: int, to: str, subject: str, body: str) -> bool:
        """Call the MCP email tool and return whether it was sent."""

        logging.info(
            "story.mcp-client | preparing send_customer_email ticket_id=%s to=%s subject=%r body=%r",
            ticket_id,
            to,
            subject,
            body,
        )
        payload = await self.session_client.call_tool(
            "send_customer_email",
            {
                "ticket_id": ticket_id,
                "to": to,
                "subject": subject,
                "body": body,
            },
        )
        return payload.get("status") == "sent"

    async def get_ticket(self, ticket_id: int) -> dict | None:
        """Call the MCP ticket lookup tool."""

        logging.info("story.mcp-client | preparing get_ticket ticket_id=%s", ticket_id)
        return await self.session_client.call_tool("get_ticket", {"ticket_id": ticket_id})

    async def get_latest_ticket_for_customer(self, customer_email: str) -> dict | None:
        """Call the MCP latest-ticket lookup tool."""

        logging.info("story.mcp-client | preparing get_latest_ticket_for_customer email=%s", customer_email)
        return await self.session_client.call_tool(
            "get_latest_ticket_for_customer",
            {"customer_email": customer_email},
        )

    async def get_tickets_for_customer(self, customer_email: str) -> dict:
        """Call the MCP ticket-list tool."""

        logging.info("story.mcp-client | preparing get_tickets_for_customer email=%s", customer_email)
        return await self.session_client.call_tool(
            "get_tickets_for_customer",
            {"customer_email": customer_email},
        )
