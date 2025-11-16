import asyncio
import json
from pathlib import Path

import httpx
import pytest

from api.catalog.jamendo.client import JamendoClient


def test_search_tracks_returns_music_track_media(tmp_path):
    async def runner() -> None:
        payload = {
            "headers": {"status": "success"},
            "results": [
                {
                    "id": "123",
                    "name": "Test Track",
                    "duration": 180,
                    "artist_name": "Test Artist",
                    "artist_id": "991",
                    "album_name": "Test Album",
                    "album_id": "771",
                    "position": 2,
                    "releasedate": "2023-05-01",
                    "musicinfo": {
                        "tags": {
                            "genres": ["ambient", "lofi"],
                        }
                    },
                    "license_ccurl": "https://creativecommons.org/licenses/by-nc-nd/3.0/",
                    "audio": "https://cdn.jamendo.com/audio/123.mp3",
                    "image": "https://images.jamendo.com/123.jpg",
                    "stats": {
                        "rate_downloads_total": 42,
                        "likes": 7,
                    },
                }
            ],
        }

        async def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v3.0/tracks"
            params = dict(request.url.params)
            assert params["client_id"] == "dummy"
            return httpx.Response(200, json=payload)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as async_http:
            async with JamendoClient(client_id="dummy", client_secret="secret", http_client=async_http) as client:
                tracks = await client.search_tracks(
                    "ambient",
                    limit=1,
                    include=["musicinfo", "stats"],
                )

        assert len(tracks) == 1
        track = tracks[0]
        assert track.title == "Test Track"
        assert track.track_id == "123"
        assert track.artist == "Test Artist"
        assert track.artist_id == "991"
        assert track.album == "Test Album"
        assert track.album_id == "771"
        assert track.track_number == 2
        assert track.duration_s == 180
        assert track.genres == ["ambient", "lofi"]
        assert track.license.startswith("https://creativecommons.org/")
        assert track.audio_url.endswith("123.mp3")
        assert track.downloads == 42
        assert track.likes == 7

    asyncio.run(runner())


@pytest.mark.parametrize("content", [b"jamendo-bytes"])
def test_download_track_saves_file(tmp_path: Path, content: bytes):
    audio_url = "https://cdn.jamendo.com/audio/456.mp3"
    payload = {
        "headers": {"status": "success"},
        "results": [
            {
                "id": "456",
                "name": "Download Track",
                "duration": 200,
                "artist_name": "Artist",
                "artist_id": "321",
                "album_name": "Album",
                "album_id": "654",
                "position": 1,
                "releasedate": "2022-09-09",
                "musicinfo": {"tags": {"genres": ["ambient"]}},
                "license_cc": "cc-by",
                "audio": audio_url,
                "audiodownload_allowed": True,
                "audiodownload": audio_url,
                "stats": {"rate_downloads_total": 10, "likes": 1},
            }
        ],
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v3.0/tracks":
            params = dict(request.url.params)
            assert params.get("id") == "456"
            return httpx.Response(200, json=payload)
        if request.url == httpx.URL(audio_url):
            return httpx.Response(200, content=content)
        raise AssertionError(f"Unexpected request: {request.url}")

    async def runner() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as async_http:
            async with JamendoClient(client_id="dummy", client_secret="secret", http_client=async_http) as client:
                result = await client.download_track("456", destination=tmp_path)

        expected_path = tmp_path / "456.mp3"
        assert expected_path.exists()
        assert expected_path.read_bytes() == content

        track = result.track
        assert track.title == "Download Track"
        assert track.track_id == "456"
        assert track.artist == "Artist"
        assert track.artist_id == "321"
        assert track.album == "Album"
        assert track.album_id == "654"
        assert track.audio_url == audio_url
        assert track.downloads == 10
        assert track.likes == 1
        assert result.path == expected_path

    asyncio.run(runner())
