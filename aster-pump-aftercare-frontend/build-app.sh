#!/usr/bin/env sh
set -eu

# Build only the React frontend application.
# This does not build a Docker image and does not start any container.

cd "$(dirname "$0")"
npm install
npm run build
