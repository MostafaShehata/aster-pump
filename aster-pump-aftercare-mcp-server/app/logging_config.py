import logging
import sys


def configure_logging() -> None:
    """Configure readable container logs for the MCP server."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | MCP | %(levelname)s | %(message)s",
        stream=sys.stdout,
        force=True,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("mcp").setLevel(logging.WARNING)
    logging.getLogger("mcp.server.streamable_http").setLevel(logging.CRITICAL)
