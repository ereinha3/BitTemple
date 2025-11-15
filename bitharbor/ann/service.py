from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bitharbor.ann.hnsw import HnswIndex
from bitharbor.ann.vector_store import VectorStore
from bitharbor.models import IdMap
from bitharbor.settings import AppSettings, get_settings


@dataclass
class AnnResult:
    row_id: int
    score: float
    vector_hash: str | None = None
    media_id: str | None = None


class AnnService:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or get_settings()
        self.vector_store = VectorStore(
            self.settings.ann.vectors_path, dim=self.settings.embedding.dim
        )
        self.index_path: Path = self.settings.ann.index_path
        self.index = HnswIndex(
            dim=self.settings.embedding.dim,
            m=self.settings.ann.m,
            ef_construction=self.settings.ann.ef_construction,
            ef_search=self.settings.ann.ef_search,
        )
        self.index.load(self.index_path)
        if not self.index_path.exists():
            self.index.persist(self.index_path)
        self._ensure_index_consistency()

    def _ensure_index_consistency(self) -> None:
        row_count = self.vector_store.row_count()
        if row_count == 0 and self.index.size() == 0:
            return
        if row_count != self.index.size():
            vectors = self.vector_store.read_all()
            self.index.reset()
            if len(vectors):
                self.index.add(vectors)
            self.index.persist(self.index_path)

    async def add_embedding(
        self,
        session: AsyncSession,
        media_id: str,
        vector_hash: str,
        vector: np.ndarray,
    ) -> int:
        vec = np.asarray(vector, dtype=np.float32)
        row_id = self.vector_store.append(vec)
        ids = self.index.add(vec)
        index_id = int(ids[-1])
        if index_id != row_id:
            raise RuntimeError("Index id mismatch with vector store row id.")
        session.add(IdMap(row_id=row_id, vector_hash=vector_hash, media_id=media_id))
        await session.flush()
        self.index.persist(self.index_path)
        return row_id

    def search(self, query_vector: np.ndarray, k: int) -> list[AnnResult]:
        if self.index.size() == 0:
            return []
        q = np.asarray(query_vector, dtype=np.float32)
        if q.ndim > 1:
            q = q[0]
        norm = np.linalg.norm(q)
        if norm > 0:
            q = q / norm

        candidates_k = max(k, self.settings.ann.refine_candidates)
        indices, _ = self.index.search(q, candidates_k)
        valid_ids = [int(idx) for idx in indices if idx >= 0]
        if not valid_ids:
            return []
        vectors = self.vector_store.read_rows(valid_ids)
        if vectors.size == 0:
            return []
        sims = vectors @ q
        order = np.argsort(-sims)[:k]
        return [AnnResult(row_id=valid_ids[i], score=float(sims[i])) for i in order]

    async def resolve_media(
        self, session: AsyncSession, results: Sequence[AnnResult]
    ) -> list[AnnResult]:
        if not results:
            return []
        row_ids = [res.row_id for res in results]
        stmt = select(IdMap.row_id, IdMap.vector_hash, IdMap.media_id).where(IdMap.row_id.in_(row_ids))
        rows = await session.execute(stmt)
        mapping = {row_id: (vector_hash, media_id) for row_id, vector_hash, media_id in rows.all()}
        resolved: list[AnnResult] = []
        for res in results:
            vector_hash, media_id = mapping.get(res.row_id, (None, None))
            resolved.append(
                AnnResult(
                    row_id=res.row_id,
                    score=res.score,
                    vector_hash=vector_hash,
                    media_id=media_id,
                )
            )
        return resolved


_ann_service: AnnService | None = None


def get_ann_service() -> AnnService:
    global _ann_service
    if _ann_service is None:
        _ann_service = AnnService()
    return _ann_service

