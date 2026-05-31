import logging
from pathlib import Path

from app.config import settings
from app.rag.document_loader import DocumentLoader, TextChunker
from app.rag.embeddings import FastEmbedTextEmbedder
from app.rag.models import RagResult
from app.rag.vector_store import QdrantVectorStore
from app.schemas import ChatRequest


DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "docs"


class RagService:
    """Coordinates document loading, chunking, indexing, and retrieval."""

    def __init__(
        self,
        loader: DocumentLoader,
        chunker: TextChunker,
        vector_store: QdrantVectorStore,
    ) -> None:
        self.loader = loader
        self.chunker = chunker
        self.vector_store = vector_store

    def ensure_index(self) -> None:
        """Rebuild the local RAG index from the docs folder."""

        logging.info("story.rag | start indexing local manuals docs_dir=%s", DOCS_DIR)
        documents = self.loader.load_documents()
        logging.info(
            "story.rag | loaded documents count=%s dir=%s sources=%s",
            len(documents),
            DOCS_DIR,
            [document.source for document in documents],
        )
        chunks = [
            chunk
            for document in documents
            for chunk in self.chunker.chunk_document(document)
        ]
        logging.info(
            "story.rag | prepared chunks count=%s embedding_model=%s chunks=%s",
            len(chunks),
            settings.embedding_model_name,
            [{"source": chunk.source, "index": chunk.chunk_index, "text": chunk.text} for chunk in chunks],
        )
        self.vector_store.rebuild_collection(chunks)
        logging.info("story.rag | finished indexing local manuals collection=%s", settings.rag_collection_name)

    def retrieve_context(self, request: ChatRequest) -> RagResult:
        """Return relevant context when RAG is enabled for a request."""

        if not request.use_rag:
            logging.info("story.rag | skipped chat retrieval because use_rag=false question=%r", request.message)
            return RagResult(context="", sources=[])

        logging.info("story.rag | retrieving chat context question=%r", request.message)
        return self.vector_store.search(request.message)

    def retrieve_for_question(self, question: str) -> RagResult:
        """Search RAG directly for agent-generated questions."""

        logging.info("story.rag | retrieving agent context question=%r", question)
        return self.vector_store.search(question)


rag_service = RagService(
    loader=DocumentLoader(DOCS_DIR),
    chunker=TextChunker(max_words=90),
    vector_store=QdrantVectorStore(
        url=settings.qdrant_url,
        collection_name=settings.rag_collection_name,
        vector_size=settings.rag_vector_size,
        top_k=settings.rag_top_k,
        embedder=FastEmbedTextEmbedder(settings.embedding_model_name),
    ),
)
