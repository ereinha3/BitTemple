from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

import numpy as np

from app.settings import get_settings
from infrastructure.ann.vector_store import VectorStore
from infrastructure.embedding.sentence_bert_service import get_sentence_bert_service

_settings = get_settings()
_sentence_service = get_sentence_bert_service()
_dim = _sentence_service.get_embedding_dimension()
_metric = "l2"
_graph_degree = _settings.ann.graph_degree
_complexity = _settings.ann.complexity
_search_memory_budget = _settings.ann.search_memory_budget
_num_threads = _settings.ann.num_threads
_rebuild_batch = max(1, _settings.ann.rebuild_batch)

_base_root = Path(
    Path(os.environ.get("VECTOR_DB_PATH", str(_settings.ann.index_directory.parent)))
)
_movie_root = _base_root / "movies"
_movie_root.mkdir(parents=True, exist_ok=True)

_vectors_path = _movie_root / "vectors.fp32"
_index_directory = _movie_root / "diskann"
_index_directory.mkdir(parents=True, exist_ok=True)

_vector_store = VectorStore(_vectors_path, dim=_dim)
_diskann_index = None


def _ensure_index_built() -> None:
    return None


def append(vector: np.ndarray) -> int:
    vec = np.asarray(vector, dtype=np.float32)
    row_id = _vector_store.append(vec)
    return row_id


def search(vector: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
    return np.array([]), np.array([])

