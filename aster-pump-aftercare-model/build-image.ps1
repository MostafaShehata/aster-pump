param(
    [string]$ImageName = "aster-pump-aftercare-model:local"
)

Push-Location $PSScriptRoot
try {
    docker build -t $ImageName .
}
finally {
    Pop-Location
}
