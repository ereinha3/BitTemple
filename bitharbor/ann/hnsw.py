from __future__ import annotations

from pathlib import Path

import faiss
import numpy as np

from bitharbor.ann.base import AnnIndex


class HnswIndex(AnnIndex):
    def __init__(self, dim: int, m: int, ef_construction: int, ef_search: int) -> None:
        self.dim = dim
        self.m = m
        self.ef_construction = ef_construction
        self.ef_search = ef_search
        self.index = faiss.IndexHNSWFlat(dim, m)
        self.index.hnsw.efConstruction = ef_construction
        self.index.hnsw.efSearch = ef_search

    def add(self, vectors: np.ndarray) -> np.ndarray:
        vecs = np.asarray(vectors, dtype=np.float32)
        if vecs.ndim == 1:
            vecs = vecs.reshape(1, -1)
        start = self.index.ntotal
        self.index.add(vecs)
        end = self.index.ntotal
        return np.arange(start, end, dtype=np.int64)

    def search(self, query: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
        q = np.asarray(query, dtype=np.float32)
        if q.ndim == 1:
            q = q.reshape(1, -1)
        distances, indices = self.index.search(q, k)
        return indices[0], distances[0]

    def persist(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(path))

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        self.index = faiss.read_index(str(path))
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search

    def reset(self) -> None:
        self.index.reset()

    def size(self) -> int:
        return self.index.ntotal

