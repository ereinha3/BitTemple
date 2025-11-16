from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

from .base import BaseMedia

class PodcastEpisodeMedia(BaseMedia):
    """Podcast episode metadata from enrichment (placeholder for future)."""
    
    # IDs
    guid: Optional[str] = Field(None, description="Episode GUID")
    
    # Basic Info
    title: str = Field(..., description="Episode title")
    show_name: Optional[str] = Field(None, description="Podcast show name")
    description: Optional[str] = Field(None, description="Episode description")
    
    # Episode Info
    pub_date: Optional[datetime] = Field(None, description="Publication date")
    duration_s: Optional[int] = Field(None, description="Duration in seconds")
    
    # Images
    image_url: Optional[str] = Field(None, description="Episode artwork URL")

