"""Reusable Internet Archive catalog client primitives."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Generic, Iterable, Mapping, Sequence, TypeVar

import internetarchive as ia
from internetarchive import ArchiveSession, Item, configure

from app.settings import get_settings

logger = logging.getLogger(__name__)

CONFIG_FILE = Path(os.getenv("HOME", "")) / ".config" / "internetarchive" / "config"
_settings = get_settings()
IA_EMAIL = _settings.internet_archive.email
IA_PASSWORD = _settings.internet_archive.password

VIDEO_EXTENSIONS_DEFAULT = (".mp4", ".mkv", ".mov", ".avi", ".mpg", ".mpeg", ".webm")
SUBTITLE_EXTENSIONS_DEFAULT = (".srt", ".vtt")

if IA_EMAIL and IA_PASSWORD:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    configure(IA_EMAIL, IA_PASSWORD, config_file=str(CONFIG_FILE))

MediaT = TypeVar("MediaT")


@dataclass(slots=True, frozen=True)
class DownloadOptions:
    """Options that influence Internet Archive download behaviour."""

    include_subtitles: bool = True
    checksum: bool = False
    ignore_existing: bool = True


@dataclass(slots=True, frozen=True)
class AssetPlan(Generic[MediaT]):
    """Description of which remote files will be retrieved for an identifier."""

    identifier: str
    title: str | None
    metadata: Mapping[str, Any]
    video_file: str | None
    metadata_xml_file: str | None
    cover_art_file: str | None
    subtitle_files: tuple[str, ...]
    normalized_metadata: MediaT | None


@dataclass(slots=True, frozen=True)
class AssetBundle(Generic[MediaT]):
    """Local artefacts produced by a download operation."""

    identifier: str
    title: str | None
    metadata: Mapping[str, Any]
    video_path: Path | None
    cover_art_path: Path | None
    metadata_xml_path: Path | None
    subtitle_paths: tuple[Path, ...]
    normalized_metadata: MediaT | None = None


@dataclass(slots=True, frozen=True)
class MediaTypeConfig(Generic[MediaT]):
    """Configuration describing how to interact with a specific IA media type."""

    mediatype: str | None
    metadata_mapper: Callable[[str, Mapping[str, Any]], MediaT]
    default_source: str = "internet_archive"
    default_filters: tuple[str, ...] = ()
    video_extensions: tuple[str, ...] = VIDEO_EXTENSIONS_DEFAULT
    subtitle_extensions: tuple[str, ...] = SUBTITLE_EXTENSIONS_DEFAULT
    plan_class: type[AssetPlan] = AssetPlan
    bundle_class: type[AssetBundle] = AssetBundle


class InternetArchiveDownloadError(RuntimeError):
    """Raised when an Internet Archive download fails."""


class InternetArchiveClient:
    """Thin wrapper around ``internetarchive`` providing reusable primitives."""

    def __init__(self, session: ArchiveSession | None = None) -> None:
        if session is not None:
            self._session = session
        elif CONFIG_FILE.exists():
            self._session = ia.get_session(config_file=str(CONFIG_FILE))
        else:
            self._session = ia.get_session()

    def search(
        self,
        config: MediaTypeConfig[MediaT],
        title: str,
        limit: int = 20,
        *,
        sorts: Sequence[str] | None = None,
        filters: Sequence[str] | None = None,
    ) -> list[MediaT]:
        """Search the Internet Archive catalog for the provided ``title``."""

        params: dict[str, Any] = {"rows": max(1, limit), "page": 1}
        sort_tokens = self._normalize_sorts(sorts or ["downloads desc"])
        if sort_tokens:
            params["sort[]"] = sort_tokens

        base_query = f'title:"{title}"' if title else "*:*"
        composed_query = self._compose_query(
            base_query,
            mediatype=config.mediatype,
            extra_filters=[*config.default_filters, *(filters or ())],
        )

        best_by_key: dict[tuple[str, int | None], tuple[MediaT, int]] = {}
        search_hits = self._session.search_items(composed_query, params=params)
        for hit in search_hits:
            if not isinstance(hit, Mapping):
                continue
            identifier = hit.get("identifier")
            if not identifier:
                continue

            metadata = dict(hit)
            item_metadata = self._safe_fetch_metadata(identifier)
            payload = item_metadata if item_metadata else {"metadata": metadata}
            try:
                media = config.metadata_mapper(identifier, payload)
            except Exception:  # noqa: BLE001
                logger.debug("Failed to map IA metadata for %s", identifier, exc_info=True)
                continue

            downloads = self._safe_int(metadata.get("downloads"))
            if downloads is not None:
                self._assign_if_possible(media, "catalog_downloads", downloads)
                self._assign_if_possible(media, "catalog_score", float(downloads))

            if not getattr(media, "catalog_id", None):
                self._assign_if_possible(media, "catalog_id", identifier)
            if not getattr(media, "catalog_source", None):
                self._assign_if_possible(media, "catalog_source", config.default_source)

            key_title = self._normalise_title(media, identifier)
            key_year = self._extract_media_year(media)
            score = downloads or 0
            existing = best_by_key.get((key_title, key_year))
            if existing is None or score > existing[1]:
                best_by_key[(key_title, key_year)] = (media, score)

            if len(best_by_key) >= limit:
                continue

        ordered = [entry[0] for entry in best_by_key.values()]
        ordered.sort(
            key=lambda m: getattr(m, "catalog_downloads", None) or 0,  # type: ignore[attr-defined]
            reverse=True,
        )
        return ordered[:limit]

    def plan_download(
        self,
        config: MediaTypeConfig[MediaT],
        identifier: str,
        *,
        include_subtitles: bool = True,
    ) -> AssetPlan[MediaT]:
        """Plan which remote files will be retrieved for ``identifier``."""

        metadata = self.fetch_metadata(identifier)
        files = metadata.get("files", []) or []
        title = metadata.get("metadata", {}).get("title")

        video_file = self._select_video_file(files, config.video_extensions)
        metadata_xml_file = self._select_metadata_xml(files)
        cover_art_file = self._select_cover_art(files)
        subtitle_files = tuple(
            self._select_subtitles(files, config.subtitle_extensions) if include_subtitles else ()
        )

        normalized: MediaT | None
        try:
            normalized = config.metadata_mapper(identifier, metadata)
        except Exception:  # noqa: BLE001
            logger.debug(
                "Failed to normalise metadata for %s during plan", identifier, exc_info=True
            )
            normalized = None

        plan_type: type[AssetPlan] = config.plan_class
        return plan_type(
            identifier=identifier,
            title=title,
            metadata=metadata,
            video_file=video_file,
            metadata_xml_file=metadata_xml_file,
            cover_art_file=cover_art_file,
            subtitle_files=subtitle_files,
            normalized_metadata=normalized,
        )

    def download(
        self,
        config: MediaTypeConfig[MediaT],
        identifier: str,
        *,
        destination: Path | None = None,
        options: DownloadOptions | None = None,
    ) -> AssetBundle[MediaT]:
        """Download the primary assets for ``identifier``."""

        opts = options or DownloadOptions()
        plan = self.plan_download(config, identifier, include_subtitles=opts.include_subtitles)

        destination = destination or Path("/home/ethan/tmp")
        destination.mkdir(parents=True, exist_ok=True)
        target_dir = destination / identifier
        target_dir.mkdir(parents=True, exist_ok=True)

        download_targets: dict[str, str] = {}
        for remote in (plan.video_file, plan.metadata_xml_file, plan.cover_art_file):
            if remote:
                download_targets[remote] = remote
        for subtitle in plan.subtitle_files:
            download_targets[subtitle] = subtitle

        if download_targets:
            item = self.get_item(identifier)
            try:
                item.download(
                    destdir=str(target_dir),
                    files=download_targets,
                    ignore_existing=opts.ignore_existing,
                    checksum=opts.checksum,
                    no_directory=True,
                )
            except Exception as exc:  # noqa: BLE001
                raise InternetArchiveDownloadError(
                    f"Failed to download Internet Archive item '{identifier}'."
                ) from exc

        def local_path(name: str | None) -> Path | None:
            return target_dir / name if name else None

        subtitle_paths = tuple(
            path for path in (local_path(name) for name in plan.subtitle_files) if path is not None
        )

        bundle_type: type[AssetBundle] = config.bundle_class
        return bundle_type(
            identifier=identifier,
            title=plan.title,
            metadata=plan.metadata,
            video_path=local_path(plan.video_file),
            cover_art_path=local_path(plan.cover_art_file),
            metadata_xml_path=local_path(plan.metadata_xml_file),
            subtitle_paths=subtitle_paths,
            normalized_metadata=plan.normalized_metadata,
        )

    def collect_assets(
        self,
        config: MediaTypeConfig[MediaT],
        identifier: str,
        *,
        destination: Path | None = None,
        include_subtitles: bool = True,
        checksum: bool = False,
    ) -> AssetBundle[MediaT]:
        """Backward-compatible alias for :meth:`download`."""

        options = DownloadOptions(
            include_subtitles=include_subtitles,
            checksum=checksum,
        )
        return self.download(
            config,
            identifier,
            destination=destination,
            options=options,
        )

    def fetch_metadata(self, identifier: str) -> Mapping[str, Any]:
        item = self.get_item(identifier)
        payload = getattr(item, "item_metadata", {}) or {}
        if not isinstance(payload, Mapping):
            return {}
        return payload

    def get_item(self, identifier: str) -> Item:
        return self._session.get_item(identifier)

    def _safe_fetch_metadata(self, identifier: str) -> Mapping[str, Any]:
        try:
            return self.fetch_metadata(identifier)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Failed to enrich metadata for %s: %s", identifier, exc, exc_info=True)
            return {}

    def _normalize_sorts(self, sorts: Sequence[str] | None) -> list[str]:
        if not sorts:
            return []
        normalized: list[str] = []
        for sort in sorts:
            token = (sort or "").strip()
            if not token:
                continue
            if " " not in token:
                token = f"{token} desc"
            normalized.append(token)
        return normalized

    def _compose_query(
        self,
        base_query: str,
        *,
        mediatype: str | None,
        extra_filters: Sequence[str] | None,
    ) -> str:
        segments: list[str] = []
        query = base_query.strip()
        if query:
            segments.append(f"({query})")
        if mediatype:
            segments.append(f"mediatype:({mediatype})")
        if extra_filters:
            segments.extend(filter(None, (flt.strip() for flt in extra_filters)))
        return " AND ".join(segments) if segments else "*:*"

    def _select_video_file(
        self,
        files: Iterable[Mapping[str, Any]],
        extensions: Sequence[str],
    ) -> str | None:
        lower_exts = tuple(ext.lower() for ext in extensions)
        for file_info in files:
            name = file_info.get("name", "")
            source = file_info.get("source")
            lowered = name.lower()
            if (
                source == "original"
                and lowered.endswith(lower_exts)
                and ".ia." not in lowered
            ):
                return name
        for file_info in files:
            name = file_info.get("name", "")
            lowered = name.lower()
            if lowered.endswith(lower_exts) and ".ia." not in lowered:
                return name
        for file_info in files:
            name = file_info.get("name", "")
            if name.lower().endswith(lower_exts):
                return name
        return None

    def _select_metadata_xml(self, files: Iterable[Mapping[str, Any]]) -> str | None:
        for file_info in files:
            name = file_info.get("name", "")
            if name.endswith("_meta.xml"):
                return name
        for file_info in files:
            name = file_info.get("name", "")
            if name.endswith("_files.xml"):
                return name
        return None

    def _select_cover_art(self, files: Iterable[Mapping[str, Any]]) -> str | None:
        for file_info in files:
            if file_info.get("format") == "Item Tile":
                return file_info.get("name")
        for file_info in files:
            if file_info.get("format") == "Thumbnail":
                return file_info.get("name")
        for file_info in files:
            name = file_info.get("name", "")
            if name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                return name
        return None

    def _select_subtitles(
        self,
        files: Iterable[Mapping[str, Any]],
        extensions: Sequence[str],
    ) -> list[str]:
        lower_exts = tuple(ext.lower() for ext in extensions)
        subtitles: list[str] = []
        for file_info in files:
            name = file_info.get("name", "")
            if name.lower().endswith(lower_exts):
                subtitles.append(name)
        return subtitles

    def _safe_int(self, value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _assign_if_possible(self, obj: Any, attr: str, value: Any) -> None:
        try:
            setattr(obj, attr, value)
        except (AttributeError, TypeError):
            # Pydantic BaseModel instances allow attribute assignment by default, but
            # guard against custom models that may be frozen.
            pass

    def _normalise_title(self, media: Any, fallback: str) -> str:
        for attr in ("title", "name"):
            value = getattr(media, attr, None)
            if isinstance(value, str) and value.strip():
                return value.strip().lower()
        return fallback.lower()

    def _extract_media_year(self, media: Any) -> int | None:
        year = getattr(media, "year", None)
        if isinstance(year, int):
            return year
        release_date = getattr(media, "release_date", None)
        if getattr(release_date, "year", None):
            try:
                return int(release_date.year)
            except (TypeError, ValueError):
                return None
        first_air_date = getattr(media, "first_air_date", None)
        if getattr(first_air_date, "year", None):
            try:
                return int(first_air_date.year)
            except (TypeError, ValueError):
                return None
        return None

