from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import httpx
from dotenv import load_dotenv

from domain.media.music import MusicTrackMedia

logger = logging.getLogger(__name__)

load_dotenv()

JAMENDO_BASE_URL = "https://api.jamendo.com/v3.0"


class JamendoAPIError(RuntimeError):
    """Generic Jamendo API error."""


class JamendoAuthError(JamendoAPIError):
    """Raised when Jamendo credentials are missing or invalid."""


@dataclass(slots=True)
class JamendoDownloadResult:
    """Result returned after downloading a Jamendo track."""

    track: MusicTrackMedia
    path: Path


class JamendoClient:
    """Thin wrapper around the Jamendo v3.0 API."""

    def __init__(
        self,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        timeout: float = 15.0,
        base_url: str = JAMENDO_BASE_URL,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.client_id = client_id or os.getenv("JAMENDO_ID")
        self.client_secret = client_secret or os.getenv("JAMENDO_SECRET")
        if not self.client_id:
            raise JamendoAuthError("Jamendo client ID is required. Set JAMENDO_ID in the environment.")

        self.base_url = base_url.rstrip("/")
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "JamendoClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def search_tracks(
        self,
        query: str,
        *,
        limit: int = 10,
        offset: int = 0,
        order: str | None = None,
        include: Sequence[str] | None = None,
        log_preview: bool = True,
    ) -> list[MusicTrackMedia]:
        """Search Jamendo tracks and return flattened MusicTrackMedia entries."""

        params: dict[str, Any] = {
            "client_id": self.client_id,
            "format": "json",
            "search": query,
            "limit": max(1, limit),
            "offset": max(0, offset),
        }
        params["order"] = order or "popularity_total_desc"
        include_parts = list(include or [])
        if "musicinfo" not in include_parts:
            include_parts.append("musicinfo")
        if "licenses" not in include_parts:
            include_parts.append("licenses")
        if "stats" not in include_parts:
            include_parts.append("stats")
        params["include"] = "+".join(include_parts)

        collected: list[MusicTrackMedia] = []
        page = 0
        while len(collected) < limit:
            page_offset = offset + page * params["limit"]
            params["offset"] = page_offset

            response = await self._client.get(
                f"{self.base_url}/tracks", params=params, follow_redirects=False
            )
            payload = self._parse_response(response)
            results = payload.get("results", [])
            if not results:
                break

            for item in results:
                allowed = item.get("audiodownload_allowed") or item.get(
                    "track_audiodownload_allowed"
                )
                if allowed is False:
                    continue
                track_media = self._coerce_track(item)
                collected.append(track_media)
                if len(collected) >= limit:
                    break

            total_pages = payload.get("headers", {}).get("results_fullcount")
            if len(results) < params["limit"]:
                break
            page += 1

        if log_preview:
            for preview in collected[:3]:
                logger.debug("Jamendo track preview %s", preview.model_dump())
        return collected

    async def download_track(
        self,
        track_id: str | int,
        *,
        destination: Path | None = None,
        filename: str | None = None,
    ) -> JamendoDownloadResult:
        """Download a Jamendo track by id."""

        params = {
            "client_id": self.client_id,
            "format": "json",
            "id": str(track_id),
            "include": "musicinfo+stats+licenses",
        }
        response = await self._client.get(
            f"{self.base_url}/tracks",
            params=params,
            follow_redirects=False,
        )
        payload = self._parse_response(response)
        results = payload.get("results") or []
        if not results:
            raise JamendoAPIError(f"Jamendo track {track_id} not found")

        item = results[0]
        track_media = self._coerce_track(item)
        download_allowed = item.get("audiodownload_allowed") or item.get("track_audiodownload_allowed")
        if download_allowed is False:
            raise JamendoAPIError(f"Jamendo track {track_id} does not allow downloads")

        audiodownload = item.get("audiodownload") or item.get("audiodownload_zip")
        if audiodownload:
            download_url = audiodownload
            params = None
        else:
            download_url = f"{self.base_url}/tracks/file"
            params = {
                "client_id": self.client_id,
                "id": str(track_id),
                "audioformat": "mp32",
                "action": "download",
            }

        dest_dir = destination or Path.home() / "tmp" / "jamendo"
        dest_dir.mkdir(parents=True, exist_ok=True)
        target_name = filename or f"{track_media.catalog_id or track_media.title}.mp3"
        target_path = dest_dir / target_name

        logger.info("Downloading Jamendo track %s to %s", track_media.catalog_id or track_id, target_path)
        async with self._client.stream(
            "GET",
            download_url,
            params=params,
            follow_redirects=True,
        ) as stream:
            stream.raise_for_status()
            with target_path.open("wb") as handle:
                async for chunk in stream.aiter_bytes():
                    handle.write(chunk)

        # If the file endpoint redirected we may not have the final URL; fall back to stored path
        if not track_media.audio_url:
            track_media.audio_url = str(target_path)

        return JamendoDownloadResult(track=track_media, path=target_path)

    def _parse_response(self, response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:  # pragma: no cover - defensive guard
            snippet = response.text[:200] if response.text else "<empty>"
            raise JamendoAPIError(
                f"Unexpected response from Jamendo API (status={response.status_code}): {snippet}"
            ) from exc

        headers = payload.get("headers") or {}
        status = headers.get("status")
        if status != "success":
            error_message = headers.get("error_message") or response.text
            raise JamendoAPIError(error_message)
        return payload

    @staticmethod
    def _ensure_list(values: Any) -> list[str] | None:
        if not values:
            return None
        if isinstance(values, list):
            return [str(v) for v in values if v]
        return [str(values)]

    @staticmethod
    def _parse_year(value: Any) -> int | None:
        if not value:
            return None
        try:
            text = str(value)
            for token in text.split("-"):
                if len(token) == 4 and token.isdigit():
                    return int(token)
            if len(text) == 4 and text.isdigit():
                return int(text)
        except Exception:  # pragma: no cover - defensive guard
            return None
        return None

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _coerce_track(self, item: dict[str, Any]) -> MusicTrackMedia:
        """Convert a Jamendo track payload into a flattened MusicTrackMedia."""

        title = item.get("name") or ""
        duration = self._safe_int(item.get("duration"))
        track_number = self._safe_int(item.get("position") or item.get("track_number"))
        release_year = self._parse_year(item.get("releasedate") or item.get("release_date"))
        genres = self._ensure_list(item.get("musicinfo", {}).get("tags", {}).get("genres"))
        downloads = self._safe_int(item.get("stats", {}).get("rate_downloads_total"))
        likes = self._safe_int(item.get("stats", {}).get("likes"))

        return MusicTrackMedia(
            title=title,
            track_id=str(item.get("id")) if item.get("id") else None,
            artist=item.get("artist_name"),
            artist_id=str(item.get("artist_id")) if item.get("artist_id") else None,
            album=item.get("album_name"),
            album_id=str(item.get("album_id")) if item.get("album_id") else None,
            track_number=track_number,
            duration_s=duration,
            release_year=release_year,
            genres=genres,
            license=item.get("license_ccurl") or item.get("license_cc"),
            audio_url=item.get("audio"),
            downloads=downloads,
            likes=likes,
            catalog_source="jamendo",
            catalog_id=str(item.get("id")) if item.get("id") else None,
            media_type="music",
            format="mp3",
            path=None,
            poster={"file_path": item.get("image")} if item.get("image") else None,
        )


_jamendo_client: JamendoClient | None = None


def get_jamendo_client() -> JamendoClient:
    """Return a singleton Jamendo client instance."""

    global _jamendo_client
    if _jamendo_client is None:
        _jamendo_client = JamendoClient()
    return _jamendo_client
