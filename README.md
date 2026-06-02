# Aster Pump Aftercare

Local Docker Desktop proof of concept for an after-purchase support assistant.

The user experience is intentionally simple: one chat screen plus one customer
email field at the top of the page. The customer can type a message, optionally
upload an image, optionally enable manual/RAG context, and the backend decides
whether to answer directly or call approved MCP tools.

## Business Use Cases

### Use Case 1: Open A Ticket From Chat

The customer can create a support ticket by typing a request such as:

```text
Create ticket for customer@example.com. The display shows E-77 on my AsterPump X17.
```

The customer can also attach a pump screen image. The email comes from the
page-level email field, so the chat box can stay focused on the actual request.
The LLM planner sees the text, the ticket-related email context, and whether an
image exists. It can request the `open_ticket_from_image` or
`open_ticket_from_text` tool workflow.

Business outcome:

- image text or typed error text is converted into detected objects such as
  `AsterPump X17` and `E-77`
- a ticket is inserted into PostgreSQL through the MCP server
- troubleshooting steps are retrieved from the local PDF manual through RAG
- the ticket is updated with those steps
- a simulated email is sent through the MCP server
- the chat returns the ticket number and status

### Use Case 2: Ask Questions

The same chat can answer:

- RAG/manual questions, for example `What is Bluefin mode?`
- general model questions, for example `Where is Egypt?`
- ticket lookup questions, for example
  `Get me list of my tickets for customer@example.com`
- latest status questions, for example
  `Get latest ticket status for customer@example.com`

When **Use manual** is enabled, the backend searches the embedded AsterPump X17
manual in Qdrant and passes the matching context to Ollama. When it is disabled,
the backend asks the local model without manual context.

## Chat-First Architecture

```mermaid
sequenceDiagram
    participant Browser as Browser Chat UI
    participant Nginx as Frontend Nginx
    participant API as FastAPI Backend
    participant Planner as LLM Tool Planner
    participant Model as Ollama qwen3:1.7b
    participant RAG as Qdrant RAG
    participant MCP as MCP Server
    participant IMG as Image AI Service
    participant DB as PostgreSQL
    participant Mail as Simulated Email

    Browser->>Nginx: Customer email, text message, optional image
    Nginx->>API: POST /api/chat/upload
    alt Use manual is enabled
        API->>RAG: Retrieve manual chunks
        RAG-->>API: Context and sources
    end
    API->>Planner: Ask model for answer or tool_call JSON
    Planner->>Model: Planning prompt with allowed tools
    Model-->>Planner: Tool decision or direct answer
    alt Tool is open_ticket_from_image
        Planner->>MCP: analyze_image
        MCP->>IMG: Send image bytes
        IMG-->>MCP: Detected objects
        Planner->>MCP: create_ticket
        MCP->>DB: Insert ticket
        Planner->>RAG: Retrieve troubleshooting steps
        Planner->>MCP: update_technical_steps
        Planner->>MCP: send_customer_email
        MCP->>Mail: Record simulated email
    else Tool is open_ticket_from_text
        Planner->>Planner: Extract text labels such as E-77
        Planner->>MCP: create_ticket, update steps, send email
    else Tool is ticket lookup
        Planner->>MCP: get_ticket or ticket list tool
        MCP->>DB: Read ticket rows
    else Direct answer
        Planner->>Model: Ask final answer with optional RAG context
    end
    API-->>Nginx: ChatResponse
    Nginx-->>Browser: Show assistant reply
```

## Model-Driven Tool Safety

The model decides the plan, but the backend validates and executes the plan.
That gives the demo dynamic behavior without letting the model call arbitrary
tools.

Approved chat tools:

- `open_ticket_from_image`
- `open_ticket_from_text`
- `get_ticket`
- `get_latest_ticket_for_customer`
- `get_tickets_for_customer`

The backend checks:

- the requested tool is in the approved catalog
- required arguments exist, such as customer email or ticket id
- image ticket creation only runs when an image was uploaded
- text ticket creation uses only the chat message text
- raw image bytes are never logged, only image size and content type

The older LangGraph support workflow still exists in the backend for learning
and comparison, but the current UI uses the chat-first LLM-to-MCP route.

## Detailed RAG Flow

Manual source files live in:

```text
aster-pump-aftercare-backend/docs
```

The backend indexes them when the backend container starts.

