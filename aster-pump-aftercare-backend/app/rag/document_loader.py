from pathlib import Path

from pypdf import PdfReader

from app.rag.models import Document, DocumentChunk


class DocumentLoader:
    """Loads plain text and PDF documents from the local docs folder."""

    def __init__(self, docs_dir: Path) -> None:
        self.docs_dir = docs_dir

    def load_documents(self) -> list[Document]:
        """Read all supported files and return non-empty documents."""

        documents: list[Document] = []

        for path in sorted(self.docs_dir.glob("*.txt")):
            documents.append(Document(source=path.name, text=path.read_text(encoding="utf-8")))

        for path in sorted(self.docs_dir.glob("*.pdf")):
            documents.append(Document(source=path.name, text=self.read_pdf_text(path)))

        return [document for document in documents if document.text.strip()]

    def read_pdf_text(self, path: Path) -> str:
        """Extract searchable text from a local PDF guide."""

        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(page.strip() for page in pages if page.strip())


class TextChunker:
    """Splits document text into compact chunks for local retrieval."""

    def __init__(self, max_words: int = 90) -> None:
        self.max_words = max_words

    def chunk_document(self, document: Document) -> list[DocumentChunk]:
        """Split one document into numbered chunks."""

        chunks = self.chunk_text(document.text)
        return [
            DocumentChunk(source=document.source, chunk_index=index, text=chunk)
            for index, chunk in enumerate(chunks)
        ]

    def chunk_text(self, text: str) -> list[str]:
        """Group paragraphs into chunks that fit the configured word budget."""

        paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
        chunks: list[str] = []
        current: list[str] = []

        for paragraph in paragraphs:
            words = paragraph.split()
            if len(current) + len(words) > self.max_words and current:
                chunks.append(" ".join(current))
                current = []
            current.extend(words)

        if current:
            chunks.append(" ".join(current))

        return chunks

