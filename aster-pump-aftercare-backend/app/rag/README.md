# RAG Package

This package contains document indexing and retrieval logic.

RAG means Retrieval Augmented Generation.

The goal is simple:

1. Read local product manuals.
2. Split the manuals into small chunks.
3. Convert chunks into vectors.
4. Store vectors in Qdrant.
5. Search Qdrant when the user asks a question.
6. Give the retrieved text to the model or agent.

## Files

| File | Function |
| --- | --- |
| `models.py` | Small data classes for documents, chunks, and RAG results. |
| `document_loader.py` | Reads `.txt` and `.pdf` files and splits text into chunks. |
| `embeddings.py` | Creates real local CPU embeddings with FastEmbed. |
| `vector_store.py` | Creates/searches the Qdrant collection. |
| `service.py` | Coordinates loading, chunking, indexing, and retrieval. |

## RAG Models

Code:

```python
@dataclass(frozen=True)
class Document:
    source: str
    text: str
```

Explanation:

- `Document` represents one source file.
- `source` is the file name.
- `text` is the extracted text.
- `frozen=True` means the object should not be changed after creation.

Code:

```python
@dataclass(frozen=True)
class DocumentChunk:
    source: str
    chunk_index: int
    text: str
```

Explanation:

- Large manuals are split into smaller pieces.
- Each piece remembers its source file and chunk number.

## Loading Documents

Code:

```python
for path in sorted(self.docs_dir.glob("*.txt")):
    documents.append(Document(source=path.name, text=path.read_text(encoding="utf-8")))
```

Explanation:

- This reads all `.txt` files from the docs folder.
- `path.name` stores only the file name, not the full path.
- The text becomes searchable RAG content.

Code:

```python
for path in sorted(self.docs_dir.glob("*.pdf")):
    documents.append(Document(source=path.name, text=self.read_pdf_text(path)))
```

Explanation:

- This reads all `.pdf` files from the docs folder.
- The Aster Pump X17 PDF manual is picked up here.

## Extracting PDF Text

Code:

```python
reader = PdfReader(str(path))
pages = [page.extract_text() or "" for page in reader.pages]
return "\n\n".join(page.strip() for page in pages if page.strip())
```

Explanation:

- `PdfReader` opens the PDF.
- `extract_text()` extracts searchable text from each page.
- Empty pages are ignored.
- The remaining page text is joined into one document string.

## Chunking Text

Code:

```python
paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
```

Explanation:

- The text is split by blank lines.
- Empty paragraphs are removed.

Code:

```python
if len(current) + len(words) > self.max_words and current:
    chunks.append(" ".join(current))
    current = []
current.extend(words)
```

Explanation:

- The chunker keeps adding words until the chunk is near the word limit.
- Default limit is 90 words.
- Smaller chunks make retrieval more precise.

## Embedding Model

Code:

```python
class FastEmbedTextEmbedder:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.model = TextEmbedding(model_name=model_name)
```

Explanation:

- This creates a real embedding model wrapper.
- `TextEmbedding` comes from the `fastembed` library.
- The configured model is `BAAI/bge-small-en-v1.5`.
- It runs locally on CPU using ONNX.

Code:

```python
vector = next(self.model.embed([text]))
return [float(value) for value in vector.tolist()]
```

Explanation:

- The text is passed into the embedding model.
- The model returns a dense semantic vector.
- The vector is converted into plain Python floats so Qdrant can store it.
- `BAAI/bge-small-en-v1.5` returns 384-dimensional vectors.

## Rebuilding Qdrant

Code:

```python
existing = {collection.name for collection in client.get_collections().collections}
if self.collection_name in existing:
    client.delete_collection(collection_name=self.collection_name)
```

Explanation:

- The PoC rebuilds the index on backend startup.
- This prevents stale chunks when manuals change.

Code:

```python
client.create_collection(
    collection_name=self.collection_name,
    vectors_config=models.VectorParams(
        size=self.vector_size,
        distance=models.Distance.COSINE,
    ),
)
```

Explanation:

- This creates a Qdrant collection.
- `size` must match the embedding vector size.
- `COSINE` means Qdrant compares vector direction, not raw length.

## Storing Points

Code:

```python
models.PointStruct(
    id=index,
    vector=self.embedder.embed(chunk.text),
    payload={
        "source": chunk.source,
        "chunk_index": chunk.chunk_index,
        "text": chunk.text,
    },
)
```

Explanation:

- A Qdrant point is one searchable record.
- `vector` is used for similarity search.
- `payload` keeps the original text and metadata.
- The payload is what the backend later sends to the model as context.

## Searching Qdrant

Code:

```python
hits = self.client().search(
    collection_name=self.collection_name,
    query_vector=self.embedder.embed(query),
    limit=self.top_k,
    with_payload=True,
)
```

Explanation:

- The user question is embedded using the same embedder.
- Qdrant compares the question vector to stored chunk vectors.
- `limit=self.top_k` returns the best matches.
- `with_payload=True` returns source names and chunk text.

## RAG Service

Code:

```python
documents = self.loader.load_documents()
chunks = [
    chunk
    for document in documents
    for chunk in self.chunker.chunk_document(document)
]
self.vector_store.rebuild_collection(chunks)
```

Explanation:

- Load every document.
- Chunk every document.
- Rebuild Qdrant from those chunks.

Code:

```python
if not request.use_rag:
    return RagResult(context="", sources=[])
```

Explanation:

- RAG is optional for normal chat.
- If the frontend disables RAG, no vector search is performed.
