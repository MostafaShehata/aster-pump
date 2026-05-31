import logging

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.rag.embeddings import FastEmbedTextEmbedder
from app.rag.models import DocumentChunk, RagResult


class QdrantVectorStore:
    """Qdrant access layer for indexing and retrieving RAG chunks."""

    def __init__(
        self,
        url: str,
        collection_name: str,
        vector_size: int,
        top_k: int,
        embedder: FastEmbedTextEmbedder,
    ) -> None:
        self.url = url
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.top_k = top_k
        self.embedder = embedder

    def client(self) -> QdrantClient:
        """Create a Qdrant client for the current operation."""

        logging.info("story.qdrant | opening client url=%s collection=%s", self.url, self.collection_name)
        return QdrantClient(url=self.url)

    def rebuild_collection(self, chunks: list[DocumentChunk]) -> None:
        """Delete and recreate the collection, then insert all chunks."""

        logging.info("story.qdrant | start rebuild collection=%s chunk_count=%s", self.collection_name, len(chunks))
        client = self.client()
        existing = {collection.name for collection in client.get_collections().collections}
        if self.collection_name in existing:
            logging.info("story.qdrant | deleting existing collection=%s", self.collection_name)
            client.delete_collection(collection_name=self.collection_name)

        logging.info(
            "story.qdrant | creating collection=%s vector_size=%s top_k=%s",
            self.collection_name,
            self.vector_size,
            self.top_k,
        )
        client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.vector_size,
                distance=models.Distance.COSINE,
            ),
        )

        points = [
            models.PointStruct(
                id=index,
                vector=self.embedder.embed(chunk.text),
                payload={
                    "source": chunk.source,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                },
            )
            for index, chunk in enumerate(chunks, start=1)
        ]
        logging.info(
            "story.qdrant | prepared points for upsert count=%s payloads=%s",
            len(points),
            [point.payload for point in points],
        )

        if points:
            client.upsert(collection_name=self.collection_name, points=points)
        logging.info("story.qdrant | indexed points=%s collection=%s", len(points), self.collection_name)

    def search(self, query: str) -> RagResult:
        """Search Qdrant and return context blocks for model prompting."""

        logging.info("story.qdrant | searching collection=%s query=%r top_k=%s", self.collection_name, query, self.top_k)
        hits = self.client().search(
            collection_name=self.collection_name,
            query_vector=self.embedder.embed(query),
            limit=self.top_k,
            with_payload=True,
        )
        logging.info("story.qdrant | search returned query=%r hits=%s", query, len(hits))

        context_blocks: list[str] = []
        sources: list[str] = []
        for hit in hits:
            payload = hit.payload or {}
            source = str(payload.get("source", "unknown"))
            text = str(payload.get("text", ""))
            if not text:
                continue
            context_blocks.append(f"Source: {source}\n{text}")
            if source not in sources:
                sources.append(source)

        logging.info(
            "story.qdrant | returning sources=%s context_blocks=%s",
            sources,
            context_blocks,
        )
        return RagResult(context="\n\n---\n\n".join(context_blocks), sources=sources)
