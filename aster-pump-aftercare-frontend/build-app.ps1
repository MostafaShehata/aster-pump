param(
    [string]$Configuration = "production"
)

# Build only the React frontend application.
# This does not build a Docker image and does not start any container.
#
# Output folder:
#   dist

Push-Location $PSScriptRoot
try {
    npm install
    npm run build
}
finally {
    Pop-Location
}
