"""Reusable Internet Archive catalog client primitives."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
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


class MovieSearchQuery:
    title: Optional[str] = None
    year: Optional[int] = None
    genres: Optional[list[str]] = None
    languages: Optional[list[str]] = None
    sort: Optional[str] = None
    filters: Optional[list[str]] = None



if __name__ == "__main__":
    url = 'https://archive.org/services/search/v1/scrape'

    params = {
        'q': 'title:"Night of the Living Dead"',
        'count': 100,
    }

    def yield_results(params):
        result = requests.get(url, params=params)
        while True:
            if (result.status_code != 200):
                yield (None, result.json())
                break
            else:
                result_obj = result.json()
                print(result_obj.keys)
                yield (result_obj, None)
                cursor = result_obj.get('cursor', None)
                if cursor is None:
                    break
                else:
                    params_copy = params.copy()
                    params_copy['cursor'] = cursor
                    result = requests.get(url, params=params_copy)

    for result, error in yield_results(params):
        print(result)
        print(error)