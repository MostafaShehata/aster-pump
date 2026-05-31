# Aster Pump Aftercare MCP Server

Official MCP protocol server for the Aster Pump Aftercare PoC.

The MCP server is the tool gateway. It owns integration with:

- Image AI service
- PostgreSQL ticket database
- simulated email sending
- ticket lookup

The backend agents call this server through the official MCP client.

## Technology Brief

### MCP Python SDK

The server uses:

```python
from mcp.server.fastmcp import FastMCP
```

MCP gives the backend a standard way to call tools.

### Streamable HTTP

The MCP endpoint is:

```text
http://localhost:8200/mcp
```

Streamable HTTP is used because the backend and MCP server are separate Docker
containers.

### PostgreSQL And HTTPX

- `psycopg` connects to PostgreSQL.
- `httpx` calls the Image AI service.

## Important Files

| File | Function |
| --- | --- |
| `app/main.py` | FastMCP tools and ASGI app. |
| `app/database.py` | PostgreSQL repository. |
| `app/image_tool.py` | Calls Image AI service. |
| `app/config.py` | Runtime settings. |
| `mcp-config.json` | Human-readable tool manifest. |
| `requirements.txt` | Python dependencies. |

## Code Walkthrough

### FastMCP Server

```python
mcp = FastMCP(
    name="Aster Pump Aftercare MCP Server",
    stateless_http=True,
    json_response=True,
)
```

Explanation:

- Creates the MCP server.
- `stateless_http=True` works well for simple service-to-service calls.
- `json_response=True` returns JSON responses for HTTP transport.

### MCP Tool: Analyze Image

```python
@mcp.tool()
async def analyze_image(
    filename: str,
    content_base64: str,
    content_type: str = "application/octet-stream",
) -> dict:
```

Explanation:

- `@mcp.tool()` exposes this function as an MCP tool.
- MCP tool arguments must be JSON-compatible.
- Image bytes arrive as base64 text.

```python
content = base64.b64decode(content_base64)
objects = await image_analyzer_tool.analyze(
    filename=filename or "uploaded-photo",
    content=content,
    content_type=content_type,
)
```

Explanation:

- Converts base64 back to bytes.
- Calls the Image AI service.
- Returns detected labels such as `AsterPump X17` and `E-77`.

### MCP Tool: Create Ticket

```python
@mcp.tool()
def create_ticket(
    customer_email: str,
    description: str,
    detected_objects: list,
) -> dict:
```

Explanation:

- Exposes ticket creation as an MCP tool.
- The backend agent calls this after image analysis.

```python
return ticket_repository.create_ticket(
    customer_email=customer_email,
    description=description,
    detected_objects=detected_objects,
)
```

Explanation:

- The MCP server delegates database work to `TicketRepository`.
- The backend remains free of direct DB code.

### Simulated Email Tool

```python
with LOG_PATH.open("a", encoding="utf-8") as log_file:
    log_file.write(json.dumps(record) + "\n")
```

Explanation:

- Email is simulated by writing to a log file.
- A real system could replace this with SMTP, SendGrid, or Microsoft Graph.

### ASGI App

```python
app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        Mount("/", app=mcp.streamable_http_app()),
    ],
    lifespan=lifespan,
)
```

Explanation:

- `/health` is for Docker health checks.
- The MCP protocol app is mounted at `/mcp`.

## Build And Deployment

See:

```text
BUILD_AND_DEPLOY.md
```

