"""Reusable Internet Archive catalog client primitives."""

from __future__ import annotations

import logging
import os
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Generic, Iterable, Mapping, Sequence, TypeVar, Optional

import internetarchive as ia
from internetarchive import ArchiveSession, Item, configure

import requests

FIELDS = [
    "avg_rating",
    "btih",
    "collection",
    "creator",
    "date",
    "description",
    "downloads",
    "format",
    "identifier",
    "indexflag",
    "item_size",
    "language", 
    "mediatype",
    "month",
    "num_reviews",
    "oai_updatedate",
    "publicdate",   
    "reviewdate",
    "subject",
    "title",
    "week",
    "year",
]

GENRES = [
    "Action",
    "Adventure",
    "Anime",
    "Animation",
    "Biography",
    "Comedy",
    "Crime",
    "Documentary",
    "Drama",
    "Family",
    "Fantasy",
    "History",
    "Horror",
    "Music",
    "Mystery",
    "Romance",
    "Sci-Fi",
    "Science Fiction"
    "Thriller",
    "War",
    "Western",
]

BLOCKED_SUBJECTS = [
    "pornography",
    "porn",
]

CONFIG_FILE = Path(os.getenv("HOME", "")) / ".config" / "internetarchive" / "config"

@dataclass(slots=True, frozen=True)
class MovieSearchQuery:
    query: Optional[str] = None
    title: Optional[str] = None
    year: Optional[int] = None
    genres: Optional[list[str]] = field(default_factory=list)
    creator: Optional[str] = None
    languages: Optional[list[str]] = field(default_factory=lambda: ['en', 'eng', "English"])
    legal_only: bool = False
    safe_search: bool = True

    def to_ia(self) -> str:
        query = []

        if self.title:
            query.append(f'title:"{self.title}"')

        if self.year:
            query.append(f'year:{self.year}')

        if self.genres:

            safe_search_insert = ""
            genres = self.genres
            if self.safe_search:
                genres = [genre for genre in genres if genre.lower() not in BLOCKED_SUBJECTS]
                safe_search_insert = " AND NOT " + f'({" OR ".join([f"({genre})" for genre in BLOCKED_SUBJECTS])})'

            if len(self.genres) > 1:
                query.append(f'subject:({" OR ".join([f"({genre})" for genre in self.genres])} {safe_search_insert})')
            else:
                query.append(f'subject:"{self.genres[0]}"')

        if self.creator:
            query.append(f'creator:"{self.creator}"')

        if self.languages:
            if len(self.languages) > 1:
                query.append(f'language:({" OR ".join([f"({language})" for language in self.languages])})')
            else:
                query.append(f'language:"{self.languages[0]}"')

        if self.legal_only:
            query.append(f'licenseurl:http*{self.license}*')
        return " AND ".join(query)


class InternetArchiveClient:
    """Thin wrapper around ``internetarchive`` providing reusable primitives."""

    def __init__(self, session: ArchiveSession | None = None) -> None:
        if session is not None:
            self._session = session
        elif CONFIG_FILE.exists():
            self._session = ia.get_session(config_file=str(CONFIG_FILE))
        self.url = 'https://archive.org/advancedsearch.php'
        self.max_count = 10_000
        self.base_query = "mediatype:movies"

    def search(
        self,
        query: MovieSearchQuery,
        rows: int = 100,
        page: int = 1,
    ) -> tuple[dict, Optional[dict]]:

        params = {
            "q": f"{self.base_query} AND {query.to_ia()}",
            "fl[]": FIELDS,
            "sort[]": ["downloads desc"],
            'rows': min(rows, self.max_count),
            'page': page,
            'output': 'json',
        }

        response = requests.get(self.url, params=params)

        if response.status_code != 200:
            return None, response.json()

        return response.json(), None

    def search_id(
        self,
        collection: str,
        rows: int = 1_000,
        page: int = 1,
    ) -> tuple[dict, Optional[dict]]:

        params = {
            "q": f"collection:{collection} mediatype:collection",
            "fl[]": FIELDS,
            'rows': min(rows, self.max_count),
            'page': page,
            'output': 'json',
            'sort[]': ['downloads desc'],
        }

        response = requests.get(self.url, params=params)

        if response.status_code != 200:
            return None, response.json()

        return response.json(), None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('collection', type=str, default='')
    args = parser.parse_args()

    client = InternetArchiveClient()

    query = MovieSearchQuery()

    result, error = client.search_id(collection=args.collection)
    response = result.get("response").get("docs")

    rows = 1_000


    for i in range(client.max_count // rows):
        result, error = client.search_id(collection=args.collection, rows=rows, page=i+1)
        response = result.get("response").get("docs")
        for r in response:
            title = r.get("title").lower()
            if not r.get("mediatype") == "collection":
                continue
            if 'movie' in title or 'film' in title:
                print(r.get("title"))
                continue
            if 'dvd' in title or 'blu-ray' in title or 'vhs' in title:
                print(r.get("title"))
                continue
            genres = r.get("subject")
            if genres:
                if isinstance(genres, list):
                    for genre in genres:
                        if genre.lower() in GENRES:
                            print(r.get("title"))
                            break
                else:
                    if genres.lower() in GENRES:
                        print(r.get("title"))
    

    # print('Title:')
    # print(response.get("title"))
    # print()

    # print('Collections:')
    # collections = response.get("collection")
    # if isinstance(collections, list):
    #     for collection in collections:
    #         print(collection)
    # else:
    #     print(collections)
    # print()

    # print('Subjects:')
    # subjects = response.get("subject")
    # if isinstance(subjects, list):
    #     for subject in subjects:
    #         print(subject)
    # else:
    #     print(subjects)
    # print()


    # print('Genres:')
    # genres = response.get("genre")
    # if isinstance(genres, list):
    #     for genre in genres:
    #         print(genre)
    # else:
    #     print(genres)