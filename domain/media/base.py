from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field

MediaTypeLiteral = Literal["movie", "tv", "music", "podcast", "video", "personal"]
SourceTypeLiteral = Literal["catalog", "home"]

class BaseMedia(BaseModel):
    """Base media model."""

    file_hash: str = Field(..., description="File hash")
    path: str = Field(..., description="File path")
    type: MediaTypeLiteral = Field(..., description="Media type")