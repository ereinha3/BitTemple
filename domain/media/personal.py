from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

from .base import BaseMedia, ImageMetadata

class PersonalMedia(BaseMedia):
    """Personal media metadata from enrichment (placeholder for future)."""
    
    # Basic Info
    title: Optional[str] = Field(None, description="Media title")