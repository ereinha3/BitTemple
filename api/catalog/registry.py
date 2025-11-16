from __future__ import annotations
from functools import cached_property
from .internetarchive.client import InternetArchiveClient

class CatalogRegistry:
    @cached_property
    def movies():
        return InternetArchiveClient()
    
    def tv():
        return None