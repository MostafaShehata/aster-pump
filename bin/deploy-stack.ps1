# Start the full local Docker Compose stack.
# Build images first with:
#   .\bin\build-all-images.ps1

$projectRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
docker compose --project-directory $projectRoot up -d
