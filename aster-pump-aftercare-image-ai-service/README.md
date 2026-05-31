# Aster Pump Aftercare Image AI Service

Small image-analysis service for the Aster Pump Aftercare PoC.

This service receives an uploaded file and returns detected objects/text labels,
for example:

```json
{
  "objects": ["AsterPump X17", "E-77"]
}
```

## Technology Brief

### FastAPI

FastAPI exposes:

- `GET /health`
- `GET /test`
- `POST /analyze-image`

### Lightweight Rule-Based Analyzer

This PoC does not run a heavy OCR or vision model. It extracts searchable text
from the uploaded filename and readable bytes, then applies simple detectors.

This keeps the service CPU-only, fast, and easy to run on Docker Desktop.

## Important Files

| File | Function |
| --- | --- |
| `app/main.py` | FastAPI routes and CORS setup. |
| `app/analyzer.py` | Object-oriented analyzer classes. |
| `app/schemas.py` | Response schema. |
| `app/static/test.html` | Browser test page. |
| `requirements.txt` | Python dependencies. |
| `Dockerfile` | Builds the service image. |

## Code Walkthrough

### FastAPI App

```python
app = FastAPI(
    title="Aftercare Image AI Service",
    description="Tiny PoC image analyzer that extracts visible text-like objects.",
    version="0.1.0",
)
```

Explanation:

- Creates the web API.
- The metadata appears in `/docs`.

### CORS For Local Test Page

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Explanation:

- Allows the standalone test HTML page to call the API.
- Useful when the HTML is served from `localhost` or opened from disk.

### Analyze Endpoint

```python
@app.post("/analyze-image")
async def analyze_image(file: UploadFile = File(...)) -> AnalyzeImageResponse:
```

Explanation:

- Receives a multipart file named `file`.
- The frontend/MCP server posts uploaded images to this endpoint.

```python
content = await file.read()
uploaded_image = UploadedImage(filename=file.filename or "", content=content)
return AnalyzeImageResponse(objects=analyzer.analyze(uploaded_image))
```

Explanation:

- Reads the uploaded bytes.
- Wraps filename and bytes in an object.
- Calls the analyzer.
- Returns a stable JSON response.

### Analyzer Design

The analyzer package is object-oriented:

- `UploadedImage`: data object containing filename and bytes
- `SearchableTextExtractor`: extracts searchable text
- `ProductDetector`: detects `AsterPump X17`
- `ErrorCodeDetector`: detects codes such as `E-77`
- `ImageAnalyzer`: coordinates all detectors

### Error Code Detection

The service is designed for demo files such as:

```text
asterpump_x17_e77_screen.png
```

or text content containing:

```text
AsterPump X17 display shows E-77
```

## Test Page

Open:

```text
http://localhost:8100/test
```

The page uploads a file to:

```text
http://localhost:8100/analyze-image
```

## Build And Deployment

See:

```text
BUILD_AND_DEPLOY.md
```

