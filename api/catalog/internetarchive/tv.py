from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from domain.media.tv import TvEpisodeMetadata

from .client import (
    AssetBundle,
    AssetPlan,
    DownloadOptions,
    InternetArchiveClient,
    InternetArchiveDownloadError,
    MediaTypeConfig,
)
from .metadata_mapper import map_metadata_to_tv

TvDownloadOptions = DownloadOptions


@dataclass(slots=True, frozen=True)
class TvAssetPlan(AssetPlan[TvEpisodeMetadata]):
    """Concrete asset-plan type for TV catalog operations."""


@dataclass(slots=True, frozen=True)
class TvAssetBundle(AssetBundle[TvEpisodeMetadata]):
    """Concrete asset-bundle type for TV catalog operations."""


_TV_CONFIG = MediaTypeConfig[TvEpisodeMetadata](
    mediatype=None,
    metadata_mapper=map_metadata_to_tv,
    default_source="internet_archive",
    default_filters=("collection:(television OR classic_tv OR tvarchive)",),
    plan_class=TvAssetPlan,
    bundle_class=TvAssetBundle,
)


@dataclass(slots=True)
class TvCatalogClient:
    """High-level helper for interacting with Internet Archive television catalogues."""

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
    ) -> list[TvEpisodeMetadata]:
        return self.client.search(
            _TV_CONFIG,
            title,
            limit=limit,
            sorts=sorts,
            filters=filters,
        )

    def search_tv(
        self,
        title: str,
        limit: int = 20,
        *,
        sorts: Sequence[str] | None = None,
        filters: Sequence[str] | None = None,
    ) -> list[TvEpisodeMetadata]:
        return self.search(title, limit=limit, sorts=sorts, filters=filters)

    def plan_download(
        self,
        identifier: str,
        *,
        include_subtitles: bool = True,
    ) -> TvAssetPlan:
        return self.client.plan_download(
            _TV_CONFIG,
            identifier,
            include_subtitles=include_subtitles,
        )

    def plan_tv_download(
        self,
        identifier: str,
        *,
        include_subtitles: bool = True,
    ) -> TvAssetPlan:
        return self.plan_download(identifier, include_subtitles=include_subtitles)

    def download(
        self,
        identifier: str,
        *,
        destination: Path | None = None,
        options: TvDownloadOptions | None = None,
    ) -> TvAssetBundle:
        return self.client.download(
            _TV_CONFIG,
            identifier,
            destination=destination,
            options=options,
        )

    def download_tv(
        self,
        identifier: str,
        *,
        destination: Path | None = None,
        options: TvDownloadOptions | None = None,
    ) -> TvAssetBundle:
        return self.download(identifier, destination=destination, options=options)

    def collect_tv_assets(
        self,
        identifier: str,
        *,
        destination: Path | None = None,
        include_subtitles: bool = True,
        checksum: bool = False,
    ) -> TvAssetBundle:
        return self.client.collect_assets(
            _TV_CONFIG,
            identifier,
            destination=destination,
            include_subtitles=include_subtitles,
            checksum=checksum,
        )


__all__ = [
    "TvCatalogClient",
    "TvDownloadOptions",
    "TvAssetPlan",
    "TvAssetBundle",
    "InternetArchiveDownloadError",
]

