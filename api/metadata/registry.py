from __future__ import annotations
from functools import cached_property
from .tmdb.client import TMDbClient


class MetadataRegistry:
    @cached_property
    def movies():
        return {
            "tmdb": TMDbMetadata(),
        }
    
    @cached_property
    def tv():
        return {
            "tmdb": TMDbMetadata(),
        }
    
    @cached_property
    def music():
        return {
            "spotify": SpotifyMetadata(),
        }