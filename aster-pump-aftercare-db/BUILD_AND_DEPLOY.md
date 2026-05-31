# Database Build And Deployment

## Build Docker Image

```powershell
cd C:\ai-workspace\lama-local-llm\aster-pump\aster-pump-aftercare-db
.\build-image.ps1
```

Image name:

```text
aster-pump-aftercare-db:local
```

## Create Persistent Volume

The root scripts normally create required volumes. Manual command:

```powershell
docker volume create aster-pump-aftercare-postgres
```

## Deploy In Stack

From root:

```powershell
cd C:\ai-workspace\lama-local-llm\aster-pump
docker compose up -d aster-pump-aftercare-db
```

## Verify

```powershell
docker compose ps aster-pump-aftercare-db
```

Expected status:

```text
healthy
```

## Important Volume Note

`init.sql` runs only when the PostgreSQL volume is first created.

If you change `init.sql` after the volume exists, the running database will not
automatically apply those changes. For local PoC reset only, remove and recreate
the volume.
