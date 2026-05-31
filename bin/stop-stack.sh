#!/usr/bin/env sh
set -eu

# Stop and remove the local Docker Compose containers.
# The Ollama volume is kept so the model is not downloaded again.

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
docker compose --project-directory "$PROJECT_ROOT" down
