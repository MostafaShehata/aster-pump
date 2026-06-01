# API Package

This package contains the FastAPI HTTP layer.

The API package is responsible for:

- creating the FastAPI application
- enabling local CORS for the React frontend
- exposing `/api/*` routes
- converting HTTP requests into calls to backend services
- converting internal dictionaries/states into public response models

It should not contain RAG logic, LangGraph node logic, model-calling logic, or
MCP protocol details. Those live in their own packages.

## Files

| File | Function |
| --- | --- |
| `application.py` | Creates and configures the FastAPI app. |
| `routes.py` | Defines public HTTP endpoints used by the frontend. |

## Application Creation

Code:

```python
def create_app() -> FastAPI:
    app = FastAPI(
        title="Aster Pump Aftercare Backend",
        description="FastAPI service that connects the React UI to agents, RAG, MCP tools, and a local model.",
        version="0.1.0",
    )
```

Explanation:

- `create_app()` is a factory function. It builds the FastAPI object.
- `FastAPI(...)` creates the web application.
- The title, description, and version appear in FastAPI docs if you open
  `/docs`.

## CORS

Code:

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

- CORS controls which browser origins can call the backend.
- `allow_origins=["*"]` is convenient for local PoC testing.
- In production, replace `*` with the exact frontend URL.

## Startup RAG Indexing

Code:

```python
@app.on_event("startup")
async def startup() -> None:
    rag_service.ensure_index()
```

Explanation:

- FastAPI runs this function when the backend container starts.
- `rag_service.ensure_index()` reads documents from `docs`, chunks them,
  embeds them, and stores them in Qdrant.
- This means the RAG database is refreshed whenever the backend starts.

## Router Registration

Code:

```python
app.include_router(router)
```

Explanation:

- `router` comes from `routes.py`.
- All endpoint definitions are grouped there.
- This keeps app setup separate from route behavior.

## Legacy Create Ticket Endpoint

Code:

```python
@router.post("/support/tickets", response_model=TicketResponse)
async def create_support_ticket(
    customer_email: str = Form(...),
    description: str = Form(""),
    photo: UploadFile | None = File(None),
) -> TicketResponse:
```

Explanation:

- This endpoint is retained for LangGraph training and direct API testing.
- The current React app uses `/api/chat/upload` instead.
- `Form(...)` means the value comes from multipart form data.
- `File(None)` means the uploaded photo is optional.
- The request is valid when it has an image, text description, or both.
- `response_model=TicketResponse` tells FastAPI what JSON shape to return.

## Calling The LangGraph Workflow

Code:

```python
final_state = await aftercare_workflow.run(
    customer_email=customer_email,
    description=description,
    image_filename=(photo.filename if photo is not None else "") or "uploaded-photo",
    image_content_type=(photo.content_type if photo is not None else None) or "application/octet-stream",
    image_bytes=image_bytes,
)
```

Explanation:

- The API does not create tickets directly.
- It calls the LangGraph workflow.
- The workflow starts with the Model Planner Agent.
- The planner asks Ollama to choose an approved JSON `plan_id`.
- The backend expands that `plan_id` into canonical agents and tools.
- The Plan Validator Agent validates the expanded model plan.
- The approved plan routes to image intake or text intake.
- Both intake paths continue to the Technical Assistant Agent and Reply Agent.
- `final_state` is the final shared state after all agents finish.

## Chat Endpoint

Code:

```python
response = await chat_service.chat(request)
```

Explanation:

- The API route does not decide whether MCP is needed.
- `chat_service` is an LLM tool-agent.
- The LLM first chooses either direct answer or approved MCP tool call.
- The backend validates and executes requested MCP tools.
- The final answer is returned as `ChatResponse`.

## Chat Upload Endpoint

Code:

```python
@router.post("/chat/upload", response_model=ChatResponse)
async def chat_with_optional_upload(
    message: str = Form(...),
    history: str = Form("[]"),
    use_rag: bool = Form(False),
    photo: UploadFile | None = File(None),
) -> ChatResponse:
```

Explanation:

- This is the primary route used by the simplified React UI.
- It accepts normal chat text and an optional image in the same request.
- `history` is a JSON string because multipart form fields are text values.
- `photo` is optional, so text-only questions still use this route.

Code:

```python
response = await chat_service.chat_with_optional_image(
    request,
    image_filename=(photo.filename if photo is not None else "") or "uploaded-photo",
    image_bytes=image_bytes,
    image_content_type=(photo.content_type if photo is not None else None) or "application/octet-stream",
)
```

Explanation:

- The API does not decide which tool to use.
- It passes the text and optional image bytes to the chat service.
- The LLM planner decides whether to answer directly or request an approved MCP
  workflow such as `open_ticket_from_image`.
- The backend logs image filename, size, and content type, but not raw image
  content.

## Mapping Internal State To API Response

Code:

```python
return TicketResponse(
    ticket_id=final_state["ticket_id"],
    customer_email=final_state["customer_email"],
    status=final_state["status"],
    detected_objects=final_state.get("detected_objects", []),
    detected_error_code=final_state.get("detected_error_code"),
    technical_steps=final_state.get("technical_steps", ""),
    reply_subject=final_state.get("reply_subject", ""),
    reply_body=final_state.get("reply_body", ""),
    email_sent=bool(final_state.get("email_sent")),
)
```

Explanation:

- The graph state is a Python dictionary.
- The API response is a Pydantic model.
- This code converts internal workflow data into stable frontend JSON.
