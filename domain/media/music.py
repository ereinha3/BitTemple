from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field

from .base import BaseMedia


class MusicTrackMedia(BaseMedia):
    """Music track metadata from enrichment (placeholder for future)."""
    
    # IDs
    musicbrainz_id: Optional[str] = Field(None, description="MusicBrainz recording ID")
    isrc: Optional[str] = Field(None, description="International Standard Recording Code")
    
    # Basic Info
    title: str = Field(..., description="Track title")
    artist: Optional[str] = Field(None, description="Artist name")
    album: Optional[str] = Field(None, description="Album title")
    
    # Track Info
    track_number: Optional[int] = Field(None, description="Track number on album")
    disc_number: Optional[int] = Field(None, description="Disc number")
    duration_s: Optional[int] = Field(None, description="Duration in seconds")
    year: Optional[int] = Field(None, description="Release year")
    
    # Categories
    genres: Optional[list[str]] = Field(None, description="List of genres")