from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Sequence, Tuple

import numpy as np


class AnnIndex(ABC):
    dim: int

    @abstractmethod
    def add(self, vectors: np.ndarray) -> np.ndarray:
        """Add vectors to the index and return their internal ids."""

    @abstractmethod
    def search(self, query: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """Return (indices, distances) for the query vector."""

    @abstractmethod
    def persist(self, path: Path) -> None:
        """Persist the index to disk."""

    @abstractmethod
    def load(self, path: Path) -> None:
        """Load the index from disk."""

    @abstractmethod
    def reset(self) -> None:
        """Reset internal state."""

    @abstractmethod
    def size(self) -> int:
        """Number of vectors currently stored."""

