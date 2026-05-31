from fastembed import TextEmbedding


class FastEmbedTextEmbedder:
    """Creates real CPU embeddings with a small ONNX embedding model."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.model = TextEmbedding(model_name=model_name)

    def embed(self, text: str) -> list[float]:
        """Convert text into a dense semantic vector."""

        vector = next(self.model.embed([text]))
        return [float(value) for value in vector.tolist()]
