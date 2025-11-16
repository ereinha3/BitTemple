from __future__ import annotations

import mimetypes
import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.catalog.jamendo import get_jamendo_client
from app.settings import get_settings
from db.models import MusicTrack
from db.session import get_session
from domain.media.music import MusicTrackMedia
from features.music import vector_index
from features.music.utils import (
    apply_media_to_track,
    ensure_duration_seconds,
    track_to_media,
)
from infrastructure.embedding.sentence_bert_service import get_sentence_bert_service
from utils.hashing import blake3_file

router = APIRouter(prefix="/music", tags=["music"])

_settings = get_settings()
_music_root = Path(os.environ.get("MUSIC_STORAGE_ROOT", "/mnt/raid/songs"))
_music_root.mkdir(parents=True, exist_ok=True)
_embedding_service = get_sentence_bert_service()


class JamendoSearchResponse(BaseModel):
    results: list[MusicTrackMedia] = Field(default_factory=list)


class JamendoDownloadRequest(BaseModel):
    track_id: str = Field(..., description="Jamendo track identifier")
    destination: Path | None = Field(
        default=None, description="Optional override for temporary download location"
    )


class JamendoDownloadResponse(BaseModel):
    track: MusicTrackMedia
    file_hash: str | None = None
    path: str | None = None
    created: bool = True


@router.get("/catalog/search", response_model=JamendoSearchResponse)
async def search_catalog_music(
    query: str = Query(..., min_length=1, description="Jamendo search query"),
    limit: int = Query(10, ge=1, le=50),
) -> JamendoSearchResponse:
    client = get_jamendo_client()
    tracks = await client.search_tracks(
        query,
        limit=limit,
        include=["musicinfo", "stats", "licenses"],
    )
    return JamendoSearchResponse(results=tracks)


@router.post("/catalog/download", response_model=JamendoDownloadResponse)
async def download_catalog_music(
    payload: JamendoDownloadRequest,
    session: AsyncSession = Depends(get_session),
) -> JamendoDownloadResponse:
    client = get_jamendo_client()
    download = await client.download_track(
        payload.track_id,
        destination=payload.destination,
    )

    track_media = download.track
    stored_path, file_hash, created = await _persist_track(session, download.path, track_media)
    await session.commit()

    track_media.path = str(stored_path) if stored_path else None
    track_media.file_hash = file_hash
    track_media.format = stored_path.suffix.lstrip(".") if stored_path else track_media.format

    return JamendoDownloadResponse(
        track=track_media,
        file_hash=file_hash,
        path=str(stored_path) if stored_path else None,
        created=created,
    )


@router.get("/all", response_model=list[MusicTrackMedia])
async def list_all_music(session: AsyncSession = Depends(get_session)) -> list[MusicTrackMedia]:
    result = await session.scalars(select(MusicTrack).order_by(MusicTrack.title))
    return [track_to_media(row) for row in result]


