# Aster Pump Aftercare Vector DB and RAG

This repository contains the local Vector DB component for the **Aster Pump
Aftercare** proof of concept.

The Vector DB is Qdrant. It stores searchable vector records generated from the
Aster Pump X17 support documents, including the PDF manual:

```text
aster-pump-aftercare-backend/docs/asterpump_x17_user_guide.pdf
```

## What This Container Does

This container runs Qdrant only.

Qdrant does not read the PDF by itself. It is a storage and search engine for
vectors. The backend service performs the RAG ingestion work and sends the
resulting vectors to Qdrant.

## Technology Brief

### Qdrant

Qdrant is a vector database. It stores points, where each point has:

- a vector, which is a list of numbers used for similarity search
- a payload, which stores metadata such as source file name and chunk text

In this PoC, Qdrant runs locally in Docker and exposes HTTP on:

```text
http://localhost:6333
```

### RAG

RAG means Retrieval Augmented Generation.

Instead of asking the model to answer only from its built-in training, the
backend first searches Qdrant for relevant manual text. Then it sends that
retrieved context to the model/agent so the reply is grounded in the Aster Pump
manual.

### Embeddings

Embeddings convert text into vectors.

For this CPU-only PoC, the backend uses a small real embedding model through
`fastembed`:

```text
aster-pump-aftercare-backend/app/rag/embeddings.py
```

The model is:

```text
BAAI/bge-small-en-v1.5
```

It runs locally on CPU and creates 384-dimensional semantic vectors.

## Source Documents

The backend indexes all supported files from:

```text
aster-pump-aftercare-backend/docs
```

Current files:

| File | Purpose |
| --- | --- |
| `asterpump_x17_user_guide.pdf` | Main PDF manual used for the RAG demo. |
| `asterpump_x17_error_codes.txt` | Small plain-text error-code reference. |
| `asterpump_x17_maintenance_policy.txt` | Maintenance policy reference. |
| `asterpump_x17_operator_manual.txt` | Operator manual reference. |

## How The PDF Manual Was Added To Qdrant

### Step 1: PDF Was Placed In The Backend Docs Folder

The generated PDF manual was saved here:

```text
aster-pump-aftercare-backend/docs/asterpump_x17_user_guide.pdf
```

The backend uses this folder as its RAG document source.

The folder location is defined in:

```text
aster-pump-aftercare-backend/app/rag/service.py
```

Code:

```python
DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "docs"
```

### Step 2: Backend Startup Runs RAG Indexing

When the backend container starts, it calls `ensure_rag_index()`.

That function is in:

```text
aster-pump-aftercare-backend/app/rag/service.py
```

The function connects to Qdrant using:

```python
QdrantClient(url=settings.qdrant_url)
```

In Docker Compose, the backend gets this value:

```text
QDRANT_URL=http://aster-pump-aftercare-vectordb:6333
```

From the host machine, Qdrant is available at:

```text
http://localhost:6333
```

### Step 3: Backend Loads `.txt` And `.pdf` Files

The backend calls `load_documents()`.

That function reads:

```python
for path in sorted(DOCS_DIR.glob("*.txt")):
    documents.append((path.name, path.read_text(encoding="utf-8")))

for path in sorted(DOCS_DIR.glob("*.pdf")):
    documents.append((path.name, read_pdf_text(path)))
```

So the PDF manual is picked up automatically because it is inside the `docs`
folder and has the `.pdf` extension.

### Step 4: PDF Text Is Extracted

The backend uses `pypdf`.

The extraction happens in `read_pdf_text()`:

```python
reader = PdfReader(str(path))
pages = [page.extract_text() or "" for page in reader.pages]
return "\n\n".join(page.strip() for page in pages if page.strip())
```

This converts the PDF pages into plain searchable text.

Images from the PDF are not embedded in this PoC. Only extracted text is used
for retrieval.

### Step 5: Text Is Split Into Chunks

The backend calls `chunk_text(text)`.

The chunker:

- splits text by paragraphs
- groups paragraphs into small chunks
- keeps each chunk around 90 words by default

Why chunking is needed:

- searching a whole PDF as one record is too broad
- smaller chunks let Qdrant return the specific manual section related to the
  user question

Each chunk becomes one Qdrant point.

### Step 6: Each Chunk Gets A Vector

The backend calls `embed_text(chunk)`.

This embedding model:

- reads the chunk text
- creates a semantic vector
- helps semantically similar questions and manual chunks match in Qdrant

The vector size is configured by:

```text
RAG_VECTOR_SIZE=384
```

Default value in backend config:

