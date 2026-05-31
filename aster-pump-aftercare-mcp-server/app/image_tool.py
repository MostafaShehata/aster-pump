from __future__ import annotations

import logging

import httpx

from app.config import settings


class ImageAnalyzerTool:
    """MCP tool wrapper around the custom image analyzer service."""

    async def analyze(self, filename: str, content: bytes, content_type: str | None) -> list[str]:
        """Send an uploaded file to the image analyzer service."""

        files = {
            "file": (
                filename,
                content,
                content_type or "application/octet-stream",
            )
        }
        logging.info(
            "story.image-tool | forwarding image to analyzer url=%s filename=%s image_bytes=%s content_type=%s",
            settings.image_ai_url,
            filename,
            len(content),
            content_type or "application/octet-stream",
        )
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{settings.image_ai_url}/analyze-image", files=files)
            response.raise_for_status()
            data = response.json()
            objects = [str(item) for item in data.get("objects", [])]
            logging.info("story.image-tool | analyzer returned response=%s objects=%s", data, objects)
            return objects
