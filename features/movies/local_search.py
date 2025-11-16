from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import AppSettings, get_settings
from db.models import IdMap, Movie
from domain.search import LocalMovieSearchHit, LocalMovieSearchResponse
from features.movies import vector_index
from features.movies.utils import movie_to_media
from infrastructure.embedding.sentence_bert_service import (
    SentenceBertService,
    TextEmbeddingResult,
    get_sentence_bert_service,
)


@dataclass(slots=True)
class _ResolvedMovie:
    movie: Movie
    score: float
    vector_hash: str | None = None


class MovieLocalSearchService:
    """Perform ANN-backed local searches over ingested movies."""

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
    ) -> LocalMovieSearchResponse:
        query = query.strip()
        if not query:
            return LocalMovieSearchResponse(results=[])

        embedding = self._embed(query)
        if embedding is None:
            return LocalMovieSearchResponse(results=[])

        # Fetch a few more candidates than requested to allow for missing mappings.
        fetch_k = max(limit * 2, limit)
        row_ids, scores = self._vector_search(embedding.vector, fetch_k)
        if row_ids.size == 0:
            return LocalMovieSearchResponse(results=[])

        resolved = await self._resolve_movies(session, row_ids.tolist(), scores.tolist())
        if not resolved:
            return LocalMovieSearchResponse(results=[])

        hits: list[LocalMovieSearchHit] = []
        count = 0
        for resolved_movie in resolved:
            if min_score is not None and resolved_movie.score < min_score:
                continue
            movie_media = movie_to_media(resolved_movie.movie)
            hits.append(
                LocalMovieSearchHit(
                    movie_id=resolved_movie.movie.id,
                    media_id=str(resolved_movie.movie.id),
                    vector_hash=resolved_movie.vector_hash,
                    score=float(resolved_movie.score),
                    movie=movie_media,
                )
            )
            count += 1
            if count >= limit:
                break
        return LocalMovieSearchResponse(results=hits)

    def _embed(self, query: str) -> TextEmbeddingResult | None:
        try:
            return self.embedding_service.encode(query)
        except Exception:  # pragma: no cover - defensive guard
            return None

    async def _resolve_movies(
        self,
        session: AsyncSession,
        row_ids: Sequence[int],
        scores: Sequence[float],
    ) -> list[_ResolvedMovie]:
        if not row_ids:
            return []

        stmt = select(IdMap.row_id, IdMap.media_id, IdMap.vector_hash).where(IdMap.row_id.in_(row_ids))
        result = await session.execute(stmt)
        row_to_media: dict[int, tuple[int, str | None]] = {}
        for row_id, media_id, vector_hash in result.all():
            try:
                row_to_media[row_id] = (int(media_id), vector_hash)
            except (TypeError, ValueError):
                continue

        if not row_to_media:
            return []

        movie_ids = list({media_id for media_id, _ in row_to_media.values()})
        movies_result = await session.execute(select(Movie).where(Movie.id.in_(movie_ids)))
        movie_by_id = {movie.id: movie for movie in movies_result.scalars()}

        ordered: list[_ResolvedMovie] = []
        for row_id, score in zip(row_ids, scores):
            mapping = row_to_media.get(row_id)
            if mapping is None:
                continue
            movie_id, vector_hash = mapping
            movie = movie_by_id.get(movie_id)
            if movie is None:
                continue
            ordered.append(_ResolvedMovie(movie=movie, score=float(score), vector_hash=vector_hash))
        # Deduplicate by movie id while preserving order.
        seen: set[int] = set()
        unique: list[_ResolvedMovie] = []
        for item in ordered:
            if item.movie.id in seen:
                continue
            seen.add(item.movie.id)
            unique.append(item)
        return unique


def get_movie_local_search_service(
    settings: AppSettings = Depends(get_settings),
) -> MovieLocalSearchService:
    return MovieLocalSearchService(settings=settings)