```python
embedding_model_name: str = Field(default="BAAI/bge-small-en-v1.5")
rag_vector_size: int = Field(default=384)
```

### Step 7: Qdrant Collection Is Created

The backend creates this Qdrant collection:

```text
asterpump_x17_docs
```

Default value in backend config:

```python
rag_collection_name: str = Field(default="asterpump_x17_docs")
```

The collection uses cosine similarity:

```python
models.VectorParams(
    size=settings.rag_vector_size,
    distance=models.Distance.COSINE,
)
```

### Step 8: Existing Collection Is Rebuilt

For this small local PoC, the backend deletes and recreates the collection on
startup:

```python
client.delete_collection(collection_name=settings.rag_collection_name)
client.create_collection(...)
```

Why this was done:

- the manual may change during development
- rebuilding avoids stale chunks
- the document set is tiny, so startup cost is low

For production, you would normally use incremental indexing instead of deleting
the whole collection.

### Step 9: Points Are Upserted Into Qdrant

For each chunk, the backend creates a Qdrant point:

```python
models.PointStruct(
    id=point_id,
    vector=embed_text(chunk),
    payload={
        "source": source,
        "chunk_index": chunk_index,
        "text": chunk,
    },
)
```

The payload is important because it lets the backend show where the answer came
from.

Example payload:

```json
{
  "source": "asterpump_x17_user_guide.pdf",
  "chunk_index": 2,
  "text": "E-77: Coolant Loop Pressure Echo..."
}
```

Finally, the backend sends the points to Qdrant:

```python
client.upsert(collection_name=settings.rag_collection_name, points=points)
```

At this moment, the PDF manual content is inside Qdrant as searchable vector
records.

## How Retrieval Works During Chat Or Agent Flow

When the backend needs RAG context, it calls:

```python
retrieve_rag_context(request)
```

The user question is embedded using the same `embed_text()` function:

```python
query_vector=embed_text(request.message)
```

Then Qdrant searches for similar chunks:

```python
hits = client.search(
    collection_name=settings.rag_collection_name,
    query_vector=embed_text(request.message),
    limit=settings.rag_top_k,
    with_payload=True,
)
```

The default top-k value is:

```text
RAG_TOP_K=4
```

The backend then builds context blocks from the returned payload text and passes
that context to the model/agent.

## How To Verify Qdrant Is Running

From the root solution folder:

```powershell
curl.exe http://localhost:6333/collections
```

You should see a collection named:

```text
asterpump_x17_docs
```

## How To Verify The PDF Was Indexed

Ask a question that depends on the fictional PDF manual:

```text
What does E-77 mean for the Aster Pump X17?
```

Expected RAG-grounded answer:

```text
E-77 means Coolant Loop Pressure Echo. Inspect the return valve, drain 200 ml
of coolant, and restart the pressure monitor.
```

Another good test:

```text
How often should the filter cassette be replaced?
```

Expected answer:

```text
Every 19 days, not monthly.
```

These details are fictional and specific to the local manual, so they are good
tests that retrieval is working.

## Persistence

Docker Compose mounts the named volume:

```text
aster-pump-aftercare-qdrant
```

To Qdrant path:

```text
/qdrant/storage
```

This keeps Qdrant data after containers stop.

However, the backend currently rebuilds the collection on startup, so the data
inside Qdrant will be refreshed from the files in:

```text
aster-pump-aftercare-backend/docs
```

## Build Locally

For detailed build and deployment steps, see:

```text
BUILD_AND_DEPLOY.md
```

Quick PowerShell build:

```powershell
.\build-image.ps1
```

Unix-style shell:

```sh
./build-image.sh
```

The local image name is:

```text
aster-pump-aftercare-vectordb:local
```

## Run In The Full Stack

From the root solution folder:

```powershell
docker compose up -d aster-pump-aftercare-vectordb aster-pump-aftercare-backend
```

The backend depends on Qdrant for RAG retrieval.

## Important Files

| File | Purpose |
| --- | --- |
| `aster-pump-aftercare-vectordb/Dockerfile` | Builds the local Qdrant wrapper image. |
| `aster-pump-aftercare-vectordb/README.md` | Explains Vector DB and RAG ingestion. |
| `aster-pump-aftercare-backend/app/rag` | Reads PDF/text files, chunks text, embeds chunks, upserts to Qdrant, and searches Qdrant. |
| `aster-pump-aftercare-backend/docs/asterpump_x17_user_guide.pdf` | Main PDF manual indexed into Qdrant. |
| `docker-compose.yml` | Starts Qdrant and attaches the persistent volume. |
