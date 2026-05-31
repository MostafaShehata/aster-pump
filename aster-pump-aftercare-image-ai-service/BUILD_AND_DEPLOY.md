# Image AI Service Build And Deployment

## Build Docker Image

```powershell
cd C:\ai-workspace\lama-local-llm\aster-pump\aster-pump-aftercare-image-ai-service
.\build-image.ps1
```

Image name:

```text
aster-pump-aftercare-image-ai-service:local
```

## Deploy In Stack

From the root folder:

```powershell
cd C:\ai-workspace\lama-local-llm\aster-pump
docker compose up -d aster-pump-aftercare-image-ai-service
```

If MCP/backend are already running and depend on image analysis, restart them:

```powershell
docker compose up -d aster-pump-aftercare-mcp-server aster-pump-aftercare-backend
```

## Verify Health

```powershell
curl.exe http://localhost:8100/health
```

Expected:

```json
{"status":"ok","service":"image-ai"}
```

## Verify Analyze Endpoint

```powershell
curl.exe -X POST http://localhost:8100/analyze-image `
  -F "file=@C:\ai-workspace\lama-local-llm\aster-pump\aster-pump-aftercare-backend\docs\assets\test-images\asterpump_x17_e77_screen.png"
```

Expected:

```json
{"objects":["AsterPump X17","E-77"]}
```

## Browser Test

Open:

```text
http://localhost:8100/test
```

Upload one of:

- `asterpump_x17_e41_screen.png`
- `asterpump_x17_e77_screen.png`
- `asterpump_x17_e93_screen.png`

## Common Problems

### CORS Error

Use:

```text
http://localhost:8100/test
```

The app also allows local testing from a file-opened HTML page, but serving it
from `/test` is cleaner.
