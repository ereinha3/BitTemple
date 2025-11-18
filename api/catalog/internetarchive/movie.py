from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from domain.media.movies import MovieMedia

from .client import (
    AssetBundle,
    AssetPlan,
    DownloadOptions,
    InternetArchiveClient,
    InternetArchiveDownloadError,
    MediaTypeConfig,
)
from .metadata_mapper import map_metadata_to_movie

MovieDownloadOptions = DownloadOptions


@dataclass(slots=True, frozen=True)
class MovieAssetPlan(AssetPlan[MovieMedia]):
    """Concrete asset-plan type for movie catalog operations."""


@dataclass(slots=True, frozen=True)
class MovieAssetBundle(AssetBundle[MovieMedia]):
    """Concrete asset-bundle type for movie catalog operations."""


_MOVIE_CONFIG = MediaTypeConfig[MovieMedia](
    mediatype="movies",
    metadata_mapper=map_metadata_to_movie,
    default_source="internet_archive",
    plan_class=MovieAssetPlan,
    bundle_class=MovieAssetBundle,
)


@dataclass(slots=True)
class MovieCatalogClient:
    """High-level helper for interacting with Internet Archive movie catalogues."""

    client: InternetArchiveClient

    def __init__(self, client: InternetArchiveClient | None = None) -> None:
        self.client = client or InternetArchiveClient()

    def search(
        self,
        title: str,
        limit: int = 20,
        *,
        sorts: Sequence[str] | None = None,
        filters: Sequence[str] | None = None,
    ) -> list[MovieMedia]:
        return self.client.search(
            _MOVIE_CONFIG,
            title,
            limit=limit,
            sorts=sorts,
            filters=filters,
        )

    def search_movies(
        self,
        title: str,
        limit: int = 20,
        *,
        sorts: Sequence[str] | None = None,
        filters: Sequence[str] | None = None,
    ) -> list[MovieMedia]:
        return self.search(title, limit=limit, sorts=sorts, filters=filters)

    def plan_download(
        self,
        identifier: str,
        *,
        include_subtitles: bool = True,
    ) -> MovieAssetPlan:
        return self.client.plan_download(
            _MOVIE_CONFIG,
            identifier,
            include_subtitles=include_subtitles,
        )

    def plan_movie_download(
        self,
        identifier: str,
        *,
        include_subtitles: bool = True,
    ) -> MovieAssetPlan:
        return self.plan_download(identifier, include_subtitles=include_subtitles)

    def download(
        self,
        identifier: str,
        *,
        destination: Path | None = None,
        options: MovieDownloadOptions | None = None,
    ) -> MovieAssetBundle:
        return self.client.download(
            _MOVIE_CONFIG,
            identifier,
            destination=destination,
            options=options,
        )

    def download_movie(
        self,
        identifier: str,
        *,
        destination: Path | None = None,
        options: MovieDownloadOptions | None = None,
    ) -> MovieAssetBundle:
        return self.download(identifier, destination=destination, options=options)

    def collect_movie_assets(
        self,
        identifier: str,
        *,
        destination: Path | None = None,
        include_subtitles: bool = True,
        checksum: bool = False,
    ) -> MovieAssetBundle:
        return self.client.collect_assets(
            _MOVIE_CONFIG,
            identifier,
            destination=destination,
            include_subtitles=include_subtitles,
            checksum=checksum,
        )


__all__ = [
    "MovieCatalogClient",
    "MovieDownloadOptions",
    "MovieAssetPlan",
    "MovieAssetBundle",
    "InternetArchiveDownloadError",
]

