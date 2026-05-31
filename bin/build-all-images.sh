#!/usr/bin/env sh
set -eu

# Build all local Docker images. This script does not start containers.
# The script lives in bin, so it first moves execution to the project root.

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

(cd aster-pump-aftercare-model && ./build-image.sh)
(cd aster-pump-aftercare-vectordb && ./build-image.sh)
(cd aster-pump-aftercare-db && ./build-image.sh)
(cd aster-pump-aftercare-image-ai-service && ./build-image.sh)
(cd aster-pump-aftercare-mcp-server && ./build-image.sh)
(cd aster-pump-aftercare-backend && ./build-image.sh)
(cd aster-pump-aftercare-frontend && ./build-image.sh)
