# Bin Scripts

Operational helper scripts for the Aster Pump Aftercare workspace.

These scripts are intentionally kept outside the component folders because they
operate on the full solution.

## Scripts

| Script | Function |
| --- | --- |
| `build-all-images.ps1` | Builds every local Docker image in the correct order. |
| `deploy-stack.ps1` | Starts the full Docker Compose stack. |
| `stop-stack.ps1` | Stops the full Docker Compose stack. |
| `generate-user-guide.py` | Regenerates the fictional Aster Pump X17 PDF guide. |
| `generate-error-test-images.py` | Regenerates image test samples for `E-41`, `E-77`, and `E-93`. |

Unix-style `.sh` equivalents are included where useful.

## Code Walkthrough

### Build All Images

```powershell
$projectRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
```

Explanation:

- `$PSScriptRoot` is the `bin` folder.
- `Join-Path $PSScriptRoot ".."` moves one folder up to the project root.
- This lets the script work no matter where PowerShell was opened.

```powershell
Push-Location .\aster-pump-aftercare-backend
.\build-image.ps1
Pop-Location
```

Explanation:

- Enters a component folder.
- Runs that component build script.
- Returns to the previous folder.

### Deploy Stack

```powershell
docker compose --project-directory $projectRoot up -d
```

Explanation:

- Starts the Compose stack from the project root.
- `-d` means detached mode.
- Starts all services defined in `docker-compose.yml`.

### Stop Stack

```powershell
docker compose --project-directory $projectRoot down
```

Explanation:

- Stops and removes containers.
- Named volumes are preserved.
- Ollama model files, Qdrant vectors, and PostgreSQL data remain available for
  the next start.

## Recommended Use

From the root folder:

```powershell
.\bin\build-all-images.ps1
.\bin\deploy-stack.ps1
```

For normal daily usage after the first build:

```powershell
.\bin\deploy-stack.ps1
docker compose ps
.\bin\stop-stack.ps1
```
