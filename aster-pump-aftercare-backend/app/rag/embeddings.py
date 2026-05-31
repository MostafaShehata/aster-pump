from fastembed import TextEmbedding
import logging


class FastEmbedTextEmbedder:
    """Creates real CPU embeddings with a small ONNX embedding model."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        logging.info("story.embedding | loading embedding model=%s", model_name)
        self.model = TextEmbedding(model_name=model_name)
        logging.info("story.embedding | embedding model ready=%s", model_name)

    def embed(self, text: str) -> list[float]:
        """Convert text into a dense semantic vector."""

        logging.info("story.embedding | embedding text=%r model=%s", text, self.model_name)
        vector = next(self.model.embed([text]))
        values = [float(value) for value in vector.tolist()]
        logging.info("story.embedding | created vector model=%s dimensions=%s", self.model_name, len(values))
        return values
