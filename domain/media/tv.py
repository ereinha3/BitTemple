from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from .shared.person import CastMember, CrewMember
from .shared.image import ImageMedia

from .base import BaseMedia

class TvShowMedia(BaseMedia):
    """Entire TV show metadata from enrichment. (not one episode)"""
    
    # IDs
    tmdb_id: Optional[int] = Field(None, description="TMDb TV show ID")
    imdb_id: Optional[str] = Field(None, description="IMDb identifier")
    tvmaze_id: Optional[int] = Field(None, description="TVmaze identifier")
    
    # Basic Info
    name: str = Field(..., description="TV show name")
    original_name: Optional[str] = Field(None, description="Original name in native language")
    tagline: Optional[str] = Field(None, description="Show tagline")
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
    countries: Optional[list[str]] = Field(None, description="List of origin countries")
    
    # Ratings
    vote_average: Optional[float] = Field(None, description="Average rating (0-10)")
    vote_count: Optional[int] = Field(None, description="Number of votes")
    popularity: Optional[float] = Field(None, description="Popularity score")
    
    # People
    cast: Optional[list[CastMember]] = Field(None, description="Main cast members")
    crew: Optional[list[CrewMember]] = Field(None, description="Key crew members")
    created_by: Optional[list[str]] = Field(None, description="Show creators")
    
    # Images
    poster_path: Optional[str] = Field(None, description="Primary poster image path")
    backdrop_path: Optional[str] = Field(None, description="Primary backdrop image path")
    posters: Optional[list[ImageMetadata]] = Field(None, description="Additional posters")
    backdrops: Optional[list[ImageMetadata]] = Field(None, description="Additional backdrops")
    
    # URLs
    poster_url: Optional[str] = Field(None, description="Full poster URL")
    backdrop_url: Optional[str] = Field(None, description="Full backdrop URL")
    homepage: Optional[str] = Field(None, description="Official website")
    
    # Networks
    networks: Optional[list[str]] = Field(None, description="Broadcasting networks")
     

class TvEpisodeMetadata(BaseModel):
    """TV episode metadata from enrichment."""
    
    # IDs
    tmdb_id: Optional[int] = Field(None, description="TMDb episode ID")
    imdb_id: Optional[str] = Field(None, description="IMDb identifier")
    tvmaze_id: Optional[int] = Field(None, description="TVmaze identifier")
    
    # Series Info
    series_name: Optional[str] = Field(None, description="TV show name")
    series_tmdb_id: Optional[int] = Field(None, description="TMDb TV show ID")
    
    # Basic Info
    name: str = Field(..., description="Episode name")
    overview: Optional[str] = Field(None, description="Episode synopsis")
    
    # Episode Info
    season_number: int = Field(..., description="Season number")
    episode_number: int = Field(..., description="Episode number within season")
    air_date: Optional[datetime] = Field(None, description="Air date")
    runtime_min: Optional[int] = Field(None, description="Runtime in minutes")
    
    # Ratings
    vote_average: Optional[float] = Field(None, description="Average rating (0-10)")
    vote_count: Optional[int] = Field(None, description="Number of votes")
    
    # People
    cast: Optional[list[CastMember]] = Field(None, description="Episode guest cast")
    crew: Optional[list[CrewMember]] = Field(None, description="Episode crew (director, writer)")
    
    # Images
    still_path: Optional[str] = Field(None, description="Episode still image path")
    still_url: Optional[str] = Field(None, description="Full still image URL")
