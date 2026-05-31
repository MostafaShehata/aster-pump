param(
    [string]$ImageName = "aster-pump-aftercare-backend:local"
)

Push-Location $PSScriptRoot
try {
    docker build -t $ImageName .
}
finally {
    Pop-Location
}
