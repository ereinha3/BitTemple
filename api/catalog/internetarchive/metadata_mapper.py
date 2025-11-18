from __future__ import annotations

import html
import re
from datetime import datetime
from typing import Any, Iterable, Mapping, Optional

from domain.media.movies import MovieMedia
from domain.media.tv import TvEpisodeMetadata
from domain.media.tv import TvShowMedia


HTML_TAG_RE = re.compile(r"<[^>]+>")
YEAR_RE = re.compile(r"(?P<year>\b\d{4}\b)")


def _clean_description(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        value = " ".join(str(item) for item in value if item)
    text = html.unescape(str(value))
    text = HTML_TAG_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    text = str(value)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d", "%Y"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed
        except ValueError:
            continue
    return None


def _parse_languages(raw: Any) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        langs = [str(item).strip() for item in raw if item]
    else:
        langs = [segment.strip() for segment in re.split(r"[,;/]", str(raw)) if segment.strip()]
    return langs or None


def _parse_subjects(raw: Any) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        subjects = [str(item).strip() for item in raw if item]
    else:
        subjects = [str(raw).strip()]
    return subjects or None


def _parse_year(*values: Any) -> int | None:
    for value in values:
        if value is None:
            continue
        if isinstance(value, int):
            if 1800 <= value <= 2100:
                return value
            continue
        text = str(value)
        # direct conversion
        try:
            candidate = int(text)
            if 1800 <= candidate <= 2100:
                return candidate
        except ValueError:
            pass
        # search inside free text
        match = YEAR_RE.search(text)
        if match:
            candidate = int(match.group("year"))
            if 1800 <= candidate <= 2100:
                return candidate
    return None


def _parse_runtime(raw: Any) -> int | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if text.isdigit():
        minutes = int(text)
        return minutes if minutes > 0 else None
    # handle HH:MM:SS or MM:SS
    parts = text.split(":")
    if len(parts) == 3:
        hours, minutes, seconds = parts
    elif len(parts) == 2:
        hours, minutes, seconds = "0", *parts
    else:
        return None
    try:
        total_minutes = int(hours) * 60 + int(minutes)
        if total_minutes <= 0:
            return None
        return total_minutes
    except ValueError:
        return None


def _parse_cast(raw: Any) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        cast = [str(item).strip() for item in raw if item]
    else:
        cast = [segment.strip() for segment in re.split(r"[,;/]", str(raw)) if segment.strip()]
    return cast or None


def _safe_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def map_metadata_to_movie(identifier: str, payload: Mapping[str, Any]) -> MovieMedia:
    """Coerce Internet Archive item metadata into ``MovieMedia``."""

    meta = payload.get("metadata", {}) if isinstance(payload, Mapping) else {}

    title = meta.get("title") or identifier
    overview = _clean_description(meta.get("description"))
    release_date = _parse_datetime(meta.get("date") or meta.get("publicdate"))
    year = _parse_year(meta.get("year"), meta.get("date"), meta.get("subject"), meta.get("publicdate"), title)
    if release_date and year is None:
        year = release_date.year

    runtime_min = _parse_runtime(meta.get("runtime"))
    languages = _parse_languages(meta.get("language"))
    subjects = _parse_subjects(meta.get("subject"))
    cast = _parse_cast(meta.get("creator") or meta.get("director") or meta.get("producer"))
    rating = meta.get("rating") or meta.get("licenseurl")

    downloads_raw = meta.get("downloads") or payload.get("downloads")
    favorites_raw = meta.get("num_favorites") or payload.get("num_favorites")
    download_count = _safe_int(downloads_raw)
    favorites_count = _safe_int(favorites_raw)
    catalog_score = favorites_count if favorites_count is not None else download_count

    movie = MovieMedia(
        file_hash=None,
        embedding_hash=None,
        path=None,
        media_type="movie",
        format=meta.get("format"),
        poster=None,
        backdrop=None,
        title=title,
        tagline=meta.get("tagline"),
        overview=overview,
        release_date=release_date,
        year=year,
        runtime_min=runtime_min,
        genres=subjects,
        languages=languages,
        vote_average=None,
        vote_count=None,
        cast=cast,
        rating=rating,
        catalog_source="internet_archive",
        catalog_id=identifier,
        catalog_downloads=download_count,
        catalog_score=float(catalog_score) if catalog_score is not None else None,
    )

    return movie


def _slugify(value: str | None) -> str | None:
    if value is None:
        return None
    text = re.sub(r"[^A-Za-z0-9]+", "-", value.lower()).strip("-")
    return text or None


def map_metadata_to_tv(identifier: str, payload: Mapping[str, Any]) -> TvEpisodeMetadata:
    """Coerce Internet Archive item metadata into ``TvEpisodeMetadata``."""

    meta = payload.get("metadata", {}) if isinstance(payload, Mapping) else {}

    raw_title = meta.get("title") or meta.get("program") or identifier
    series_name = meta.get("program") or meta.get("series") or raw_title
    name = raw_title
    overview = _clean_description(meta.get("description"))
    first_air_date = _parse_datetime(
        meta.get("first_air_date") or meta.get("start_time") or meta.get("date") or meta.get("publicdate")
    )
    last_air_date = _parse_datetime(meta.get("last_air_date") or meta.get("stop_time"))

    languages = _parse_languages(meta.get("language"))
    subjects = _parse_subjects(meta.get("subject"))
    cast = _parse_cast(meta.get("creator") or meta.get("cast") or meta.get("director"))

    downloads_raw = meta.get("downloads") or payload.get("downloads")
    favorites_raw = meta.get("num_favorites") or payload.get("num_favorites")
    download_count = _safe_int(downloads_raw)
    favorites_count = _safe_int(favorites_raw)
    catalog_score = favorites_count if favorites_count is not None else download_count

    status = meta.get("status")
    media_subtype = meta.get("type")
    vote_average = _safe_float(meta.get("vote_average"))
    vote_count = _safe_int(meta.get("vote_count"))

    runtime_text = meta.get("runtime") or meta.get("length")
    runtime_min = _parse_runtime(runtime_text)

    season_label: str | None = None
    collections = meta.get("collection")
    if isinstance(collections, list):
        # Prefer a descriptive collection name if available.
        preferred = next(
            (col for col in collections if col not in {"tvnews", "tvarchive", "TV-CSPAN"}), None
        )
        season_label = preferred or (collections[0] if collections else None)
    elif isinstance(collections, str):
        season_label = collections
    season_name = (season_label or "Season 1").replace("_", " ").title()

    series_catalog_id = _slugify(series_name) or identifier
    season_number = 1
    season_catalog_id = f"{series_catalog_id}::season-{season_number}"
    episode_number = _safe_int(meta.get("episode")) or 1

    episode = TvEpisodeMetadata(
        name=name,
        overview=overview,
        episode_number=episode_number,
        season_number=season_number,
        season_name=season_name,
        season_catalog_id=season_catalog_id,
        series_name=series_name,
        series_catalog_id=series_catalog_id,
        series_overview=overview,
        series_status=status,
        series_first_air_date=first_air_date,
        series_last_air_date=last_air_date,
        series_genres=subjects,
        series_languages=languages,
        series_cast=cast,
        collections=collections if isinstance(collections, list) else [collections] if isinstance(collections, str) else None,
        air_date=first_air_date,
        runtime_min=runtime_min,
        media_type="tv_episode",
        catalog_source="internet_archive",
        catalog_id=identifier,
        catalog_downloads=download_count,
        catalog_score=float(catalog_score) if catalog_score is not None else None,
    )

    return episode


__all__ = ["map_metadata_to_movie", "map_metadata_to_tv"]
