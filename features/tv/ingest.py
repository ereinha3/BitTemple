from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import get_settings
from db.models import IdMap, TvEpisode, TvSeason, TvShow
from features.tv.vector_index import append as append_vector
from infrastructure.embedding.sentence_bert_service import get_sentence_bert_service
from utils.hashing import blake3_file, blake3_string


@dataclass(slots=True)
class TvIngestResult:
    file_hash: str
    video_path: Path
    vector_hash: str | None
    vector_row_id: int | None
    episode_id: int
    season_id: int
    show_id: int
    created: bool
    metadata: Mapping[str, object]


_settings = get_settings()
_embedding_service = get_sentence_bert_service()
_raid_root = Path(os.environ.get("RAID_PATH", str(_settings.server.pool_root)))


def _store_video_on_raid(source: Path, file_hash: str) -> Path:
    suffix = source.suffix.lower()
    shard = file_hash[:2]
    dest_dir = _raid_root / "tv" / shard
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{file_hash}{suffix}"
    if not dest.exists():
        shutil.copy2(source, dest)
    return dest


def _parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


async def ingest_catalog_tv(
    *,
    session: AsyncSession,
    video_path: Path,
    metadata: Mapping[str, object],
) -> TvIngestResult:
    metadata_dict = dict(metadata)
    video_path = video_path.expanduser().resolve()
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found at {video_path}")

    file_hash = blake3_file(video_path)

    existing_episode = (
        await session.execute(select(TvEpisode).where(TvEpisode.file_hash == file_hash))
    ).scalar_one_or_none()
    if existing_episode:
        existing_season = await session.get(TvSeason, existing_episode.season_id)
        existing_show = await session.get(TvShow, existing_season.show_id) if existing_season else None
        existing_path = Path(existing_episode.path) if existing_episode.path else video_path
        return TvIngestResult(
            file_hash=file_hash,
            video_path=existing_path,
            vector_hash=existing_episode.embedding_hash,
            vector_row_id=None,
            episode_id=existing_episode.id,
            season_id=existing_season.id if existing_season else 0,
            show_id=existing_show.id if existing_show else 0,
            created=False,
            metadata=metadata_dict,
        )

    episode_name = str(metadata_dict.get("episode_name") or metadata_dict.get("name") or "").strip()
    episode_overview = str(metadata_dict.get("episode_overview") or "").strip()
    series_name = str(metadata_dict.get("series_name") or "").strip()
    series_overview = str(metadata_dict.get("series_overview") or "").strip()

    text_components = [episode_name, episode_overview, series_name, series_overview]
    text_blob = " ".join(filter(None, text_components)).strip() or video_path.stem.replace("_", " ")

    embedding = _embedding_service.encode(text_blob)

    duplicate_episode = (
        await session.execute(select(TvEpisode).where(TvEpisode.embedding_hash == embedding.vector_hash))
    ).scalar_one_or_none()
    if duplicate_episode:
        existing_season = await session.get(TvSeason, duplicate_episode.season_id)
        existing_show = await session.get(TvShow, existing_season.show_id) if existing_season else None
        existing_path = Path(duplicate_episode.path) if duplicate_episode.path else video_path
        return TvIngestResult(
            file_hash=duplicate_episode.file_hash or file_hash,
            video_path=existing_path,
            vector_hash=duplicate_episode.embedding_hash,
            vector_row_id=None,
            episode_id=duplicate_episode.id,
            season_id=existing_season.id if existing_season else 0,
            show_id=existing_show.id if existing_show else 0,
            created=False,
            metadata=metadata_dict,
        )

    stored_path = _store_video_on_raid(video_path, file_hash)
    vector_row_id = append_vector(embedding.vector)

    series_catalog_id = (
        str(metadata_dict.get("series_catalog_id"))
        if metadata_dict.get("series_catalog_id") is not None
        else series_name or stored_path.stem
    )
    season_number = int(metadata_dict.get("season_number") or 1)
    season_catalog_id = (
        str(metadata_dict.get("season_catalog_id"))
        if metadata_dict.get("season_catalog_id") is not None
        else f"{series_catalog_id}::season-{season_number}"
    )
    season_name = metadata_dict.get("season_name") or f"Season {season_number}"

    show = (
        await session.execute(select(TvShow).where(TvShow.catalog_id == series_catalog_id))
    ).scalar_one_or_none()
    if show is None and series_name:
        show = (
            await session.execute(select(TvShow).where(TvShow.name == series_name))
        ).scalar_one_or_none()

    if show is None:
        show = TvShow(
            file_hash=None,
            embedding_hash=blake3_string(f"show:{series_catalog_id}"),
            path=None,
            format=stored_path.suffix.lstrip("."),
            media_type="tv",
            catalog_source=metadata_dict.get("catalog_source"),
            catalog_id=series_catalog_id,
            catalog_score=metadata_dict.get("ia_score"),
            catalog_downloads=metadata_dict.get("ia_downloads"),
            name=series_name or stored_path.stem,
            overview=series_overview or None,
            type=metadata_dict.get("series_type"),
            status=metadata_dict.get("series_status"),
            first_air_date=_parse_datetime(metadata_dict.get("series_first_air_date")),
            last_air_date=_parse_datetime(metadata_dict.get("series_last_air_date")),
            number_of_seasons=metadata_dict.get("series_number_of_seasons"),
            number_of_episodes=metadata_dict.get("series_number_of_episodes"),
            genres=metadata_dict.get("series_genres"),
            languages=metadata_dict.get("series_languages"),
            vote_average=metadata_dict.get("series_vote_average"),
            vote_count=metadata_dict.get("series_vote_count"),
            cast=metadata_dict.get("series_cast"),
            poster=metadata_dict.get("series_poster"),
            backdrop=metadata_dict.get("series_backdrop"),
        )
        session.add(show)
        await session.flush()

    season = (
        await session.execute(select(TvSeason).where(TvSeason.catalog_id == season_catalog_id))
    ).scalar_one_or_none()
    if season is None:
        season = (
            await session.execute(
                select(TvSeason).where(
                    TvSeason.show_id == show.id,
                    TvSeason.season_number == season_number,
                )
            )
        ).scalar_one_or_none()

    if season is None:
        season = TvSeason(
            show_id=show.id,
            file_hash=None,
            embedding_hash=blake3_string(f"season:{season_catalog_id}"),
            path=None,
            format=stored_path.suffix.lstrip("."),
            media_type="tv",
            catalog_source=metadata_dict.get("catalog_source"),
            catalog_id=season_catalog_id,
            name=str(season_name),
            overview=metadata_dict.get("season_overview"),
            season_number=season_number,
            poster=metadata_dict.get("season_poster"),
            backdrop=metadata_dict.get("season_backdrop"),
        )
        session.add(season)
        await session.flush()

    episode = TvEpisode(
        season_id=season.id,
        file_hash=file_hash,
        embedding_hash=embedding.vector_hash,
        path=str(stored_path),
        format=stored_path.suffix.lstrip("."),
        media_type="tv",
        catalog_source=metadata_dict.get("catalog_source"),
        catalog_id=metadata_dict.get("catalog_id") or series_catalog_id,
        name=episode_name or stored_path.stem,
        overview=episode_overview or series_overview or None,
        episode_number=int(metadata_dict.get("episode_number") or 1),
        air_date=_parse_datetime(metadata_dict.get("episode_air_date")),
        runtime_min=metadata_dict.get("episode_runtime_min"),
        poster=metadata_dict.get("poster"),
        backdrop=metadata_dict.get("backdrop"),
    )
    session.add(episode)
    await session.flush()

    if vector_row_id is not None:
        session.add(
            IdMap(
                row_id=vector_row_id,
                vector_hash=embedding.vector_hash,
                media_id=str(episode.id),
            )
        )

    return TvIngestResult(
        file_hash=file_hash,
        video_path=stored_path,
        vector_hash=embedding.vector_hash,
        vector_row_id=vector_row_id,
        episode_id=episode.id,
        season_id=season.id,
        show_id=show.id,
        created=True,
        metadata=metadata_dict,
    )
