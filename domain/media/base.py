from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field

MediaTypeLiteral = Literal["movie", "tv", "music", "podcast", "video", "personal"]
SourceTypeLiteral = Literal["catalog", "home"]

class ImageMetadata(BaseModel):
    """Image metadata from TMDb."""
    
    file_path: str = Field(..., description="Image file path")
    width: Optional[int] = Field(None, description="Image width in pixels")
    height: Optional[int] = Field(None, description="Image height in pixels")
    aspect_ratio: Optional[float] = Field(None, description="Image aspect ratio")

class BaseMedia(BaseModel):
    """Base media model."""

    file_hash: str = Field(..., description="File hash")
    embedding_hash: str = Field(..., description="Embedding hash")
    path: str = Field(..., description="File path")
    type: MediaTypeLiteral = Field(..., description="Media type")
    format: Optional[str] = Field(None, description="File format/extension")

    poster: Optional[ImageMetadata] = Field(None, description="Primary poster image path")
    backdrop: Optional[ImageMetadata] = Field(None, description="Primary backdrop image path")