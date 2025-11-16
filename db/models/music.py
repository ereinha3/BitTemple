from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class MusicTrack(Base):
    """Flattened music track metadata."""

    __tablename__ = "music_tracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    track_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    embedding_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="mp3")
    media_type: Mapped[str] = mapped_column(String(50), default="music", nullable=False)

    catalog_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    catalog_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    artist: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    artist_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    album: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    album_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    track_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_s: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    release_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    genres: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    license: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    audio_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    downloads: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    likes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    poster: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    backdrop: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    @classmethod
    async def get_all_hashes(cls, session) -> dict[str, list[str]]:
        """Get all hashes in the table."""

        from sqlalchemy import select

        result = await session.execute(
            select(cls.file_hash, cls.embedding_hash).where(
                cls.file_hash.isnot(None) | cls.embedding_hash.isnot(None)
            )
        )
        rows = result.all()
        return {
            "file_hashes": [row[0] for row in rows if row[0]],
            "embedding_hashes": [row[1] for row in rows if row[1]],
        }

    @classmethod
    async def hash_exists(cls, session, embedding_hash: str) -> bool:
        """Check if an embedding hash already exists in the table."""

        from sqlalchemy import select

        result = await session.execute(
            select(cls).where(cls.embedding_hash == embedding_hash)
        )
        return result.scalar_one_or_none() is not None
