# Model Package

This package contains local model chat logic.

The backend talks to the model container through Ollama.

## Files

| File | Function |
| --- | --- |
| `chat_client.py` | Builds prompts, optionally adds RAG context, calls Ollama, and returns chat responses. |

## What Is Ollama?

Ollama is the local model runtime used in this PoC.

The model container exposes an HTTP API:

```text
http://aster-pump-aftercare-model:11434/api/chat
```

The selected model is configured by:

```python
model_name: str = Field(default="qwen3:1.7b")
```

## Prompt Builder

Code:

```python
class PromptBuilder:
    def build_messages(self, request: ChatRequest, rag_context: str) -> list[dict[str, str]]:
```

Explanation:

- `PromptBuilder` prepares the message list for the model.
- A message has a `role` and `content`.
- Roles used here are `system`, `user`, and previous chat roles.

Code:

```python
messages = [
    {
        "role": "system",
        "content": (
            "You are a concise local assistant running in a CPU-only PoC. "
            "Answer clearly. Keep responses short unless the user asks for detail."
        ),
    }
]
```

Explanation:

- The first system message gives the model its behavior.
- It tells the model to be concise because the local model is small and CPU-only.

## Adding RAG Context

Code:

```python
if rag_context:
    messages.append(
        {
            "role": "system",
            "content": (
                "Use this retrieved local context when it is relevant. "
                "If the answer is in the context, prefer it over general knowledge.\n\n"
                f"{rag_context}"
            ),
        }
    )
```

Explanation:

- If RAG found relevant manual chunks, they are added as a system message.
- This makes the model answer from the local manual instead of guessing.

## Keeping History Small

Code:

```python
for item in request.history[-6:]:
    messages.append({"role": item.role, "content": item.content})
```

Explanation:

- Only the last six messages are sent.
- This keeps the prompt small.
- Small CPU models are slower and have smaller context windows.

## Calling Ollama

Code:

```python
model_request = {
    "model": settings.model_name,
    "stream": False,
    "think": False,
    "options": {
        "temperature": 0.2,
        "num_predict": 256,
        "num_ctx": 2048,
    },
    "messages": messages,
}
```

Explanation:

- `model` selects the local Ollama model.
- `stream=False` asks for one complete response instead of streamed tokens.
- `think=False` disables visible thinking behavior for models that support it.
- `temperature=0.2` makes answers more deterministic.
- `num_predict=256` limits answer length.
- `num_ctx=2048` limits prompt context size.

Code:

```python
response = await client.post(f"{settings.model_base_url}/api/chat", json=model_request)
response.raise_for_status()
```

Explanation:

- The backend sends JSON to Ollama.
- `raise_for_status()` raises an error if Ollama returns HTTP 4xx or 5xx.

## Returning The API Response

Code:

```python
return ChatResponse(
    reply=reply,
    model=settings.model_name,
    used_rag=bool(rag_result.context),
    sources=rag_result.sources,
)
```

Explanation:

- `reply` is the model output.
- `model` tells the frontend which local model answered.
- `used_rag` tells whether retrieval context was included.
- `sources` lists the retrieved document names.