@router.get("/local/search", response_model=list[MusicTrackMedia])
async def search_local_music(
    query: str = Query(..., min_length=1, description="Search local library"),
    limit: int = Query(20, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> list[MusicTrackMedia]:
    like_expr = f"%{query}%"
    stmt = (
        select(MusicTrack)
        .where(
            or_(
                MusicTrack.title.ilike(like_expr),
                MusicTrack.artist.ilike(like_expr),
                MusicTrack.album.ilike(like_expr),
            )
        )
        .order_by(MusicTrack.title)
        .limit(limit)
    )
    result = await session.scalars(stmt)
    return [track_to_media(row) for row in result]


@router.get("/stream")
async def stream_music(
    file_hash: str = Query(..., description="BLAKE3 hash of the stored track"),
    range_header: str | None = Header(None, alias="Range"),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    track = await session.scalar(select(MusicTrack).where(MusicTrack.file_hash == file_hash))
    if track is None or not track.path:
        raise HTTPException(status_code=404, detail="Track not found")

    file_path = Path(track.path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Track file missing on disk")

    file_size = file_path.stat().st_size
    if file_size == 0:
        raise HTTPException(status_code=404, detail="Track file is empty")

    start, end = _parse_range(range_header, file_size)
    headers = {"Accept-Ranges": "bytes"}
    status_code = 206 if range_header else 200
    content_length = end - start + 1
    headers["Content-Length"] = str(content_length)
    if status_code == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"

    media_type = mimetypes.guess_type(file_path.name)[0] or "audio/mpeg"
    return StreamingResponse(
        _iter_file(file_path, start, end),
        media_type=media_type,
        status_code=status_code,
        headers=headers,
    )


async def _persist_track(
    session: AsyncSession,
    downloaded_path: Path,
    media: MusicTrackMedia,
) -> tuple[Path, str, bool]:
    downloaded_path = downloaded_path.resolve()
    file_hash = blake3_file(downloaded_path)
    stored_path = _store_track_on_raid(downloaded_path, file_hash)

    text_blob = _build_embedding_corpus(media)
    embedding = _embedding_service.encode(text_blob)
    media.embedding_hash = embedding.vector_hash
    vector_index.append(embedding.vector)

    media.duration_s = ensure_duration_seconds(stored_path, media.duration_s)

    stmt = select(MusicTrack).where(
        (MusicTrack.catalog_source == media.catalog_source)
        & (MusicTrack.catalog_id == media.catalog_id)
    )
    existing = await session.scalar(stmt)

    if existing:
        apply_media_to_track(
            existing,
            media,
            file_hash=file_hash,
            path=str(stored_path),
            embedding_hash=embedding.vector_hash,
        )
        created = False
    else:
        model = MusicTrack(title=media.title)
        apply_media_to_track(
            model,
            media,
            file_hash=file_hash,
            path=str(stored_path),
            embedding_hash=embedding.vector_hash,
        )
        session.add(model)
        created = True

    return stored_path, file_hash, created


def _store_track_on_raid(source: Path, file_hash: str) -> Path:
    suffix = source.suffix.lower() or ".bin"
    shard = file_hash[:2] if file_hash else "00"
    dest_dir = _music_root / shard
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{file_hash}{suffix}"

    if dest.exists():
        if source != dest:
            source.unlink(missing_ok=True)
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), dest)
    return dest


def _parse_range(range_header: str | None, file_size: int) -> tuple[int, int]:
    if not range_header:
        return 0, file_size - 1

    if "=" not in range_header:
        raise HTTPException(status_code=416, detail="Invalid Range header format")

    unit, byte_range = range_header.strip().split("=", 1)
    if unit != "bytes":
        raise HTTPException(status_code=416, detail="Unsupported range unit")

    first_range = byte_range.split(",")[0].strip()
    if "-" not in first_range:
        raise HTTPException(status_code=416, detail="Invalid Range header format")

    start_str, end_str = first_range.split("-", 1)
    if start_str == "":
        length = int(end_str)
        start = max(file_size - length, 0)
        end = file_size - 1
    else:
        start = int(start_str)
        end = int(end_str) if end_str else file_size - 1
        if start >= file_size or start > end:
            raise HTTPException(status_code=416, detail="Invalid range values")
        end = min(end, file_size - 1)

    return start, end


def _iter_file(path: Path, start: int, end: int, chunk_size: int = 1024 * 1024):
    with path.open("rb") as file_obj:
        file_obj.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = file_obj.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def _build_embedding_corpus(media: MusicTrackMedia) -> str:
    parts: list[str] = []
    parts.append(media.title or "")
    if media.artist:
        parts.append(media.artist)
    if media.album:
        parts.append(media.album)
    if media.genres:
        parts.extend(media.genres)
    if media.license:
        parts.append(media.license)
    return " ".join(filter(None, parts)) or media.title or "unknown track"
