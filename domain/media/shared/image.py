from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from .base import BaseMedia

class ImageMetadata(BaseModel):
    """Image metadata from TMDb."""
    
    file_path: str = Field(..., description="Image file path")
    width: Optional[int] = Field(None, description="Image width in pixels")
    height: Optional[int] = Field(None, description="Image height in pixels")
    aspect_ratio: Optional[float] = Field(None, description="Image aspect ratio")
    vote_average: Optional[float] = Field(None, description="Community rating")
    vote_count: Optional[int] = Field(None, description="Number of votes")
    iso_639_1: Optional[str] = Field(None, description="Language code")