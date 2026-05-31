import logging
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.analyzer import ImageAnalyzer, UploadedImage
from app.logging_config import configure_logging
from app.schemas import AnalyzeImageResponse


configure_logging()
app = FastAPI(
    title="Aftercare Image AI Service",
    description="Tiny PoC image analyzer that extracts visible text-like objects.",
    version="0.1.0",
)

# The standalone test HTML can be opened from http://localhost:8100/test or
# directly from disk. Allowing all origins keeps that local-only test page easy
# to use while the PoC runs inside Docker Desktop.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

analyzer = ImageAnalyzer()
STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/health")
async def health() -> dict[str, str]:
    """Health endpoint for Docker and manual verification."""

    return {"status": "ok", "service": "image-ai"}


@app.get("/test")
async def test_page() -> FileResponse:
    """Serve a small browser page for manually testing image uploads."""

    logging.info("test-page | serving manual test page")
    return FileResponse(STATIC_DIR / "test.html")


@app.post("/analyze-image")
async def analyze_image(file: UploadFile = File(...)) -> AnalyzeImageResponse:
    """Return a small list of detected objects/text from an uploaded image.

    This PoC avoids a heavy vision model. It looks for product/error text in
    the filename and file bytes. For demos, name the uploaded file like
    `asterpump-e-77.jpg` or upload a simple text file containing `E-77`.
    """

    content = await file.read()
    logging.info(
        "analyze-image | received filename=%s bytes=%s content_type=%s",
        file.filename,
        len(content),
        file.content_type,
    )
    uploaded_image = UploadedImage(filename=file.filename or "", content=content)
    objects = analyzer.analyze(uploaded_image)
    logging.info("analyze-image | detected objects=%s", objects)
    return AnalyzeImageResponse(objects=objects)
