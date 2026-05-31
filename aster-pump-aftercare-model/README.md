# Aster Pump Aftercare Model Service

Local LLM runtime for the Aster Pump Aftercare PoC.

This component runs Ollama and pulls a small CPU-friendly model:

```text
qwen3:1.7b
```

## Technology Brief

### Ollama

Ollama runs local language models and exposes an HTTP chat API.

The backend calls:

```text
http://aster-pump-aftercare-model:11434/api/chat
```

From the host machine:

```text
http://localhost:11434/api/chat
```

### Qwen3 1.7B

`qwen3:1.7b` was selected because it is small enough for a CPU-only Docker
Desktop PoC on a 32 GB RAM Windows machine.

It is not the smartest model, but it is realistic for local testing and avoids
large downloads.

## Important Files

| File | Function |
| --- | --- |
| `Dockerfile` | Builds local Ollama wrapper image. |
| `start-ollama.sh` | Starts Ollama and pulls the configured model. |
| `build-image.ps1` | Builds the local Docker image. |

## Code Walkthrough

### Dockerfile Base

```dockerfile
FROM ollama/ollama:latest
```

Explanation:

- Uses the official Ollama image.
- The wrapper adds startup behavior for this PoC.

### Environment Variables

```dockerfile
ENV OLLAMA_HOST=0.0.0.0:11434
ENV OLLAMA_MODEL=qwen3:1.7b
```

Explanation:

- `OLLAMA_HOST` makes Ollama listen inside the container on port `11434`.
- `OLLAMA_MODEL` selects the model pulled during startup.

### Startup Script

```sh
ollama serve &
SERVER_PID="$!"
```

Explanation:

- Starts Ollama in the background.
- Stores the process ID so the script can wait on it later.

```sh
until ollama list >/dev/null 2>&1; do
  sleep 2
done
```

Explanation:

- Waits until Ollama is ready to accept commands.

```sh
if ! ollama list | awk '{print $1}' | grep -qx "$OLLAMA_MODEL"; then
  ollama pull "$OLLAMA_MODEL"
fi
```

Explanation:

- Checks whether the model already exists in the Docker volume.
- Pulls it only when missing.
- This avoids re-downloading on every container restart.

## Build And Deployment

See:

```text
BUILD_AND_DEPLOY.md
```