```mermaid
sequenceDiagram
    participant Files as PDF and Text Manuals
    participant Backend as Backend Startup
    participant Loader as Document Loader
    participant Embedder as FastEmbed BAAI/bge-small-en-v1.5
    participant Qdrant as Qdrant Vector DB
    participant Chat as Chat Request
    participant Model as Ollama

    Backend->>Files: Read manual files from /app/docs
    Files-->>Loader: PDF/text content
    Loader-->>Backend: Documents
    Backend->>Embedder: Embed document chunks
    Embedder-->>Backend: Vectors
    Backend->>Qdrant: Store vectors and source text
    Chat->>Embedder: Embed user question
    Embedder-->>Chat: Question vector
    Chat->>Qdrant: Search nearest manual chunks
    Qdrant-->>Chat: Matching context and sources
    Chat->>Model: Prompt with retrieved manual context
    Model-->>Chat: Grounded answer
```

## System Map

```mermaid
flowchart LR
    User["User Browser"] --> Frontend["Frontend\nReact + Nginx\nlocalhost:8080"]
    Frontend --> Backend["Backend\nFastAPI chat orchestrator\nlocalhost:8000"]
    Backend --> Model["Model\nOllama qwen3:1.7b\nlocalhost:11434"]
    Backend --> VectorDB["Vector DB\nQdrant\nlocalhost:6333"]
    Backend --> MCP["MCP Server\nOfficial MCP HTTP\nlocalhost:8200"]
    MCP --> ImageAI["Image AI Service\nFastAPI\nlocalhost:8100"]
    MCP --> DB["PostgreSQL DB\nlocalhost:5432"]
    MCP --> Mail["Simulated Email Log"]
```

## Repositories In This Workspace

| Folder | Component |
| --- | --- |
| `aster-pump-aftercare-frontend` | React chat UI served by Nginx |
| `aster-pump-aftercare-backend` | FastAPI, RAG, model client, MCP client, and legacy LangGraph training workflow |
| `aster-pump-aftercare-model` | Ollama model runtime with `qwen3:1.7b` |
| `aster-pump-aftercare-vectordb` | Qdrant vector database |
| `aster-pump-aftercare-db` | PostgreSQL ticket database |
| `aster-pump-aftercare-image-ai-service` | Small image/text analyzer |
| `aster-pump-aftercare-mcp-server` | Official MCP tool server |

## Main Guides

Start here:

```text
DEPLOYMENT_STEPS.md
```

For business-flow code tracing with logs, read:

- `BUSINESS_FLOW_00_TRACE_INDEX.md`
- `BUSINESS_FLOW_01_GENERAL_CHAT.md`
- `BUSINESS_FLOW_02_RAG_MANUAL_QUESTION.md`
- `BUSINESS_FLOW_03_TICKET_LOOKUP.md`
- `BUSINESS_FLOW_04_TEXT_TICKET_CREATION.md`
- `BUSINESS_FLOW_05_IMAGE_TICKET_CREATION.md`

Then read component-specific guides:

- `aster-pump-aftercare-frontend/README.md`
- `aster-pump-aftercare-backend/README.md`
- `aster-pump-aftercare-model/README.md`
- `aster-pump-aftercare-vectordb/README.md`
- `aster-pump-aftercare-db/README.md`
- `aster-pump-aftercare-image-ai-service/README.md`
- `aster-pump-aftercare-mcp-server/README.md`

## Quick Start

```powershell
cd C:\ai-workspace\lama-local-llm\aster-pump
.\bin\build-all-images.ps1
.\bin\deploy-stack.ps1
```

Open:

```text
http://localhost:8080
```

Useful UI tests:

- set email to `customer@example.com`, then ask
  `Create ticket. The display shows E-77 on my AsterPump X17.`
- attach `aster-pump-aftercare-backend/docs/assets/test-images/asterpump_x17_e77_screen.png`
  and type `Create ticket for customer@example.com`
- with **Use manual** checked, ask `What is Bluefin mode?`
- with **Use manual** unchecked, ask `Where is Egypt?`
- ask `List my tickets`
- ask `Get latest ticket status`

## Daily Start And Stop

Start:

```powershell
.\bin\deploy-stack.ps1
```

Stop:

```powershell
.\bin\stop-stack.ps1
```

Check containers:

```powershell
docker compose ps
```

Follow logs:

```powershell
docker compose logs -f
```
