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

BLOCKED_SUBJECTS = [
    "pornography",
    "porn",
    "adult",
    "nazi",
    "klu klux klan",
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
    "Science Fiction",
    "Thriller",
    "War",
    "Western",
]

FORCE_GENRES = True

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
        query = [] + [f'"{self.query}"'] if self.query else []

        if self.title:
            query.append(f'title:"{self.title}"')

        if self.year:
            query.append(f'year:{self.year}')

        if self.safe_search or self.genres or FORCE_GENRES:

            safe_search_insert = ""
            genres = self.genres + GENRES if FORCE_GENRES else self.genres
            genres = list(set([genre.lower() for genre in genres if (genre not in BLOCKED_SUBJECTS and self.safe_search) or (not self.safe_search)]))

            if self.safe_search:
                safe_search_insert = " AND NOT " + '(' + ' OR '.join([f'"{block}"' for block in BLOCKED_SUBJECTS]) + ')'

            subject = f'subject:(' + ' OR '.join([f'"{genre}"' for genre in genres]) + ' ' + safe_search_insert + ')'
            genre = f'genre:(' + ' OR '.join([f'"{genre}"' for genre in genres]) + ' ' + safe_search_insert + ')'
            query.append(f"({subject} OR {genre})")

        if self.creator:
            query.append(f'creator:"{self.creator}"')

        if self.languages:
            query.append('language:(' + ' OR '.join([f'"{language}"' for language in self.languages]) + ')')

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

        print(params['q'])

        response = requests.get(self.url, params=params)

        if response.status_code != 200:
            return None, response.json()

        return response.json(), None


if __name__ == "__main__":

    client = InternetArchiveClient()

    query = MovieSearchQuery()

    count = 0
    page = 1
    total = 300
    rows = 100

    out_dir = Path('output')
    os.system(f'rm -rf {out_dir}')
    os.makedirs(out_dir, exist_ok=True)

    while True:
        result, error = client.search(query=query, rows=rows, page=page)
        if error:
            print(error)
            break
        
        dictionary = result.get("response").get("docs")
        if not dictionary:
            break

        found = len(dictionary)

        with open(f'{out_dir}/page_{page}.txt', 'w') as f:
            f.write(f'{len(dictionary)} items on this page\n\n')
            for item in dictionary:
                f.write(item.get("title") + '\n')
                f.write('\t' "Genre: " + str(item.get("genre")) + '\n')
                f.write('\t' "Subject: " + str(item.get("subject")) + '\n')
                # f.write('\t' "Creator: " + str(item.get("creator")) + '\n')
                # f.write('\t' "Year: " + str(item.get("year")) + '\n')
                # f.write('\t' "Downloads: " + str(item.get("downloads")) + '\n')
                f.write('\n')

        count += found

        if found < rows:
            break
        
        if count >= total:
            break

        page += 1
