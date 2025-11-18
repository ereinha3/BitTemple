from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np
from fastapi import Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.settings import AppSettings, get_settings
from db.models import IdMap, TvEpisode, TvSeason, TvShow
from domain.media.tv import TvEpisodeMetadata
from features.tv import vector_index
from infrastructure.embedding.sentence_bert_service import (
    SentenceBertService,
    TextEmbeddingResult,
    get_sentence_bert_service,
)


class LocalTvSearchHit(BaseModel):
    episode_id: int
    media_id: str
    score: float
    episode: TvEpisodeMetadata


class LocalTvSearchResponse(BaseModel):
    results: list[LocalTvSearchHit] = Field(default_factory=list)


@dataclass(slots=True)
class _ResolvedEpisode:
    episode: TvEpisode
    score: float


class TvLocalSearchService:
    """Perform ANN-backed local searches over ingested TV episodes."""

    def __init__(
        self,
        settings: AppSettings | None = None,
        embedding_service: SentenceBertService | None = None,
        vector_search_fn: Callable[[np.ndarray, int], tuple[np.ndarray, np.ndarray]] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.embedding_service = embedding_service or get_sentence_bert_service()
        self._vector_search = vector_search_fn or vector_index.search

    async def search(
        self,
        session: AsyncSession,
        query: str,
        limit: int = 10,
        *,
        min_score: float | None = None,
    ) -> LocalTvSearchResponse:
        query = query.strip()
        if not query:
            return LocalTvSearchResponse(results=[])

        embedding = self._embed(query)
        if embedding is None:
            return LocalTvSearchResponse(results=[])

        fetch_k = max(limit * 2, limit)
        row_ids, scores = self._vector_search(embedding.vector, fetch_k)
        if row_ids.size == 0:
            return LocalTvSearchResponse(results=[])

        resolved = await self._resolve_episodes(session, row_ids.tolist(), scores.tolist())
        if not resolved:
            return LocalTvSearchResponse(results=[])

        hits: list[LocalTvSearchHit] = []
        count = 0
        for resolved_episode in resolved:
            if min_score is not None and resolved_episode.score < min_score:
                continue
            metadata = self._to_episode_metadata(resolved_episode.episode)
            hits.append(
                LocalTvSearchHit(
                    episode_id=resolved_episode.episode.id,
                    media_id=str(resolved_episode.episode.id),
                    score=float(resolved_episode.score),
                    episode=metadata,
                )
            )
            count += 1
            if count >= limit:
                break
        return LocalTvSearchResponse(results=hits)

    def _embed(self, query: str) -> TextEmbeddingResult | None:
        try:
            return self.embedding_service.encode(query)
        except Exception:  # pragma: no cover - defensive guard
            return None

    async def _resolve_episodes(
        self,
        session: AsyncSession,
        row_ids: Sequence[int],
        scores: Sequence[float],
    ) -> list[_ResolvedEpisode]:
        if not row_ids:
            return []

        stmt = select(IdMap.row_id, IdMap.media_id).where(IdMap.row_id.in_(row_ids))
        result = await session.execute(stmt)
        row_to_media: dict[int, int] = {}
        for row_id, media_id in result.all():
            try:
                row_to_media[row_id] = int(media_id)
            except (TypeError, ValueError):
                continue

        if not row_to_media:
            return []

        episode_ids = list(set(row_to_media.values()))
        episodes_stmt = (
            select(TvEpisode)
            .where(TvEpisode.id.in_(episode_ids))
            .options(selectinload(TvEpisode.season).selectinload(TvSeason.show))
        )
        episodes_result = await session.execute(episodes_stmt)
        episode_by_id = {episode.id: episode for episode in episodes_result.scalars()}

        ordered: list[_ResolvedEpisode] = []
        for row_id, score in zip(row_ids, scores):
            episode_id = row_to_media.get(row_id)
            if episode_id is None:
                continue
            episode = episode_by_id.get(episode_id)
            if episode is None:
                continue
            ordered.append(_ResolvedEpisode(episode=episode, score=float(score)))

        seen: set[int] = set()
        unique: list[_ResolvedEpisode] = []
        for item in ordered:
            if item.episode.id in seen:
                continue
            seen.add(item.episode.id)
            unique.append(item)
        return unique

    @staticmethod
    def _to_episode_metadata(episode: TvEpisode) -> TvEpisodeMetadata:
        season: TvSeason | None = episode.season
        show: TvShow | None = season.show if season else None
        return TvEpisodeMetadata(
            name=episode.name,
            overview=episode.overview,
            episode_number=episode.episode_number,
            air_date=episode.air_date,
            runtime_min=episode.runtime_min,
            season_number=season.season_number if season else None,
            season_name=season.name if season else None,
            season_catalog_id=season.catalog_id if season else None,
            series_name=show.name if show else None,
            series_catalog_id=show.catalog_id if show else None,
            series_overview=show.overview if show else None,
            series_status=show.status if show else None,
            series_first_air_date=show.first_air_date if show else None,
            series_last_air_date=show.last_air_date if show else None,
            series_genres=show.genres if show else None,
            series_languages=show.languages if show else None,
            series_cast=show.cast if show else None,
            collections=None,
            file_hash=episode.file_hash,
            embedding_hash=episode.embedding_hash,
            path=episode.path,
            format=episode.format,
            media_type=episode.media_type,
            catalog_source=episode.catalog_source,
            catalog_id=episode.catalog_id,
            catalog_score=None,
            catalog_downloads=None,
        )


def get_tv_local_search_service(
    settings: AppSettings = Depends(get_settings),
) -> TvLocalSearchService:
    return TvLocalSearchService(settings=settings)
