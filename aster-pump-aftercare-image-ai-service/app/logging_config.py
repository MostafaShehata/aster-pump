import logging
import sys


def configure_logging() -> None:
    """Configure readable container logs for the image analyzer service."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | IMAGE-AI | %(levelname)s | %(message)s",
        stream=sys.stdout,
        force=True,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
