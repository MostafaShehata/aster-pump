#!/usr/bin/env sh
set -eu

# Start the full local Docker Compose stack.
# Build images first with:
#   ./bin/build-all-images.sh

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
docker compose --project-directory "$PROJECT_ROOT" up -d
