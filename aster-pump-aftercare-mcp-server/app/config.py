from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime configuration for MCP tool integrations."""

    database_url: str = Field(
        default="postgresql://aftercare:aftercare@aster-pump-aftercare-db:5432/aster_pump_aftercare"
    )
    image_ai_url: str = Field(default="http://aster-pump-aftercare-image-ai-service:8100")


settings = Settings()
