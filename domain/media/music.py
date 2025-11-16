from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field

from .base import BaseMedia

class MusicArtistMedia(BaseMedia):
    """Music track metadata from enrichment (placeholder for future)."""
    
    # Basic Info
    artist: Optional[str] = Field(None, description="Artist name")
    albums: Optional[list[MusicAlbumMedia]] = Field(
        None, description="List of albums by the artist"
    )
    


class MusicAlbumMedia(BaseMedia):
    """Music track metadata from enrichment (placeholder for future)."""
    
    # Basic Info
    title: str = Field(..., description="Album title")
    genres: Optional[list[str]] = Field(None, description="List of genres")
    release_year: Optional[int] = Field(None, description="Release year")
    tracks: Optional[list[MusicTrackMedia]] = Field(
        None, description="List of tracks in the album"
    )


class MusicTrackMedia(BaseMedia):
    """Music track metadata from enrichment (placeholder for future)."""
    
    # Basic Info
    title: str = Field(..., description="Track title")
    track_number: Optional[int] = Field(None, description="Track number on album")
    duration_s: Optional[int] = Field(None, description="Duration in seconds")
