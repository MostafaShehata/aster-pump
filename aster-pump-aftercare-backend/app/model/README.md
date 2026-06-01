# Model Package

This package contains the chat LLM agent.

The backend talks to the local model through Ollama, but chat is no longer just
"send question, get answer." The model can now decide to request approved MCP
tools. The backend validates and executes the tool request, then asks the model
to produce the final user-facing answer.

## Files

| File | Function |
| --- | --- |
| `chat_client.py` | LLM tool planner, MCP tool executor, final prompt builder, and Ollama client. |

## Main Flow

1. `OllamaChatService.chat(...)` receives a `ChatRequest`.
2. RAG context is retrieved when `use_rag=true`.
3. `ChatToolPlanner` asks Ollama for a JSON decision.
4. If the decision is `tool_call`, `McpToolExecutor` calls MCP.
5. `PromptBuilder` builds final messages with the compact tool result.
6. Ollama writes the final reply.

## Tool Decision

Code:

```python
content = await self.ollama_client.chat(
    messages,
    temperature=0,
    response_format="json",
    num_predict=256,
)
decision = self.parse_decision(content)
```

Explanation:

- The first LLM call is a planning call.
- `response_format="json"` asks Ollama for JSON.
- The model chooses either `answer` or `tool_call`.
- The backend parses and validates the model decision.

Example model decision:

```json
{
  "action": "tool_call",
  "tool_name": "get_tickets_for_customer",
  "arguments": {
    "customer_email": "llm-agent-demo@example.com"
  },
  "reason": "The user asked for their ticket list."
}
```

## Approved MCP Tools

The chat agent allows only these tools:

```python
TOOL_CATALOG = {
    "get_ticket": {...},
    "get_latest_ticket_for_customer": {...},
    "get_tickets_for_customer": {...},
}
```

Explanation:

- The model cannot call arbitrary MCP tools.
- The backend rejects unsupported tool names.
- Missing required arguments make the assistant ask the user for more info.

## MCP Execution

Code:

```python
if tool_name == "get_tickets_for_customer":
    result = await self.mcp_client.get_tickets_for_customer(str(arguments["customer_email"]))
```

Explanation:

- The LLM requested the tool.
- The backend executes it through the official MCP client.
- MCP reads PostgreSQL and returns ticket data.

## Compact Tool Results

Code:

```python
return {
    "id": ticket.get("id"),
    "customer_email": ticket.get("customer_email"),
    "status": ticket.get("status"),
    "detected_error_code": ticket.get("detected_error_code"),
    "email_sent": ticket.get("email_sent"),
    "created_at": ticket.get("created_at"),
    "completed_at": ticket.get("completed_at"),
}
```

Explanation:

- Tickets can contain long troubleshooting text and email bodies.
- The tiny CPU model is much faster when it receives only summary fields.
- The full database row remains in MCP/PostgreSQL, but the final LLM prompt is compact.

## Final Answer

Code:

```python
messages = self.prompt_builder.build_tool_result_messages(
    request=request,
    decision=decision,
    tool_result=tool_result,
    rag_context=rag_result.context,
)
reply = await self.ollama_client.chat(messages, temperature=0.1, num_predict=192)
```

Explanation:

- The second LLM call writes the final answer.
- The model sees the MCP tool name, arguments, and compact result.
- The response is returned to the frontend as `ChatResponse`.

## Example

User:

```text
Get me list of my tickets for llm-agent-demo@example.com
```

Result:

```text
Ticket ID: 10
Status: Completed
Error Code: E-77
Email Sent: Yes
```
