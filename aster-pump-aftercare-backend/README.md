# Aster Pump Aftercare Backend

FastAPI + model-planned LangGraph orchestration backend for the Aster Pump
aftercare service.

This backend is the main application brain. It receives requests from the React
frontend, runs the model-planned LangGraph workflow, retrieves manual content through
RAG, calls the local Ollama model for chat, and uses the MCP server for external
tools such as image analysis, database tickets, and email.

## Architecture

The backend is split by domain package:

| Package | Responsibility |
| --- | --- |
| `app/api` | FastAPI app creation and HTTP routes. |
| `app/agents` | LangGraph state, nodes, and workflow. |
| `app/rag` | PDF/text loading, chunking, embeddings, Qdrant indexing, and retrieval. |
| `app/mcp` | Official MCP Streamable HTTP client. |
| `app/model` | Ollama chat client and prompt building. |

Each package has its own `README.md` with beginner-friendly code explanations.

## Model-Planned Agent Flow

1. Frontend submits customer email plus image, text, or both.
2. API route calls `aftercare_workflow.run(...)`.
3. Model Planner Agent asks Ollama to choose an approved JSON `plan_id`.
4. Backend expands the plan id into canonical agents and tools.
5. Plan Validator Agent validates agents, tools, order, request inputs, and max
   step limits.
6. Validated plan chooses the route:
   `image_intake` when an image exists, otherwise `text_intake`.
7. Image Customer Service Agent calls MCP `analyze_image` when image input is
   present.
8. Text Customer Service Agent skips image analysis and extracts simple text
   signals when only text is present.
9. The selected customer-service agent calls MCP `create_ticket`.
10. Technical Assistant Agent searches RAG/Qdrant for manual steps.
11. Technical Assistant Agent calls MCP `update_technical_steps`.
12. Reply Agent calls MCP `send_customer_email`.
13. API returns the completed ticket result to the frontend.

Safety checks:

- `MAX_WORKFLOW_STEPS` defaults to `8` and stops runaway graphs.
- `MAX_SUPERVISOR_ROUTES` defaults to `3` and stops repeated plan routing.
- Each workflow records a `workflow_trace` in backend logs so the executed agent
  path is visible.

## Plan Validation

The local model can only choose a plan. It cannot directly execute tools.

For CPU reliability, the tiny model chooses one approved `plan_id`:

- `image_ticket` for requests with an uploaded image
- `text_ticket` for text-only requests

The backend expands the selected id into the exact agent/tool plan, then
validates that expanded plan.

Approved agents:

- `image_customer_service`
- `text_customer_service`
- `technical_assistant`
- `reply_agent`

Approved tools:

- `analyze_image`
- `create_ticket`
- `rag_search`
- `update_technical_steps`
- `send_customer_email`

The backend rejects any plan that invents an agent, invents a tool, uses a tool
with the wrong agent, starts with the wrong intake agent, or exceeds the maximum
workflow step count.

## RAG Flow

1. Backend starts.
2. `app/api/application.py` calls `rag_service.ensure_index()`.
3. RAG loads documents from `docs`.
4. PDF text is extracted with `pypdf`.
5. Text is chunked into small sections.
6. Each chunk is embedded with the small CPU embedding model `BAAI/bge-small-en-v1.5`.
7. Vectors and payloads are stored in Qdrant collection `asterpump_x17_docs`.
8. Chat or agents search Qdrant when they need local manual knowledge.

## Endpoints

- `GET /api/health`
- `POST /api/chat`
- `POST /api/support/tickets`
- `GET /api/support/tickets/{ticket_id}`
- `GET /api/support/tickets?email=<customer email>`

## Runtime Dependencies

- Ollama model service for `/api/chat`.
- Qdrant for RAG retrieval.
- MCP server for image analysis, ticket DB operations, ticket lookup, and email.

## Important Training Docs

Read these in order:

1. `app/api/README.md`
2. `app/agents/README.md`
3. `app/rag/README.md`
4. `app/mcp/README.md`
5. `app/model/README.md`

That order follows the request path from frontend to agents, then into RAG,
tools, and model chat.

## Important Files

| File | Purpose |
| --- | --- |
| `app/main.py` | Uvicorn entrypoint. Creates the FastAPI app. |
| `app/api/application.py` | App factory, CORS setup, startup indexing. |
| `app/api/routes.py` | Public HTTP API routes. |
| `app/agents/workflow.py` | LangGraph workflow wiring. |
| `app/agents/nodes.py` | Model planner, plan validator, customer-service, technical-assistant, and reply agents. |
| `app/rag/service.py` | Coordinates RAG indexing and retrieval. |
| `app/mcp/client.py` | Official MCP client wrapper. |
| `app/model/chat_client.py` | Ollama chat service. |
| `app/schemas.py` | API request and response models. |
