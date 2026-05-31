# MCP Package

This package contains the official MCP client used by the backend.

The backend does not call PostgreSQL, image analysis, or email directly. It asks
the MCP server to run tools.

## What Is MCP?

MCP means Model Context Protocol.

It is a standard protocol for exposing tools to AI applications. In this PoC,
the MCP server exposes tools such as:

- `analyze_image`
- `create_ticket`
- `update_technical_steps`
- `send_customer_email`
- `get_ticket`
- `get_latest_ticket_for_customer`

The backend is the MCP client.

## Files

| File | Function |
| --- | --- |
| `client.py` | Official MCP Streamable HTTP client and domain methods. |

## MCP Endpoint

Code:

```python
@property
def endpoint_url(self) -> str:
    return f"{self.server_url}/mcp"
```

Explanation:

- The MCP server base URL is configured as `http://aster-pump-aftercare-mcp-server:8200`.
- The actual MCP protocol endpoint is `/mcp`.
- The final endpoint inside Docker is
  `http://aster-pump-aftercare-mcp-server:8200/mcp`.

## Calling A Tool

Code:

```python
async with streamablehttp_client(self.endpoint_url) as (
    read_stream,
    write_stream,
    _,
):
    async with ClientSession(read_stream, write_stream) as session:
        await session.initialize()
        result = await session.call_tool(name, arguments=arguments)
        return self.parser.parse(result)
```

Explanation:

- `streamablehttp_client(...)` opens an official MCP Streamable HTTP connection.
- `ClientSession(...)` creates an MCP client session.
- `session.initialize()` performs the MCP initialization handshake.
- `session.call_tool(...)` calls one named MCP tool.
- The response is parsed into normal Python data.

## Parsing MCP Tool Responses

Code:

```python
if result.isError:
    error_text = "; ".join(
        content.text
        for content in result.content
        if isinstance(content, types.TextContent)
    )
    raise RuntimeError(error_text or "MCP tool call failed.")
```

Explanation:

- MCP tool calls can return protocol-level errors.
- This block turns those into Python exceptions.
- The API layer can then return a clean HTTP error if needed.

Code:

```python
if result.structuredContent is not None:
    return result.structuredContent
```

Explanation:

- MCP tools may return structured JSON-like content.
- If that exists, the backend uses it directly.

## Image Analysis Tool

Code:

```python
payload = await self.session_client.call_tool(
    "analyze_image",
    {
        "filename": filename,
        "content_base64": base64.b64encode(content).decode("ascii"),
        "content_type": content_type or "application/octet-stream",
    },
)
```

Explanation:

- MCP tool arguments are JSON-compatible.
- Raw bytes are not JSON-compatible.
- The image bytes are converted to base64 text before being sent.

Code:

```python
return [str(item) for item in payload.get("objects", [])]
```

Explanation:

- The MCP server returns an object list.
- The backend normalizes every item into a string.

## Ticket Creation Tool

Code:

```python
return await self.session_client.call_tool(
    "create_ticket",
    {
        "customer_email": customer_email,
        "description": description,
        "detected_objects": detected_objects,
    },
)
```

Explanation:

- The backend asks MCP to create the ticket.
- MCP inserts the record into PostgreSQL.
- The returned dictionary includes the database ticket ID and status.

## Why This Package Exists

This package keeps protocol details out of agents and API routes.

Agents can say:

```python
await self.mcp_client.create_ticket(...)
```

Instead of knowing about:

- MCP sessions
- Streamable HTTP
- tool result parsing
- base64 transport details

