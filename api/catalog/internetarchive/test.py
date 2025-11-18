"""Reusable Internet Archive catalog client primitives."""

from __future__ import annotations

import logging
import os
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Generic, Iterable, Mapping, Sequence, TypeVar

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

    def to_ia(self) -> str:
        query = []
        if self.title:
            query.append(f'title:"{self.title}"')
        if self.year:
            query.append(f'year:{self.year}')
        if self.genres:
            if len(self.genres) > 1:
                query.append(f'subject:({" OR ".join([f"({genre})" for genre in self.genres])})')
            else:
                query.append(f'subject:"{self.genres[0]}"')
        if self.creator:
            query.append(f'creator:"{self.creator}"')
        if self.languages:
            if len(self.languages) > 1:
                query.append(f'language:({" OR ".join([f"({language})" for language in self.languages])})')
            else:
                query.append(f'language:"{self.languages[0]}"')
        return " AND ".join(query)


class InternetArchiveClient:
    """Thin wrapper around ``internetarchive`` providing reusable primitives."""

    def __init__(self, session: ArchiveSession | None = None) -> None:
        if session is not None:
            self._session = session
        elif CONFIG_FILE.exists():
            self._session = ia.get_session(config_file=str(CONFIG_FILE))
        self.url = 'https://archive.org/services/search/v1/scrape'
        self.max_count = 10_000
        self.base_query = "mediatype:movies"

    def search(
        self,
        query: MovieSearchQuery,
        limit: int = 200,
        safe_search: bool = True,
    ) -> list[MediaT]:

        params = {
            'q': f'{self.base_query} AND {query.to_ia()}',
            'count': min(limit, self.max_count),
            'fields': ",".join(FIELDS),
            'sorts': "downloads desc",
        }

        # print(params)

        for result, error in self.yield_results(params):
            if error:
                yield (None, error)
                break
            else:
                yield (result, None)

    def yield_results(self, params):
        result = requests.get(self.url, params=params)
        while True:
            if (result.status_code != 200):
                yield (None, result.json())
                break
            else:
                result_obj = result.json()
                yield (result_obj, None)
                cursor = result_obj.get('cursor', None)
                if cursor is None:
                    break
                else:
                    params_copy = params.copy()
                    params_copy['cursor'] = cursor
                    result = requests.get(self.url, params=params_copy)

if __name__ == "__main__":

    client = InternetArchiveClient()

    query = MovieSearchQuery(title="Night of the Living Dead")

    count = 0
    first = None
    for result, error in client.search(query):
        dictionary = result['items']
        first = dictionary[0]
        count += len(dictionary)
        # for item in dictionary:
        #     print(item.get("title"))
        #     print('\t', item.get("description"))
        #     print('\t', item.get("downloads"))
        #     print('\t', item.get("language"))
        #     print('\t', item.get("creator"))
        #     print('\t', item.get("year"))
        #     print()

    print('Found', count, 'items')
    print()
    print('First item:', first.get("title"))
    print('First item description:', first.get("description"))
    print('First item downloads:', first.get("downloads"))
    print('First item language:', first.get("language"))
    print('First item creator:', first.get("creator"))
    print('First item year:', first.get("year"))
    print()
