# Agents Package

This package contains the LangGraph workflow.

The backend has three agents:

1. Customer Service Agent
2. Technical Assistant Agent
3. Reply Agent

They run in sequence. Each agent reads and writes the same shared state object.

## What Is LangGraph?

LangGraph is a framework for building workflows with nodes and edges.

In this project:

- a node is one agent function/class
- an edge says which node runs next
- state is the shared dictionary passed between nodes
- the graph is the complete workflow

This PoC uses LangGraph as an orchestrator. The agents do not directly own DB,
email, or image analysis. They call MCP tools for those actions.

## Files

| File | Function |
| --- | --- |
| `state.py` | Defines the shared graph state. |
| `nodes.py` | Contains the three agent classes. |
| `workflow.py` | Builds and runs the LangGraph workflow. |

## Shared State

Code:

```python
class AftercareState(TypedDict, total=False):
    customer_email: str
    description: str
    image_filename: str
    image_content_type: str
    image_bytes: bytes
    detected_objects: list[str]
    detected_error_code: str | None
    ticket_id: int
    technical_steps: str
    reply_subject: str
    reply_body: str
    email_sent: bool
    status: str
```

Explanation:

- `TypedDict` describes the keys expected in the graph state dictionary.
- `total=False` means not every key must exist at the start.
- The API starts with image/customer fields.
- Later agents add ticket fields, technical steps, and email status.

## Customer Service Agent

Code:

```python
class CustomerServiceAgent:
    def __init__(self, mcp_client: AftercareMcpClient) -> None:
        self.mcp_client = mcp_client
```

Explanation:

- The agent receives an `AftercareMcpClient`.
- This makes the agent depend on an interface-like client, not direct DB/image
  code.
- This design is easier to test and easier to replace later.

Code:

```python
detected_objects = await self.mcp_client.analyze_image(
    state["image_filename"],
    state["image_bytes"],
    state.get("image_content_type"),
)
```

Explanation:

- The image is sent to the MCP server.
- MCP calls the Image AI service.
- The response is a list such as `["AsterPump X17", "E-77"]`.

Code:

```python
ticket = await self.mcp_client.create_ticket(
    customer_email=state["customer_email"],
    description=state.get("description", ""),
    detected_objects=detected_objects,
)
```

Explanation:

- The ticket is created through MCP.
- The backend does not connect to PostgreSQL directly.
- The MCP server owns DB operations.

## Technical Assistant Agent

Code:

```python
question = (
    f"Provide after-purchase troubleshooting steps for {issue_terms}. "
    f"Customer description: {state.get('description', '')}"
)
rag_result = rag_service.retrieve_for_question(question)
```

Explanation:

- The agent creates a search question from detected objects and customer text.
- It asks the RAG service for relevant manual chunks.
- RAG searches Qdrant and returns context from the PDF/manual files.

Code:

```python
technical_steps = (
    "Based on the product manual:\n"
    f"{self.summarize_context_for_customer(rag_result.context)}"
)
```

Explanation:

- If RAG returns context, the agent turns it into customer-facing steps.
- This is intentionally simple for the PoC.
- In a stronger version, this agent could call the LLM to summarize the context.

Code:

```python
await self.mcp_client.update_technical_steps(state["ticket_id"], technical_steps)
```

Explanation:

- The generated steps are saved back to the ticket through MCP.
- The MCP server updates PostgreSQL.

## Reply Agent

Code:

```python
subject = f"Support ticket #{state['ticket_id']} troubleshooting steps"
body = (
    f"Hello,\n\n"
    f"We created ticket #{state['ticket_id']} for your product issue.\n\n"
    f"Detected from your photo: {', '.join(state.get('detected_objects', []))}\n\n"
    f"{state['technical_steps']}\n\n"
    "Regards,\nAftercare Support"
)
```

Explanation:

- This agent formats the final customer reply.
- The body includes ticket number, detected objects, and RAG-generated steps.

Code:

```python
email_sent = await self.mcp_client.send_customer_email(
    ticket_id=state["ticket_id"],
    to=state["customer_email"],
    subject=subject,
    body=body,
)
```

Explanation:

- The reply is sent through MCP.
- In this PoC the email is simulated.
- In production the MCP server could call SMTP, SendGrid, or Microsoft Graph.

## Building The Graph

Code:

```python
graph = StateGraph(AftercareState)
graph.add_node("customer_service", CustomerServiceAgent(self.mcp_client))
graph.add_node("technical_assistant", TechnicalAssistantAgent(self.mcp_client))
graph.add_node("reply_agent", ReplyAgent(self.mcp_client))
```

Explanation:

- `StateGraph(AftercareState)` creates a stateful LangGraph workflow.
- `add_node` registers each agent as a named node.
- Names are useful for debugging and graph tracing.

Code:

```python
graph.set_entry_point("customer_service")
graph.add_edge("customer_service", "technical_assistant")
graph.add_edge("technical_assistant", "reply_agent")
graph.add_edge("reply_agent", END)
```

Explanation:

- The workflow starts at `customer_service`.
- Then it runs `technical_assistant`.
- Then it runs `reply_agent`.
- `END` tells LangGraph the workflow is finished.

## Running The Graph

Code:

```python
return await self.graph.ainvoke(
    {
        "customer_email": customer_email,
        "description": description,
        "image_filename": image_filename,
        "image_content_type": image_content_type,
        "image_bytes": image_bytes,
    }
)
```

Explanation:

- `ainvoke` runs the graph asynchronously.
- The dictionary is the initial state.
- Each node returns an updated dictionary.
- The final returned dictionary becomes the API response source.

