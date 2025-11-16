from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

from .base import BaseMedia, ImageMetadata

class PodcastShowMedia(BaseMedia):
    """Podcast show metadata from enrichment (placeholder for future)."""
    
    # Basic Info
    podcast_title: str = Field(..., description="Show title")
    publisher: Optional[str] = Field(None, description="Publisher name")
    description: Optional[str] = Field(None, description="Show description")
    
    poster: Optional[ImageMetadata] = Field(None, description="Primary poster image path")


class PodcastEpisodeMedia(PodcastShowMedia):
    """Podcast episode metadata from enrichment (placeholder for future)."""
    
    # Basic Info
    episode_title: str = Field(..., description="Episode title")
    
    # Episode Info
    pub_date: Optional[datetime] = Field(None, description="Publication date")
    duration_s: Optional[int] = Field(None, description="Duration in seconds")
    episode_description: Optional[str] = Field(None, description="Episode description")