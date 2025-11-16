from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Optional

from db.models import MusicTrack
from domain.media.base import ImageMetadata
from domain.media.music import MusicTrackMedia

logger = logging.getLogger(__name__)


def _probe_duration_seconds(file_path: Path) -> Optional[int]:
    """Use ffprobe to determine audio duration in seconds."""

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(file_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        logger.warning("ffprobe executable not found when probing %s", file_path)
        return None
    except subprocess.CalledProcessError as exc:
        logger.warning("ffprobe failed for %s: %s", file_path, exc)
        return None

    try:
        payload = json.loads(result.stdout)
        duration_raw = payload["format"]["duration"]
        duration = float(duration_raw)
        return int(round(duration))
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Unable to parse ffprobe output for %s: %s", file_path, exc)
        return None


def ensure_duration_seconds(file_path: Optional[Path], current: Optional[int]) -> Optional[int]:
    """Ensure the duration is populated, probing disk if necessary."""

    if current is None and file_path and file_path.exists():
        return _probe_duration_seconds(file_path)
    return current


def track_to_media(model: MusicTrack) -> MusicTrackMedia:
    poster = ImageMetadata(**model.poster) if model.poster else None
    backdrop = ImageMetadata(**model.backdrop) if model.backdrop else None

    duration = ensure_duration_seconds(Path(model.path) if model.path else None, model.duration_s)

    return MusicTrackMedia(
        title=model.title,
        track_id=model.track_id,
        artist=model.artist,
        artist_id=model.artist_id,
        album=model.album,
        album_id=model.album_id,
        track_number=model.track_number,
        duration_s=duration,
        release_year=model.release_year,
        genres=model.genres,
        license=model.license,
        audio_url=model.audio_url,
        downloads=model.downloads,
        likes=model.likes,
        file_hash=model.file_hash,
        embedding_hash=model.embedding_hash,
        path=model.path,
        format=model.format,
        media_type=model.media_type,
        catalog_source=model.catalog_source,
        catalog_id=model.catalog_id,
        poster=poster,
        backdrop=backdrop,
    )


def apply_media_to_track(
    model: MusicTrack,
    media: MusicTrackMedia,
    *,
    file_hash: Optional[str] = None,
    path: Optional[str] = None,
    embedding_hash: Optional[str] = None,
) -> MusicTrack:
    model.title = media.title
    model.track_id = media.track_id
    model.artist = media.artist
    model.artist_id = media.artist_id
    model.album = media.album
    model.album_id = media.album_id
    model.track_number = media.track_number
    model.duration_s = media.duration_s
    model.release_year = media.release_year
    model.genres = media.genres
    model.license = media.license
    model.audio_url = media.audio_url
    model.downloads = media.downloads
    model.likes = media.likes
    model.catalog_source = media.catalog_source
    model.catalog_id = media.catalog_id
    model.media_type = media.media_type or "music"
    model.format = media.format or model.format
    model.poster = media.poster.model_dump() if media.poster else None
    model.backdrop = media.backdrop.model_dump() if media.backdrop else None
    if file_hash is not None:
        model.file_hash = file_hash
    if path is not None:
        model.path = path
    if embedding_hash is not None:
        model.embedding_hash = embedding_hash
    return model
