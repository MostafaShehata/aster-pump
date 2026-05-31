param(
    [string]$ImageName = "aster-pump-aftercare-frontend:local"
)

Push-Location $PSScriptRoot
try {
    # Build React outside Docker, then package dist into Nginx.
    .\build-app.ps1
    docker build -t $ImageName .
}
finally {
    Pop-Location
}
