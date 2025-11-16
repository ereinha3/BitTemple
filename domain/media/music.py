from __future__ import annotations
from typing import Optional
from pydantic import Field

from .base import BaseMedia


class MusicTrackMedia(BaseMedia):
    """Flattened track metadata stored alongside the media file."""

    title: str = Field(..., description="Track title")
    track_id: Optional[str] = Field(None, description="Identifier used by the catalog/search layer")
    artist: Optional[str] = Field(None, description="Artist name")
    artist_id: Optional[str] = Field(None, description="Catalog identifier for the artist")
    album: Optional[str] = Field(None, description="Album title")
    album_id: Optional[str] = Field(None, description="Catalog identifier for the album")
    track_number: Optional[int] = Field(None, description="Track number on album")
    duration_s: Optional[int] = Field(None, description="Duration in seconds")
    release_year: Optional[int] = Field(None, description="Release year")
    genres: Optional[list[str]] = Field(None, description="List of genres")
    license: Optional[str] = Field(None, description="License information")
    audio_url: Optional[str] = Field(None, description="Remote audio URL (if available)")
    downloads: Optional[int] = Field(None, description="Number of downloads")
    likes: Optional[int] = Field(None, description="Number of likes")
