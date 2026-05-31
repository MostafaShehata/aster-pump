# Model Service Build And Deployment

## Build Docker Image

```powershell
cd C:\ai-workspace\lama-local-llm\aster-pump\aster-pump-aftercare-model
.\build-image.ps1
```

Image name:

```text
aster-pump-aftercare-model:local
```

## Create Persistent Volume

The model volume stores downloaded Ollama models:

```powershell
docker volume create aster-pump-aftercare-ollama
```

## Deploy In Stack

From root:

```powershell
cd C:\ai-workspace\lama-local-llm\aster-pump
docker compose up -d aster-pump-aftercare-model
```

First startup may take several minutes because Ollama downloads `qwen3:1.7b`.

## Verify

```powershell
curl.exe http://localhost:11434/api/tags
```

Expected:

```json
{
  "models": [
    {
      "name": "qwen3:1.7b"
    }
  ]
}
```

## Common Problems

### Model Takes Long Time On First Run

That is expected. The first run downloads the model into:

```text
aster-pump-aftercare-ollama
```

Later restarts reuse the volume.

### Backend Chat Is Slow

This is CPU-only. Keep prompts short and use small `num_predict` values in the
backend model client.
