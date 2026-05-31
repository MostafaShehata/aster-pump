# Frontend Build And Deployment

## Build React Locally

PowerShell:

```powershell
cd C:\ai-workspace\lama-local-llm\aster-pump\aster-pump-aftercare-frontend
.\build-app.ps1
```

What happens:

1. `npm install` installs or refreshes local dependencies.
2. `npm run build` runs Vite.
3. Static files are written to `dist`.

## Build Docker Image

```powershell
.\build-image.ps1
```

What happens:

1. `build-app.ps1` is called.
2. Docker builds `aster-pump-aftercare-frontend:local`.
3. The Dockerfile copies `dist` into Nginx.

## Deploy In Stack

From the root folder:

```powershell
cd C:\ai-workspace\lama-local-llm\aster-pump
docker compose up -d aster-pump-aftercare-frontend
```

## Verify

```powershell
curl.exe -I http://localhost:8080
```

Expected:

```text
HTTP/1.1 200 OK
```

Open:

```text
http://localhost:8080
```

## Common Problems

### HTTP 413 When Uploading Image

Nginx upload size is controlled in `nginx.conf`:

```nginx
client_max_body_size 10m;
```

Increase this if larger test images are needed.

### UI Does Not Show Latest Changes

Rebuild the app and image:

```powershell
.\build-image.ps1
docker compose up -d aster-pump-aftercare-frontend
```
