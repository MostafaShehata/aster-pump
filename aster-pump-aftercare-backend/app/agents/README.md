# Agents Package

This package contains the LangGraph supervisor workflow for the aftercare
support-ticket journey.

The goal of this package is to decide what work must happen, run the correct
agents in the correct order, and return one final state to the API layer.

## Agent List

| Agent | Runs When | Main Job |
| --- | --- | --- |
| `SupervisorAgent` | Always first | Decides whether the request should use image intake or text intake. |
| `CustomerServiceAgent` | Image exists | Sends image to MCP image tool, receives detected labels, creates ticket. |
| `TextCustomerServiceAgent` | Text only | Extracts simple text labels, creates ticket without image analysis. |
| `TechnicalAssistantAgent` | After ticket creation | Uses RAG to find manual troubleshooting steps and stores them on the ticket. |
| `ReplyAgent` | Last | Builds the customer reply and calls the MCP email tool. |

The important design idea is this:

```text
Supervisor chooses the route.
Worker agents do the task.
MCP owns external tools.
RAG owns manual knowledge.
The API only starts the workflow and maps the final response.
```

## Package Files

| File | Function |
| --- | --- |
| `state.py` | Defines the shared state dictionary used by all graph nodes. |
| `nodes.py` | Contains the supervisor and worker agent classes. |
| `workflow.py` | Builds the LangGraph graph and defines dynamic routing. |

## What Is LangGraph?

LangGraph is a workflow library for stateful agent systems.

In this project:

- a **node** is one agent class
- an **edge** tells LangGraph what node can run next
- a **conditional edge** lets the graph choose the next node from state
- **state** is a shared dictionary passed from node to node
- the **compiled graph** is the runnable workflow

This is different from one simple function calling another. LangGraph gives the
workflow a clear structure:

```text
supervisor
  -> image_customer_service OR text_customer_service
  -> technical_assistant
  -> reply_agent
  -> END
```

## Shared State

Code from `state.py`:

```python
from typing import Literal, TypedDict


class AftercareState(TypedDict, total=False):
    """Shared state passed between the supervisor and worker agents."""

    customer_email: str
    description: str
    intake_route: Literal["image_intake", "text_intake"]
    image_filename: str
    image_content_type: str
    image_bytes: bytes
    has_image: bool
    has_text: bool
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

- `TypedDict` documents the shape of the graph state.
- `total=False` means the graph does not require every key at the beginning.
- The API starts with `customer_email`, optional `description`, and optional
  image fields.
- The supervisor adds `intake_route`, `has_image`, and `has_text`.
- Intake agents add `detected_objects`, `detected_error_code`, `ticket_id`, and
  first ticket `status`.
- The technical agent adds `technical_steps`.
- The reply agent adds `reply_subject`, `reply_body`, `email_sent`, and final
  `status`.

## Supervisor Agent

Code from `nodes.py`:

```python
class SupervisorAgent:
    """Routes the request to the correct intake agent based on available input."""

    def __call__(self, state: AftercareState) -> AftercareState:
        description = state.get("description", "").strip()
        has_image = bool(state.get("image_bytes"))
        has_text = bool(description)

        if not has_image and not has_text:
            raise ValueError("Request must include an image, text description, or both.")

        route = "image_intake" if has_image else "text_intake"
        logging.info(
            "agent.supervisor | routed request route=%s has_image=%s has_text=%s",
            route,
            has_image,
            has_text,
        )
        return {
            **state,
            "intake_route": route,
            "has_image": has_image,
            "has_text": has_text,
            "status": "routed",
        }
```

Line-by-line idea:

- `description = ...strip()` normalizes the text input.
- `has_image = bool(state.get("image_bytes"))` checks whether a file was
  uploaded.
- `has_text = bool(description)` checks whether the user wrote anything useful.
- The `ValueError` protects the workflow from empty requests.
- `route = "image_intake" if has_image else "text_intake"` is the routing
  decision.
- The returned dictionary keeps the old state with `**state` and adds routing
  metadata.

The supervisor does not create tickets, call the model, search RAG, or send
email. It only decides what should happen next.

## Image Customer Service Agent

This agent runs when the request contains an image. It is the image-aware
intake path.

Code:

```python
class CustomerServiceAgent:
    """Analyzes an uploaded image and opens the support ticket."""

    def __init__(self, mcp_client: AftercareMcpClient) -> None:
        self.mcp_client = mcp_client
