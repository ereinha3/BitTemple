from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


from .shared.person import CastMember, CrewMember
from .shared.image import ImageMedia
from .base import BaseMedia

class MovieMedia(BaseMedia):
    """Complete movie metadata from enrichment."""
    
    # IDs
    tmdb_id: Optional[int] = Field(None, description="TMDb movie ID")
    imdb_id: Optional[str] = Field(None, description="IMDb identifier")
    
    # Basic Info
    title: str = Field(..., description="Movie title")
    original_title: Optional[str] = Field(None, description="Original title in native language")
    tagline: Optional[str] = Field(None, description="Movie tagline")
    overview: Optional[str] = Field(None, description="Plot synopsis")
    
    # Release Info
    release_date: Optional[datetime] = Field(None, description="Release date")
    year: Optional[int] = Field(None, description="Release year")
    
    # Runtime & Production
    runtime_min: Optional[int] = Field(None, description="Runtime in minutes")

    # Categories
    genres: Optional[list[str]] = Field(None, description="List of genre names")
    languages: Optional[list[str]] = Field(None, description="List of spoken languages")
    countries: Optional[list[str]] = Field(None, description="List of production countries")
    
    # Ratings
    vote_average: Optional[float] = Field(None, description="Average rating (0-10)")
    vote_count: Optional[int] = Field(None, description="Number of votes")
    popularity: Optional[float] = Field(None, description="Popularity score")
    
    # People
    cast: Optional[list[CastMember]] = Field(None, description="Top cast members")
    crew: Optional[list[CrewMember]] = Field(None, description="Key crew members")
    
    # Images
    poster_path: Optional[str] = Field(None, description="Primary poster image path")
    backdrop_path: Optional[str] = Field(None, description="Primary backdrop image path")
    posters: Optional[list[ImageMetadata]] = Field(None, description="Additional posters")
    backdrops: Optional[list[ImageMetadata]] = Field(None, description="Additional backdrops")
    
    # URLs
    poster_url: Optional[str] = Field(None, description="Full poster URL")
    backdrop_url: Optional[str] = Field(None, description="Full backdrop URL")
    homepage: Optional[str] = Field(None, description="Official website")
    
    # Flags
    adult: Optional[bool] = Field(None, description="Adult content flag")
    
