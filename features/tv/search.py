from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional
from uuid import uuid4

from fastapi import Depends
from pydantic import BaseModel, Field

from app.settings import AppSettings, get_settings
from api.catalog.internetarchive.tv import TvCatalogClient
from api.metadata.tmdb.client import TMDbClient, TMDbTvSearchResult
from domain.media.tv import TvEpisodeMetadata


class TvCatalogMatchCandidate(BaseModel):
    identifier: str
    score: float = Field(ge=0.0, le=1.0)
    downloads: Optional[int] = None
    episode: TvEpisodeMetadata


class TvCatalogMatch(BaseModel):
    match_key: str
    tmdb_id: int
    tmdb_episode: TvEpisodeMetadata
    best_candidate: TvCatalogMatchCandidate
    candidates: List[TvCatalogMatchCandidate] = Field(default_factory=list)


class TvCatalogMatchResponse(BaseModel):
    matches: List[TvCatalogMatch] = Field(default_factory=list)
    total: int


_MATCH_REGISTRY: Dict[str, TvCatalogMatch] = {}


def get_registered_match(match_key: str) -> Optional[TvCatalogMatch]:
    return _MATCH_REGISTRY.get(match_key)


def clear_registered_matches() -> None:
    _MATCH_REGISTRY.clear()


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _search_result_to_metadata(result: TMDbTvSearchResult) -> TvEpisodeMetadata:
    first_air = _parse_date(result.first_air_date)
    languages = [result.original_language] if result.original_language else None
    name = result.name or result.original_name or ""
    catalog_id = str(result.id)
    return TvEpisodeMetadata(
        name=name,
        overview=result.overview,
        episode_number=None,
        air_date=first_air,
        runtime_min=None,
        season_number=None,
        season_name=None,
        season_catalog_id=None,
        series_name=name,
        series_catalog_id=catalog_id,
        series_overview=result.overview,
        series_status=None,
        series_first_air_date=first_air,
        series_last_air_date=None,
        series_genres=None,
        series_languages=languages,
        series_cast=None,
        collections=None,
        media_type="tv",
        catalog_source="tmdb",
        catalog_id=catalog_id,
        catalog_score=float(result.popularity) if result.popularity is not None else None,
        catalog_downloads=None,
    )


def _extract_year(date_value: Optional[datetime]) -> Optional[int]:
    return date_value.year if date_value else None


@dataclass(slots=True)
class TvCatalogSearchService:
    settings: AppSettings
    ia_client: TvCatalogClient
    tmdb_client_factory: Callable[[], TMDbClient]

    def __init__(
        self,
        settings: AppSettings,
        ia_client: TvCatalogClient | None = None,
        tmdb_client_factory: Callable[[], TMDbClient] | None = None,
    ) -> None:
        self.settings = settings
        self.ia_client = ia_client or TvCatalogClient()
        self.tmdb_client_factory = tmdb_client_factory or TMDbClient

    async def search(
        self,
        *,
        query: str,
        limit: int = 10,
        year: int | None = None,
    ) -> TvCatalogMatchResponse:
        if not (self.settings.tmdb.api_key or self.settings.tmdb.access_token):
            raise RuntimeError("TMDb credentials are required for catalog matching")

        tmdb_client = self.tmdb_client_factory()
        try:
            tmdb_results = await tmdb_client.search_tv(
                query,
                language=self.settings.tmdb.language,
                include_adult=self.settings.tmdb.include_adult,
            )
        finally:
            await tmdb_client.close()

        tmdb_metadata = [_search_result_to_metadata(result) for result in tmdb_results]
        if year is not None:
            tmdb_metadata = [
                meta for meta in tmdb_metadata if _extract_year(meta.series_first_air_date) == year
            ]

        ia_candidates = self.ia_client.search(
            query,
            limit=max(limit * 3, 5),
            sorts=["downloads desc", "date desc"],
        )

        matches: List[TvCatalogMatch] = []
        for tmdb_episode in tmdb_metadata:
            candidates = self._match_candidates(tmdb_episode, ia_candidates, requested_year=year)
            if not candidates:
                continue
            match_key = uuid4().hex
            match = TvCatalogMatch(
                match_key=match_key,
                tmdb_id=int(tmdb_episode.catalog_id or 0),
                tmdb_episode=tmdb_episode,
                best_candidate=candidates[0],
                candidates=candidates,
            )
            _MATCH_REGISTRY[match_key] = match
            matches.append(match)
            if len(matches) >= limit:
                break

        return TvCatalogMatchResponse(matches=matches, total=len(matches))

    def _match_candidates(
        self,
        tmdb_episode: TvEpisodeMetadata,
        ia_episodes: List[TvEpisodeMetadata],
        requested_year: int | None = None,
    ) -> List[TvCatalogMatchCandidate]:
        tmdb_year = _extract_year(tmdb_episode.series_first_air_date)
        if requested_year is not None:
            tmdb_year = requested_year

        filtered: List[TvEpisodeMetadata] = []
        for episode in ia_episodes:
            candidate_year = _extract_year(episode.series_first_air_date or episode.air_date)
            if tmdb_year is not None and candidate_year is not None and tmdb_year != candidate_year:
                continue
            if episode.series_name and tmdb_episode.series_name:
                if episode.series_name.strip().lower() != tmdb_episode.series_name.strip().lower():
                    continue
            filtered.append(episode)

        if not filtered:
            return []

        filtered.sort(key=lambda ep: ep.catalog_downloads or 0, reverse=True)
        max_downloads = filtered[0].catalog_downloads or 0

        candidates: List[TvCatalogMatchCandidate] = []
        for episode in filtered:
            downloads = episode.catalog_downloads or 0
            score = downloads / max_downloads if max_downloads else 0.0
            candidates.append(
                TvCatalogMatchCandidate(
                    identifier=episode.catalog_id or tmdb_episode.catalog_id or "",
                    score=min(1.0, score),
                    downloads=downloads,
                    episode=episode,
                )
            )
        return candidates


def get_tv_catalog_search_service(
    settings: AppSettings = Depends(get_settings),
) -> TvCatalogSearchService:
    return TvCatalogSearchService(settings=settings)
