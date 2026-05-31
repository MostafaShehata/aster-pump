"""RAG package for document indexing and Qdrant retrieval."""

from app.rag.service import rag_service


def ensure_rag_index() -> None:
    """Compatibility wrapper for older imports."""

    rag_service.ensure_index()


def retrieve_rag_context(request):
    """Compatibility wrapper for older imports."""

    return rag_service.retrieve_context(request)

