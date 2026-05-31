# Stop and remove the local Docker Compose containers.
# The Ollama volume is kept so the model is not downloaded again.

$projectRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
docker compose --project-directory $projectRoot down
