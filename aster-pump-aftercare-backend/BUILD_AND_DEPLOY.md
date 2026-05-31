# Backend Build And Deployment

## Build Docker Image

```powershell
cd C:\ai-workspace\lama-local-llm\aster-pump\aster-pump-aftercare-backend
.\build-image.ps1
```

Image name:

```text
aster-pump-aftercare-backend:local
```

## Dependencies

Backend requires these services:

- model service: Ollama chat
- vector DB: Qdrant RAG storage
- MCP server: tools for image analysis, DB, and email

Docker Compose handles startup order.

## Deploy In Stack

From root:

```powershell
cd C:\ai-workspace\lama-local-llm\aster-pump
docker compose up -d aster-pump-aftercare-backend
```

If dependencies are not already running:

```powershell
docker compose up -d aster-pump-aftercare-model aster-pump-aftercare-vectordb aster-pump-aftercare-mcp-server
docker compose up -d aster-pump-aftercare-backend
```

## Verify Health

```powershell
curl.exe http://localhost:8000/api/health
```

Expected:

```json
{"status":"ok","service":"backend"}
```

## Verify RAG Chat

```powershell
$body = @{ message='What does E-77 mean for Aster Pump X17?'; use_rag=$true } | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri 'http://localhost:8000/api/chat' `
  -ContentType 'application/json' `
  -Body $body
```

Expected answer should mention:

```text
Coolant Loop Pressure Echo
```

## Verify Ticket Flow

```powershell
curl.exe -X POST http://localhost:8000/api/support/tickets `
  -F "customer_email=backend-test@example.com" `
  -F "description=The display shows E-77" `
  -F "photo=@C:\ai-workspace\lama-local-llm\aster-pump\aster-pump-aftercare-backend\docs\assets\test-images\asterpump_x17_e77_screen.png"
```

Text-only supervisor route:

```powershell
curl.exe -X POST http://localhost:8000/api/support/tickets `
  -F "customer_email=backend-text-test@example.com" `
  -F "description=The display shows E-77 on my AsterPump X17"
```

Expected:

- `status` is `completed`
- `detected_error_code` is `E-77`
- `email_sent` is `true`

## What Happens On Startup

Backend startup calls:

```text
app.rag.service.rag_service.ensure_index()
```

That rebuilds the Qdrant collection from files in:

```text
docs
```

## Common Problems

### Backend Healthy But Chat Fails

Check model service:

```powershell
curl.exe http://localhost:11434/api/tags
```

### Ticket Flow Fails

Check MCP and Image AI:

```powershell
curl.exe http://localhost:8200/health
curl.exe http://localhost:8100/health
```
