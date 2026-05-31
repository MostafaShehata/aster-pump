#!/usr/bin/env sh
set -eu

# Build the local Qdrant wrapper image from this component folder.
IMAGE_NAME="${1:-aster-pump-aftercare-vectordb:local}"
docker build -t "$IMAGE_NAME" .
