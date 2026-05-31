# Build all local Docker images. This script does not start containers.
# The script lives in bin, so it first moves execution to the project root.

$projectRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")

Push-Location $projectRoot
try {
    Push-Location .\aster-pump-aftercare-model
    .\build-image.ps1
    Pop-Location

    Push-Location .\aster-pump-aftercare-vectordb
    .\build-image.ps1
    Pop-Location

    Push-Location .\aster-pump-aftercare-db
    .\build-image.ps1
    Pop-Location

    Push-Location .\aster-pump-aftercare-image-ai-service
    .\build-image.ps1
    Pop-Location

    Push-Location .\aster-pump-aftercare-mcp-server
    .\build-image.ps1
    Pop-Location

    Push-Location .\aster-pump-aftercare-backend
    .\build-image.ps1
    Pop-Location

    Push-Location .\aster-pump-aftercare-frontend
    .\build-image.ps1
    Pop-Location
}
finally {
    Pop-Location
}
