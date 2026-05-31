#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"

IMAGE_NAME="${1:-aster-pump-aftercare-frontend:local}"

# Build React outside Docker, then package dist into Nginx.
./build-app.sh
docker build -t "$IMAGE_NAME" .
