"""Domain media types for consistent metadata handling across backend."""

from .base import BaseMedia, ImageMetadata, MediaTypeLiteral, SourceTypeLiteral
from .movies import MovieMedia
from .tv import TvShowMedia, TvSeasonMetadata, TvEpisodeMetadata
from .shared import CastMember, CrewMember, ImageMedia

__all__ = [
    "BaseMedia",
    "ImageMetadata",
    "MediaTypeLiteral",
    "SourceTypeLiteral",
    "MovieMedia",
    "TvShowMedia",
    "TvSeasonMetadata",
    "TvEpisodeMetadata",
    "CastMember",
    "CrewMember",
    "ImageMedia",
]
