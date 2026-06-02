# Business Flow Trace Index

These files explain the current chat-first Aster Pump Aftercare PoC from the
browser to the backend, LLM, MCP server, image analyzer, RAG, PostgreSQL, and
back to the UI.

Read them in this order:

| File | Business flow |
| --- | --- |
| `BUSINESS_FLOW_01_GENERAL_CHAT.md` | User asks a general question such as `Where is Egypt?` |
| `BUSINESS_FLOW_02_RAG_MANUAL_QUESTION.md` | User asks an Aster manual question such as `What is Bluefin mode?` |
| `BUSINESS_FLOW_03_TICKET_LOOKUP.md` | User asks `List my tickets` or `Get latest ticket status` |
| `BUSINESS_FLOW_04_TEXT_TICKET_CREATION.md` | User creates a ticket from typed text |
| `BUSINESS_FLOW_05_IMAGE_TICKET_CREATION.md` | User creates a ticket from an uploaded error image |

## Important Safety Concept

When these documents say "the LLM calls MCP", the exact implementation is:

1. The backend sends a planning prompt to Ollama.
2. Ollama returns JSON with `action=tool_call`, `tool_name`, and `arguments`.
3. The backend validates the tool name and arguments.
4. The backend uses the official MCP client to call the MCP server.

So the LLM decides the tool, but backend code executes the tool.

## Main Code Files

| Component | File |
| --- | --- |
| React UI | `aster-pump-aftercare-frontend/src/main.tsx` |
| Backend API route | `aster-pump-aftercare-backend/app/api/routes.py` |
| LLM agent and prompt | `aster-pump-aftercare-backend/app/model/chat_client.py` |
| Backend MCP client | `aster-pump-aftercare-backend/app/mcp/client.py` |
| MCP tool server | `aster-pump-aftercare-mcp-server/app/main.py` |
| RAG service | `aster-pump-aftercare-backend/app/rag/service.py` |
| Image analyzer | `aster-pump-aftercare-image-ai-service/app/main.py` and `app/analyzer.py` |

## Logs Command

Use this command to watch the story across all containers:

```powershell
docker compose logs -f
```

Useful focused filter:

```powershell
docker compose logs -f | Select-String -Pattern "story.chat-upload|story.llm-agent|story.rag|story.mcp-client|story.mcp.tool|story.image-ai"
```