```

Explanation:

- The agent receives `AftercareMcpClient`.
- It does not know HTTP details, PostgreSQL details, or Image AI service
  details.
- It only knows that MCP exposes a tool named `analyze_image` and a tool named
  `create_ticket`.

Code:

```python
detected_objects = await self.mcp_client.analyze_image(
    state["image_filename"],
    state["image_bytes"],
    state.get("image_content_type"),
)
```

Explanation:

- The image bytes are sent to the MCP server.
- MCP forwards them to the Image AI service.
- The Image AI service returns labels such as `["AsterPump X17", "E-77"]`.

Code:

```python
ticket = await self.mcp_client.create_ticket(
    customer_email=state["customer_email"],
    description=state.get("description", ""),
    detected_objects=detected_objects,
)
```

Explanation:

- Ticket creation is also done through MCP.
- The backend agents do not connect to PostgreSQL directly.
- This keeps database ownership inside the MCP server.

Code:

```python
return {
    **state,
    "detected_objects": detected_objects,
    "detected_error_code": ticket.get("detected_error_code"),
    "ticket_id": ticket["id"],
    "status": ticket["status"],
}
```

Explanation:

- The agent returns a new state dictionary.
- The next agent receives the ticket ID and detected issue details.

## Text Customer Service Agent

This agent runs when the request has text but no image. It lets the system open
tickets without requiring a photo.

Code:

```python
class TextCustomerServiceAgent:
    """Creates a ticket from text-only customer input without image analysis."""

    ERROR_PATTERN = re.compile(r"E-?(\d{2,3})(?!\d)", re.IGNORECASE)
```

Explanation:

- The regex finds error codes like `E-77`, `E77`, or `e93`.
- This is intentionally small and deterministic for the PoC.
- A production version could replace this with an LLM classifier or OCR/text
  extraction pipeline.

Code:

```python
def detect_text_objects(self, text: str) -> list[str]:
    """Extract simple product/error labels from a text-only request."""

    objects: list[str] = []
    normalized = text.lower()
    if "asterpump" in normalized or "x17" in normalized:
        objects.append("AsterPump X17")

    for match in self.ERROR_PATTERN.finditer(text):
        digits = re.sub(r"\D", "", match.group(0))
        code = f"E-{digits}"
        if code not in objects:
            objects.append(code)

    return objects or ["text_request"]
```

Explanation:

- The method looks for product words first.
- Then it extracts normalized error codes.
- `objects or ["text_request"]` guarantees ticket creation still has at least
  one label even when no code is found.

Code:

```python
ticket = await self.mcp_client.create_ticket(
    customer_email=state["customer_email"],
    description=description,
    detected_objects=detected_objects,
)
```

Explanation:

- Text-only and image-based tickets use the same MCP DB tool.
- After the ticket is created, the workflow joins the same technical-assistant
  path used by image tickets.

## Technical Assistant Agent

This agent creates troubleshooting steps using the local RAG knowledge base.

Code:

```python
issue_terms = ", ".join(state.get("detected_objects", []))
question = (
    f"Provide after-purchase troubleshooting steps for {issue_terms}. "
    f"Customer description: {state.get('description', '')}"
)
rag_result = rag_service.retrieve_for_question(question)
```

Explanation:

- `detected_objects` came from image analysis or text extraction.
- The agent builds a RAG search question from those objects and the customer
  description.
- `rag_service.retrieve_for_question(...)` searches Qdrant for matching manual
  chunks.

Code:

```python
if rag_result.context:
    technical_steps = (
        "Based on the product manual:\n"
        f"{self.summarize_context_for_customer(rag_result.context)}"
    )
else:
    technical_steps = (
        "No matching manual entry was found. Please confirm the displayed error code "
        "and contact Level 2 support."
    )
```

Explanation:

- If RAG finds matching manual text, the agent creates a manual-based answer.
- If RAG finds nothing, it creates a safe fallback.
- This PoC uses a deterministic summarizer. A later version could call the LLM
  to summarize retrieved context.

Code:

```python
await self.mcp_client.update_technical_steps(state["ticket_id"], technical_steps)
```

Explanation:

- The troubleshooting steps are stored on the ticket through MCP.
- PostgreSQL is still accessed only by the MCP server.

## Reply Agent

This agent prepares the final customer message and sends it through the MCP
email tool.

Code:

```python
subject = f"Support ticket #{state['ticket_id']} troubleshooting steps"
body = (
    f"Hello,\n\n"
    f"We created ticket #{state['ticket_id']} for your product issue.\n\n"
    f"Detected from your request: {', '.join(state.get('detected_objects', []))}\n\n"
    f"{state['technical_steps']}\n\n"
    "Regards,\nAftercare Support"
)
```

Explanation:

- The email subject includes the ticket number.
- The body avoids saying "photo" because the request may be text-only.
- The body includes detected labels and manual-based technical steps.

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

- The agent calls MCP instead of sending email directly.
- In this PoC, email is simulated by writing to a log and updating the ticket.
- In production, the MCP server could call SMTP, SendGrid, Microsoft Graph, or
  another email provider.

## How The Supervisor Creates The Workflow

The supervisor does not literally create the graph at runtime. The graph is
created once when the backend starts. The supervisor creates the **route** inside
state, and LangGraph uses that route to choose the next node.

Code from `workflow.py`:

```python
class AftercareWorkflow:
    """Builds and runs the supervisor-routed LangGraph workflow."""

    def __init__(self, mcp_client: AftercareMcpClient | None = None) -> None:
        self.mcp_client = mcp_client or AftercareMcpClient()
        self.graph = self.build_graph()
