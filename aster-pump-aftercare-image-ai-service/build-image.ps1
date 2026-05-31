param(
    [string]$ImageName = "aster-pump-aftercare-image-ai-service:local"
)

Push-Location $PSScriptRoot
try {
    docker build -t $ImageName .
}
finally {
    Pop-Location
}
