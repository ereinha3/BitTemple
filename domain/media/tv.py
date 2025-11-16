from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


from .base import BaseMedia

class TvShowMedia(BaseMedia):
    """Entire TV show metadata from enrichment. (not one episode)"""
    
    # Basic Info
    name: str = Field(..., description="TV show name")
    overview: Optional[str] = Field(None, description="Show synopsis")
    type: Optional[str] = Field(None, description="Show type (Scripted, Reality, etc.)")
    status: Optional[str] = Field(None, description="Show status (Returning, Ended, etc.)")
    
    # Air Dates
    first_air_date: Optional[datetime] = Field(None, description="First episode air date")
    last_air_date: Optional[datetime] = Field(None, description="Last episode air date")
    
    # Episodes & Seasons
    number_of_seasons: Optional[int] = Field(None, description="Total number of seasons")
    number_of_episodes: Optional[int] = Field(None, description="Total number of episodes")
    
    # Categories
    genres: Optional[list[str]] = Field(None, description="List of genre names")
    languages: Optional[list[str]] = Field(None, description="List of spoken languages")
    
    # Ratings
    vote_average: Optional[float] = Field(None, description="Average rating (0-10)")
    vote_count: Optional[int] = Field(None, description="Number of votes")
    
    # People
    cast: Optional[list[str]] = Field(None, description="Main cast members")

    seasons: Optional[list[TvSeasonMetadata]] = Field(
        None, description="List of seasons with basic info"
    )   
    
class TvSeasonMetadata(BaseMedia):
    """TV episode metadata from enrichment."""
    
    # Basic Info
    name: str = Field(..., description="Season name")
    overview: Optional[str] = Field(None, description="Season synopsis")
    
    # Episode Info
    season_number: int = Field(..., description="Season number")
    episodes: Optional[list[TvEpisodeMetadata]] = Field(None, description="List of episodes in the season")


class TvEpisodeMetadata(BaseMedia):
    """TV episode metadata from enrichment."""
    
    # Basic Info
    name: str = Field(..., description="Episode name")
    overview: Optional[str] = Field(None, description="Episode synopsis")
    
    # Episode Info
    episode_number: int = Field(..., description="Episode number within season")
    air_date: Optional[datetime] = Field(None, description="Air date")
    runtime_min: Optional[int] = Field(None, description="Runtime in minutes")
    
