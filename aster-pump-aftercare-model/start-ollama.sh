#!/usr/bin/env sh
set -eu

echo "$(date -Iseconds) | MODEL | startup | starting Ollama server for model ${OLLAMA_MODEL}"

# Start Ollama in the background so the selected model can be pulled on first run.
ollama serve &
SERVER_PID="$!"

# Wait until the local Ollama API is ready.
echo "$(date -Iseconds) | MODEL | startup | waiting for Ollama API"
until ollama list >/dev/null 2>&1; do
  sleep 2
done
echo "$(date -Iseconds) | MODEL | startup | Ollama API is ready"

# Pull the configured tiny model only if it is not already present in the volume.
if ! ollama list | awk '{print $1}' | grep -qx "$OLLAMA_MODEL"; then
  echo "$(date -Iseconds) | MODEL | model | pulling ${OLLAMA_MODEL} into persistent volume"
  ollama pull "$OLLAMA_MODEL"
  echo "$(date -Iseconds) | MODEL | model | pull completed for ${OLLAMA_MODEL}"
else
  echo "$(date -Iseconds) | MODEL | model | ${OLLAMA_MODEL} already exists in persistent volume"
fi

echo "$(date -Iseconds) | MODEL | startup | model service ready on ${OLLAMA_HOST}"
wait "$SERVER_PID"
