from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from fastapi import Depends

from api.catalog.internetarchive.tv import (
    InternetArchiveDownloadError,
    TvAssetBundle,
    TvAssetPlan,
    TvCatalogClient,
    TvDownloadOptions,
)
from domain.catalog import CatalogDownloadRequest, CatalogDownloadResponse
from domain.media.tv import TvEpisodeMetadata

from .search import TvCatalogMatch, TvCatalogMatchCandidate, get_registered_match


class CatalogMatchNotFoundError(RuntimeError):
    """Raised when a download is requested for an unknown match."""


@dataclass(slots=True)
class TvCatalogDownloadService:
    client: TvCatalogClient

    def __init__(self, client: TvCatalogClient | None = None) -> None:
        self.client = client or TvCatalogClient()

    def _resolve_match(self, match_key: str) -> tuple[TvCatalogMatch, str]:
        match = get_registered_match(match_key)
        if match is None:
            raise CatalogMatchNotFoundError(f"Unknown match key: {match_key}")

        identifier = match.best_candidate.identifier
        if not identifier:
            raise CatalogMatchNotFoundError("Matched candidate is missing an identifier")
        return match, identifier

    def plan(self, match_key: str, destination: Optional[Path] = None) -> CatalogDownloadResponse:
        match, identifier = self._resolve_match(match_key)
        plan: TvAssetPlan = self.client.plan_tv_download(identifier)
        destination_str = str(destination) if destination else None
        return CatalogDownloadResponse(
            match_key=match_key,
            identifier=identifier,
            title=match.tmdb_episode.name,
            destination=destination_str,
            video_file=plan.video_file,
            metadata_xml_file=plan.metadata_xml_file,
            cover_art_file=plan.cover_art_file,
            subtitle_files=list(plan.subtitle_files),
            downloaded=False,
            video_path=None,
            subtitle_paths=[],
        )

    def download(
        self,
        match_key: str,
        *,
        destination: Optional[Path] = None,
        options: TvDownloadOptions | None = None,
    ) -> CatalogDownloadResponse:
        match, identifier = self._resolve_match(match_key)
        opts = options or TvDownloadOptions()
        bundle: TvAssetBundle = self.client.download_tv(
            identifier,
            destination=destination,
            options=opts,
        )
        destination_str = str(destination) if destination else None
        return CatalogDownloadResponse(
            match_key=match_key,
            identifier=identifier,
            title=match.tmdb_episode.name,
            destination=destination_str,
            video_file=bundle.video_path.name if bundle.video_path else None,
            metadata_xml_file=bundle.metadata_xml_path.name if bundle.metadata_xml_path else None,
            cover_art_file=bundle.cover_art_path.name if bundle.cover_art_path else None,
            subtitle_files=[path.name for path in bundle.subtitle_paths],
            downloaded=True,
            video_path=str(bundle.video_path) if bundle.video_path else None,
            subtitle_paths=[str(path) for path in bundle.subtitle_paths],
        )

    @staticmethod
    def build_metadata(
        match: TvCatalogMatch,
        episode_candidate: TvCatalogMatchCandidate,
        download_response: CatalogDownloadResponse,
    ) -> Dict[str, object]:
        episode = episode_candidate.episode
        tmdb_episode = match.tmdb_episode

        # Episode-level fields
        metadata: Dict[str, object] = {
            "catalog_source": episode.catalog_source or "internet_archive",
            "catalog_id": download_response.identifier,
            "collections": episode.collections,
            "episode_name": episode.name or tmdb_episode.name,
            "episode_overview": episode.overview or tmdb_episode.series_overview,
            "episode_number": episode.episode_number or 1,
            "episode_air_date": episode.air_date or tmdb_episode.air_date,
            "episode_runtime_min": episode.runtime_min,
            "poster": None,
            "backdrop": None,
            "ia_downloads": episode_candidate.downloads,
            "ia_score": episode_candidate.score,
        }

        # Season context
        season_number = episode.season_number or 1
        season_catalog_id = (
            episode.season_catalog_id
            or (episode.series_catalog_id or tmdb_episode.series_catalog_id or download_response.identifier)
            + f"::season-{season_number}"
        )
        metadata.update(
            {
                "season_number": season_number,
                "season_name": episode.season_name or f"Season {season_number}",
                "season_catalog_id": season_catalog_id,
                "season_overview": None,
                "season_poster": None,
                "season_backdrop": None,
            }
        )

        # Series context
        series_name = episode.series_name or tmdb_episode.series_name or tmdb_episode.name
        metadata.update(
            {
                "series_name": series_name,
                "series_catalog_id": episode.series_catalog_id or tmdb_episode.series_catalog_id,
                "series_overview": tmdb_episode.series_overview or episode.series_overview,
                "series_status": tmdb_episode.series_status or episode.series_status,
                "series_first_air_date": episode.series_first_air_date or tmdb_episode.series_first_air_date,
                "series_last_air_date": episode.series_last_air_date or tmdb_episode.series_last_air_date,
                "series_genres": tmdb_episode.series_genres or episode.series_genres,
                "series_languages": tmdb_episode.series_languages or episode.series_languages,
                "series_cast": tmdb_episode.series_cast or episode.series_cast,
                "series_poster": None,
                "series_backdrop": None,
            }
        )

        return metadata


def get_tv_catalog_download_service() -> TvCatalogDownloadService:
    return TvCatalogDownloadService()
