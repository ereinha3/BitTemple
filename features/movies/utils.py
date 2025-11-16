from __future__ import annotations

import subprocess
from pathlib import Path

from db.models import Movie
from domain.media.movies import MovieMedia


def movie_to_media(movie: Movie) -> MovieMedia:
    runtime = ensure_runtime_minutes(movie.path, movie.runtime_min)

    return MovieMedia(
        file_hash=movie.file_hash,
        embedding_hash=movie.embedding_hash,
        path=movie.path,
        format=movie.format,
        media_type=movie.media_type,
        catalog_source=movie.catalog_source,
        catalog_id=movie.catalog_id,
        catalog_score=movie.catalog_score,
        catalog_downloads=movie.catalog_downloads,
        poster=movie.poster,
        backdrop=movie.backdrop,
        title=movie.title,
        tagline=movie.tagline,
        overview=movie.overview,
        release_date=movie.release_date,
        year=movie.year,
        runtime_min=runtime,
        genres=movie.genres,
        languages=movie.languages,
        vote_average=movie.vote_average,
        vote_count=movie.vote_count,
        cast=movie.cast,
        rating=movie.rating,
    )


def ensure_runtime_minutes(path: str | None, current: int | None) -> int | None:
    if current is not None:
        return current
    if not path:
        return None
    return _probe_runtime_minutes(path)


def _probe_runtime_minutes(path: str) -> int | None:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        seconds = float(result.stdout.strip())
        return int(round(seconds / 60))
    except Exception:
        return None
