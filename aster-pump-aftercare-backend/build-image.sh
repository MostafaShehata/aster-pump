#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"
IMAGE_NAME="${1:-aster-pump-aftercare-backend:local}"
docker build -t "$IMAGE_NAME" .
