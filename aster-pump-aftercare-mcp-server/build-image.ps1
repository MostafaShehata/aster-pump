param(
    [string]$ImageName = "aster-pump-aftercare-mcp-server:local"
)

Push-Location $PSScriptRoot
try {
    docker build -t $ImageName .
}
finally {
    Pop-Location
}
