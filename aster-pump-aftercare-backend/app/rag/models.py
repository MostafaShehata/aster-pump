from dataclasses import dataclass


@dataclass(frozen=True)
class Document:
    """One source document loaded from the backend docs folder."""

    source: str
    text: str


@dataclass(frozen=True)
class DocumentChunk:
    """A small searchable piece of a larger document."""

    source: str
    chunk_index: int
    text: str


@dataclass(frozen=True)
class RagResult:
    """Context and source names retrieved from the vector database."""

    context: str
    sources: list[str]

