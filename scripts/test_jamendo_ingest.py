from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import httpx

API_ROOT = os.environ.get("BITHARBOR_API_ROOT", "http://localhost:8080/api/v1")
TOKEN = os.environ["BITHARBOR_ADMIN_TOKEN"]  # export your JWT before running

SEARCH_QUERY = os.environ.get("JAMENDO_SEARCH", "lofi ambient")
DOWNLOAD_LIMIT = int(os.environ.get("JAMENDO_DOWNLOAD_LIMIT", "3"))


async def main() -> None:
    headers = {"Authorization": f"Bearer {TOKEN}"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: search catalog
        search_resp = await client.get(
            f"{API_ROOT}/music/catalog/search",
            params={"query": SEARCH_QUERY, "limit": DOWNLOAD_LIMIT},
            headers=headers,
        )
        search_resp.raise_for_status()
        search_data = search_resp.json()
        print("Search results:\n", json.dumps(search_data, indent=2))

        tracks = search_data.get("results") or []
        if not tracks:
            print("No tracks returned for query.")
            return

        # Step 2: download the first track
        first_track = tracks[0]
        track_id = first_track.get("track_id") or first_track.get("catalog_id")
        if not track_id:
            raise RuntimeError("Track is missing track_id/catalog_id")

        print(f"\nDownloading track {track_id} ...")
        download_resp = await client.post(
            f"{API_ROOT}/music/catalog/download",
            json={"track_id": track_id},
            headers=headers,
        )
        download_resp.raise_for_status()
        download_data = download_resp.json()
        print("Download response:\n", json.dumps(download_data, indent=2))

        # Step 3: list local library
        local_resp = await client.get(f"{API_ROOT}/music/all", headers=headers)
        local_resp.raise_for_status()
        local_data = local_resp.json()
        print("\nLocal library:\n", json.dumps(local_data, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
