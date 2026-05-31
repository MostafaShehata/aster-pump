from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import Protocol


@dataclass(frozen=True)
class UploadedImage:
    """Small immutable representation of the uploaded file.

    This service is intentionally lightweight for the PoC. It does not run a
    heavy OCR or vision model. Instead, it searches metadata and readable bytes
    from the uploaded file for product names and error-code patterns.
    """

    filename: str
    content: bytes


class SearchableTextExtractor:
    """Build the text surface used by simple detector classes."""

    def __init__(self, max_bytes: int = 4096) -> None:
        # Reading only a small prefix keeps the service predictable for local
        # demos and avoids trying to decode large binary image files.
        self.max_bytes = max_bytes

    def extract(self, uploaded_image: UploadedImage) -> str:
        """Return filename plus readable content bytes as one search string."""

        logging.info(
            "story.image-ai.extractor | extracting searchable metadata filename=%s image_bytes=%s max_bytes=%s",
            uploaded_image.filename,
            len(uploaded_image.content),
            self.max_bytes,
        )
        readable_content = uploaded_image.content[: self.max_bytes].decode(
            "utf-8",
            errors="ignore",
        )
        return f"{uploaded_image.filename} {readable_content}"


class Detector(Protocol):
    """Common interface for object/text detectors."""

    def detect(self, searchable_text: str) -> list[str]:
        """Return detected object labels from the searchable text."""


class ProductDetector:
    """Detect the fictional AsterPump product family."""

    PRODUCT_LABEL = "AsterPump X17"

    def detect(self, searchable_text: str) -> list[str]:
        normalized_text = searchable_text.lower()
        if "asterpump" in normalized_text or "x17" in normalized_text:
            return [self.PRODUCT_LABEL]
        return []


class ErrorCodeDetector:
    """Detect AsterPump-style error codes such as E-77, e77, or E93."""

    # This pattern accepts human display form (`E-77`) and filename-safe form
    # (`e77`). `(?!\d)` prevents partial matches such as E-771 becoming E-77.
    ERROR_PATTERN = re.compile(r"E-?(\d{2,3})(?!\d)", re.IGNORECASE)

    def detect(self, searchable_text: str) -> list[str]:
        labels: list[str] = []
        for match in self.ERROR_PATTERN.finditer(searchable_text):
            normalized = self.normalize_error_code(match.group(0))
            if normalized not in labels:
                labels.append(normalized)
        return labels

    @staticmethod
    def normalize_error_code(value: str) -> str:
        """Normalize values such as `e77`, `E77`, and `E-77` to `E-77`."""

        digits = re.sub(r"\D", "", value)
        return f"E-{digits}"


class ImageAnalyzer:
    """Coordinates the extraction and detector pipeline."""

    UNKNOWN_LABEL = "unknown_display"

    def __init__(
        self,
        extractor: SearchableTextExtractor | None = None,
        detectors: list[Detector] | None = None,
    ) -> None:
        self.extractor = extractor or SearchableTextExtractor()
        self.detectors = detectors or [ProductDetector(), ErrorCodeDetector()]

    def analyze(self, uploaded_image: UploadedImage) -> list[str]:
        """Analyze an uploaded image and return detected object/text labels."""

        searchable_text = self.extractor.extract(uploaded_image)
        objects: list[str] = []
        logging.info(
            "story.image-ai.analyzer | running detectors filename=%s image_bytes=%s detector_count=%s",
            uploaded_image.filename,
            len(uploaded_image.content),
            len(self.detectors),
        )

        for detector in self.detectors:
            detector_name = detector.__class__.__name__
            labels = detector.detect(searchable_text)
            logging.info("story.image-ai.analyzer | detector=%s labels=%s", detector_name, labels)
            for label in labels:
                if label not in objects:
                    objects.append(label)

        result = objects or [self.UNKNOWN_LABEL]
        logging.info("story.image-ai.analyzer | final result=%s", result)
        return result
