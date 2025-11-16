from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

import numpy as np

from infrastructure.ann.vector_store import VectorStore
from infrastructure.embedding.sentence_bert_service import get_sentence_bert_service

_sentence_service = get_sentence_bert_service()
_dim = _sentence_service.get_embedding_dimension()

_vector_root = Path(os.environ.get("MUSIC_VECTOR_DB_ROOT", "/mnt/vectordb")) / "songs"
_vector_root.mkdir(parents=True, exist_ok=True)

_vectors_path = Path(os.environ.get("MUSIC_VECTORS_PATH", str(_vector_root / "vectors.fp32")))
_vectors_path.parent.mkdir(parents=True, exist_ok=True)

_vector_store = VectorStore(_vectors_path, dim=_dim)


def _normalize(vectors: np.ndarray) -> np.ndarray:
    if vectors.size == 0:
        return vectors
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    safe = np.where(norms == 0.0, 1.0, norms)
    return vectors / safe


def append(vector: np.ndarray) -> int:
    vec = np.asarray(vector, dtype=np.float32)
    return _vector_store.append(vec)


def search(vector: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
    if k <= 0:
        return np.empty((0,), dtype=np.int64), np.empty((0,), dtype=np.float32)

    stored = _vector_store.read_all()
    if stored.size == 0:
        return np.empty((0,), dtype=np.int64), np.empty((0,), dtype=np.float32)

    stored = stored.astype(np.float32, copy=False)
    stored_norm = _normalize(stored)

    query = np.asarray(vector, dtype=np.float32)
    if query.ndim > 1:
        query = query.ravel()
    norm = np.linalg.norm(query)
    if norm == 0:
        return np.empty((0,), dtype=np.int64), np.empty((0,), dtype=np.float32)
    query_norm = query / norm

    sims = stored_norm @ query_norm
    order = np.argsort(sims)[::-1]
    top = order[: min(k, sims.shape[0])]
    return top.astype(np.int64), sims[top].astype(np.float32)
