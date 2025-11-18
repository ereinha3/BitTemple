from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import Field

from .base import BaseMedia


class TvEpisodeMetadata(BaseMedia):
    """Flattened TV episode metadata with optional season/series context."""

    # Episode basics
    name: str = Field(..., description="Episode title")
    overview: Optional[str] = Field(None, description="Episode synopsis")
    episode_number: Optional[int] = Field(None, description="Episode number within the season")
    air_date: Optional[datetime] = Field(None, description="Original air date")
    runtime_min: Optional[int] = Field(None, description="Runtime in minutes")

    # Season context
    season_number: Optional[int] = Field(None, description="Season number")
    season_name: Optional[str] = Field(None, description="Human-readable season label")
    season_catalog_id: Optional[str] = Field(None, description="Catalog identifier for the season")

    # Series context
    series_name: Optional[str] = Field(None, description="Parent series title")
    series_catalog_id: Optional[str] = Field(None, description="Catalog identifier for the parent series")
    series_overview: Optional[str] = Field(None, description="Series synopsis")
    series_status: Optional[str] = Field(None, description="Series status (Returning, Ended, etc.)")
    series_first_air_date: Optional[datetime] = Field(None, description="Series first air date")
    series_last_air_date: Optional[datetime] = Field(None, description="Series most recent air date")
    series_genres: Optional[list[str]] = Field(None, description="Series genres")
    series_languages: Optional[list[str]] = Field(None, description="Series languages")
    series_cast: Optional[list[str]] = Field(None, description="Series cast members")

    # Provenance
    collections: Optional[list[str]] = Field(None, description="Source collections associated with this item")


# Backwards compatibility aliases
TvSeasonMetadata = TvEpisodeMetadata
TvShowMedia = TvEpisodeMetadata
    
