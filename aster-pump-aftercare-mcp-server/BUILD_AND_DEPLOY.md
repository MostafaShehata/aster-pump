# MCP Server Build And Deployment

## Build Docker Image

```powershell
cd C:\ai-workspace\lama-local-llm\aster-pump\aster-pump-aftercare-mcp-server
.\build-image.ps1
```

Image name:

```text
aster-pump-aftercare-mcp-server:local
```

## Deploy In Stack

MCP depends on DB and Image AI service.

From root:

```powershell
cd C:\ai-workspace\lama-local-llm\aster-pump
docker compose up -d aster-pump-aftercare-db aster-pump-aftercare-image-ai-service
docker compose up -d aster-pump-aftercare-mcp-server
```

## Verify Health

```powershell
curl.exe http://localhost:8200/health
```

Expected:

```json
{"status":"ok","service":"mcp-server","protocol":"mcp"}
```

## Verify Through Backend

The MCP endpoint is not a normal browser page. The best verification is an
end-to-end ticket request through the backend/frontend.

```powershell
curl.exe -X POST http://localhost:8080/api/support/tickets `
  -F "customer_email=mcp-test@example.com" `
  -F "description=The display shows E-77" `
  -F "photo=@C:\ai-workspace\lama-local-llm\aster-pump\aster-pump-aftercare-backend\docs\assets\test-images\asterpump_x17_e77_screen.png"
```

Expected:

- ticket is created
- status is `completed`
- detected error is `E-77`
- `email_sent` is `true`

## Common Problems

### Backend Cannot Call MCP

Check that backend environment variable points to the base server URL:

```text
MCP_SERVER_URL=http://aster-pump-aftercare-mcp-server:8200
```

The backend appends `/mcp` in code.

### MCP Healthy But Ticket Fails

Check dependencies:

```powershell
docker compose ps aster-pump-aftercare-db
docker compose ps aster-pump-aftercare-image-ai-service
```
