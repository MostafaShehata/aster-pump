from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_base_url: str = Field(default="http://aster-pump-aftercare-model:11434")
    model_name: str = Field(default="qwen3:1.7b")
    request_timeout_seconds: float = Field(default=300.0)
    qdrant_url: str = Field(default="http://aster-pump-aftercare-vectordb:6333")
    rag_collection_name: str = Field(default="asterpump_x17_docs")
    embedding_model_name: str = Field(default="BAAI/bge-small-en-v1.5")
    rag_vector_size: int = Field(default=384)
    rag_top_k: int = Field(default=4)
    mcp_server_url: str = Field(default="http://aster-pump-aftercare-mcp-server:8200")


settings = Settings()
