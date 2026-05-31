from pydantic import BaseModel


class AnalyzeImageResponse(BaseModel):
    """Response returned by the image analyzer endpoint."""

    objects: list[str]