```

Explanation:

- `AftercareWorkflow` owns the compiled graph.
- `mcp_client` is shared by agents that need MCP tools.
- `self.graph = self.build_graph()` builds the workflow once.

Code:

```python
graph = StateGraph(AftercareState)
graph.add_node("supervisor", SupervisorAgent())
graph.add_node("image_customer_service", CustomerServiceAgent(self.mcp_client))
graph.add_node("text_customer_service", TextCustomerServiceAgent(self.mcp_client))
graph.add_node("technical_assistant", TechnicalAssistantAgent(self.mcp_client))
graph.add_node("reply_agent", ReplyAgent(self.mcp_client))
```

Explanation:

- `StateGraph(AftercareState)` tells LangGraph the shape of the shared state.
- `add_node("supervisor", SupervisorAgent())` registers the first node.
- `image_customer_service` is the image route.
- `text_customer_service` is the text-only route.
- `technical_assistant` and `reply_agent` are shared by both routes.

Code:

```python
graph.set_entry_point("supervisor")
```

Explanation:

- Every support-ticket workflow starts at the supervisor.
- This is what makes the flow dynamic instead of fixed.

Code:

```python
graph.add_conditional_edges(
    "supervisor",
    self.route_after_supervisor,
    {
        "image_intake": "image_customer_service",
        "text_intake": "text_customer_service",
    },
)
```

Explanation:

- `add_conditional_edges` is the key LangGraph feature here.
- After `supervisor` runs, LangGraph calls `route_after_supervisor`.
- The returned value is matched against the mapping.
- If the route is `image_intake`, LangGraph runs `image_customer_service`.
- If the route is `text_intake`, LangGraph runs `text_customer_service`.

Code:

```python
def route_after_supervisor(self, state: AftercareState) -> str:
    """Return the next node key selected by the supervisor."""

    return state["intake_route"]
```

Explanation:

- The supervisor already wrote `state["intake_route"]`.
- This method simply gives that value to LangGraph.
- The graph mapping decides the actual next node name.

Code:

```python
graph.add_edge("image_customer_service", "technical_assistant")
graph.add_edge("text_customer_service", "technical_assistant")
graph.add_edge("technical_assistant", "reply_agent")
graph.add_edge("reply_agent", END)
```

Explanation:

- Both intake paths join at `technical_assistant`.
- The workflow then sends the reply.
- `END` marks the graph complete.

Code:

```python
return graph.compile()
```

Explanation:

- `compile()` turns the graph definition into a runnable workflow object.
- The API later runs this compiled graph with `ainvoke`.

## Running The Graph

Code from `workflow.py`:

```python
async def run(
    self,
    customer_email: str,
    description: str,
    image_filename: str = "",
    image_content_type: str = "application/octet-stream",
    image_bytes: bytes = b"",
) -> AftercareState:
    """Create the initial graph state and run the workflow."""

    final_state = await self.graph.ainvoke(
        {
            "customer_email": customer_email,
            "description": description,
            "image_filename": image_filename,
            "image_content_type": image_content_type,
            "image_bytes": image_bytes,
        }
    )
    return final_state
```

Explanation:

- The API passes user input into `run(...)`.
- Image fields are optional, so text-only requests can still run.
- `ainvoke(...)` executes the graph asynchronously.
- Every node receives state and returns updated state.
- The final state becomes the source for the API response.

## End-To-End Examples

Text-only request:

```text
Initial state:
customer_email = supervisor-text@example.com
description = The display shows E-77 on my AsterPump X17
image_bytes = b""

Supervisor route:
text_intake

Agents:
SupervisorAgent
-> TextCustomerServiceAgent
-> TechnicalAssistantAgent
-> ReplyAgent
```

Image-plus-text request:

```text
Initial state:
customer_email = supervisor-image@example.com
description = The display shows E-77
image_bytes = <uploaded PNG bytes>

Supervisor route:
image_intake

Agents:
SupervisorAgent
-> CustomerServiceAgent
-> TechnicalAssistantAgent
-> ReplyAgent
```

## Reading Logs

The supervisor route appears in backend logs:

```text
BACKEND | INFO | agent.supervisor | routed request route=text_intake has_image=False has_text=True
BACKEND | INFO | agent.supervisor | routed request route=image_intake has_image=True has_text=True
```

This makes it easy to prove whether the dynamic routing used the image service
or skipped it.
