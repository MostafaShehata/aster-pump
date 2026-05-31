# Aster Pump Aftercare

Local Docker Desktop proof of concept for an after-purchase support system.

The system demonstrates:

- simple customer support UI
- chat UI for manual questions and general questions
- FastAPI backend
- LangGraph agent orchestration
- official MCP protocol tool server
- local CPU-only LLM through Ollama
- RAG with Qdrant
- PostgreSQL ticket storage
- small Image AI service

## Business Use Cases

Aster Pump Aftercare is a fictional after-purchase support desk for the
`AsterPump X17` product. The PoC demonstrates two customer journeys.

### Use Case 1: Open A Support Ticket

A customer has a visible error on the pump display. Instead of writing a long
support request, the customer uploads a photo and enters an email address.

Business outcome:

- the system detects visible product/error information from the image
- a support ticket is created in the database
- technical troubleshooting steps are selected from the product manual
- a reply is prepared and marked as sent by the email tool
- the customer can check the latest ticket status from the UI

Component flow:

```mermaid
sequenceDiagram
    participant User as Customer
    participant UI as React UI + Nginx
    participant API as FastAPI Backend
    participant Graph as LangGraph Agents
    participant MCP as MCP Server
    participant IMG as Image AI Service
    participant DB as PostgreSQL
    participant RAG as Qdrant RAG
    participant Mail as Simulated Email

    User->>UI: Upload error photo and email
    UI->>API: POST /api/support/tickets
    API->>Graph: Start aftercare workflow
    Graph->>MCP: analyze_image tool
    MCP->>IMG: Send uploaded image
    IMG-->>MCP: Return labels, for example E-77
    Graph->>MCP: create_ticket tool
    MCP->>DB: Insert support ticket
    Graph->>RAG: Retrieve manual steps for detected issue
    Graph->>MCP: update_technical_steps tool
    MCP->>DB: Store technical steps
    Graph->>MCP: send_customer_email tool
    MCP->>Mail: Write simulated email log
    MCP->>DB: Mark ticket completed
    API-->>UI: Return ticket result
```

The backend uses three LangGraph agents for this journey:

- Customer Service Agent: analyzes the image through MCP and opens the ticket.
- Technical Assistant Agent: searches the manual through RAG and writes steps.
- Reply Agent: prepares the customer response and calls the email tool.

### Use Case 2: Ask The Model

A customer or support user can ask questions without opening a ticket. This is
useful for quick product-help questions or general model questions.

Business outcome:

- when **Use Aster manual** is checked, the answer is grounded in the local
  Aster Pump manual through RAG
- when **Use Aster manual** is unchecked, the backend asks the local model
  directly for a general answer
- no ticket is created for chat-only questions

Component flow:

```mermaid
sequenceDiagram
    participant User as Customer
    participant UI as React UI + Nginx
    participant API as FastAPI Backend
    participant RAG as Qdrant Vector DB
    participant Model as Ollama qwen3:1.7b

    User->>UI: Ask a question
    UI->>API: POST /api/chat
    alt Use Aster manual is checked
        API->>RAG: Search embedded manual chunks
        RAG-->>API: Return relevant manual context
        API->>Model: Ask with retrieved context
    else Use Aster manual is unchecked
        API->>Model: Ask direct general question
    end
    Model-->>API: Return answer
    API-->>UI: Show answer and sources when RAG was used
```

Examples:

- Manual/RAG question: `What is Bluefin mode?`
- General model question: `Where is Egypt?`

## System Map

```mermaid
flowchart LR
    User["User Browser"] --> Frontend["Frontend\nReact + Nginx\nlocalhost:8080"]
    Frontend --> Backend["Backend\nFastAPI + LangGraph\nlocalhost:8000"]
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
| `aster-pump-aftercare-frontend` | React UI served by Nginx |
| `aster-pump-aftercare-backend` | FastAPI, LangGraph, RAG, model client, MCP client |
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

Then read component-specific guides:

- `aster-pump-aftercare-frontend/README.md`
- `aster-pump-aftercare-backend/README.md`
- `aster-pump-aftercare-model/README.md`
- `aster-pump-aftercare-vectordb/README.md`
- `aster-pump-aftercare-db/README.md`
- `aster-pump-aftercare-image-ai-service/README.md`
- `aster-pump-aftercare-mcp-server/README.md`

Each repo also has:

```text
BUILD_AND_DEPLOY.md
```

## Operational Scripts

Scripts are kept in `bin`.

| Script | Function |
| --- | --- |
| `bin/build-all-images.ps1` | Builds all local Docker images. |
| `bin/deploy-stack.ps1` | Starts the Docker Compose stack. |
| `bin/stop-stack.ps1` | Stops the stack. |
| `bin/generate-user-guide.py` | Regenerates the fictional PDF manual. |
| `bin/generate-error-test-images.py` | Regenerates `E-41`, `E-77`, and `E-93` screen images. |

Script details are documented in:

```text
bin/README.md
```

## Quick Start

```powershell
cd C:\ai-workspace\lama-local-llm\aster-pump
docker volume create aster-pump-aftercare-ollama
docker volume create aster-pump-aftercare-qdrant
docker volume create aster-pump-aftercare-postgres
.\bin\build-all-images.ps1
.\bin\deploy-stack.ps1
```

Open:

```text
http://localhost:8080
```

Useful UI tests:

- With **Use Aster manual** checked, ask `What is Bluefin mode?`
- With **Use Aster manual** unchecked, ask `Where is Egypt?`
- Upload `asterpump_x17_e77_screen.png` to test the ticket workflow.

## Daily Start And Stop

Use these commands after the images and volumes already exist.

Start the full stack:

```powershell
cd C:\ai-workspace\lama-local-llm\aster-pump
.\bin\deploy-stack.ps1
```

Equivalent Docker command:

```powershell
docker compose up -d
```

Stop the full stack:

```powershell
.\bin\stop-stack.ps1
```

Equivalent Docker command:

```powershell
docker compose down
```

Check running containers:

```powershell
docker compose ps
```

Follow logs:

```powershell
docker compose logs -f
```

Follow the main demo story lines only:

```powershell
docker compose logs -f | Select-String -Pattern "FRONTEND \||BACKEND \||MCP \||IMAGE-AI \||MODEL \|"
```

Stopping the stack removes containers, but keeps the named Docker volumes. That
means the Ollama model files, Qdrant vectors, and PostgreSQL tickets stay on
your machine for the next start.
