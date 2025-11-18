from __future__ import annotations
from __future__ import annotations

from functools import cached_property

from .internetarchive.movie import MovieCatalogClient
from .internetarchive.tv import TvCatalogClient


class CatalogRegistry:
    """Expose lazily constructed catalog clients."""

    @cached_property
    def movies(self) -> MovieCatalogClient:
        return MovieCatalogClient()

    @cached_property
    def tv(self) -> TvCatalogClient:
        return TvCatalogClient()