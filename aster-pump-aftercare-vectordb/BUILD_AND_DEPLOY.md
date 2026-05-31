# Vector DB Build And Deployment

## Build Docker Image

```powershell
cd C:\ai-workspace\lama-local-llm\aster-pump\aster-pump-aftercare-vectordb
.\build-image.ps1
```

Image name:

```text
aster-pump-aftercare-vectordb:local
```

## Create Persistent Volume

```powershell
docker volume create aster-pump-aftercare-qdrant
```

## Deploy In Stack

From root:

```powershell
cd C:\ai-workspace\lama-local-llm\aster-pump
docker compose up -d aster-pump-aftercare-vectordb
```

The backend rebuilds the RAG collection on backend startup, so after changing
manual files, restart backend:

```powershell
docker compose up -d aster-pump-aftercare-backend
```

## Verify Qdrant

```powershell
curl.exe http://localhost:6333/collections
```

Expected:

```json
{"result":{"collections":[{"name":"asterpump_x17_docs"}]},"status":"ok"}
```

If the collection does not exist, start or restart backend because backend
performs the indexing.

## Verify RAG From Backend

```powershell
$body = @{ message='What does error code E-77 mean?'; use_rag=$true } | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri 'http://localhost:8000/api/chat' `
  -ContentType 'application/json' `
  -Body $body
```

Expected answer should mention:

```text
Coolant Loop Pressure Echo
```

## Common Problems

### Qdrant Runs But Has No Collection

Qdrant only stores vectors. It does not read PDF files. Start backend to index:

```powershell
docker compose up -d aster-pump-aftercare-backend
```

### Old Manual Content Appears

The backend rebuilds the collection on startup. Restart backend after editing
manual files.
