param(
    [string]$ImageName = "aster-pump-aftercare-vectordb:local"
)

# Build the local Qdrant wrapper image from this component folder.
Push-Location $PSScriptRoot
try {
    docker build -t $ImageName .
}
finally {
    Pop-Location
}
