from __future__ import annotations

from pathlib import Path
import mimetypes

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Movie
from db.session import get_session
from domain.catalog import CatalogDownloadRequest, CatalogDownloadResponse, CatalogMatchResponse
from domain.media.movies import MovieMedia
from domain.search import LocalMovieSearchResponse

from .download import (
    CatalogMatchNotFoundError,
    MovieCatalogDownloadService,
    get_movie_catalog_download_service,
)
from .ingest import ingest_catalog_movie
from .local_search import (
    MovieLocalSearchService,
    get_movie_local_search_service,
)
from .search import (
    MovieCatalogSearchService,
    get_movie_catalog_search_service,
    get_registered_match,
)
from .utils import movie_to_media

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("/catalog/search", response_model=CatalogMatchResponse)
async def search_catalog_movies(
    query: str = Query(..., min_length=1, description="Movie title to search in catalog sources"),
    limit: int = Query(10, ge=1, le=50),
    year: int | None = Query(None, description="Restrict matches to a specific release year"),
    search_service: MovieCatalogSearchService = Depends(get_movie_catalog_search_service),
) -> CatalogMatchResponse:
    """Search TMDb and Internet Archive for catalog matches."""

    try:
        return await search_service.search(query=query, limit=limit, year=year)
    except RuntimeError as exc:  # missing TMDb creds
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/local/search", response_model=LocalMovieSearchResponse)
async def search_local_movies(
    query: str = Query(..., min_length=1, description="Search term for local library"),
    limit: int = Query(10, ge=1, le=50),
    min_score: float | None = Query(
        0.2,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity score required for a hit (0-1).",
    ),
    session: AsyncSession = Depends(get_session),
    search_service: MovieLocalSearchService = Depends(get_movie_local_search_service),
) -> LocalMovieSearchResponse:
    return await search_service.search(session=session, query=query, limit=limit, min_score=min_score)


async def _fetch_all_movies(session: AsyncSession) -> list[MovieMedia]:
    result = await session.scalars(select(Movie))
    movies = result.all()
    return [movie_to_media(movie) for movie in movies]


@router.get("/all", response_model=list[MovieMedia])
async def list_all_movies(session: AsyncSession = Depends(get_session)) -> list[MovieMedia]:
    return await _fetch_all_movies(session)


def _parse_range(range_header: str | None, file_size: int) -> tuple[int, int]:
    if not range_header:
        return 0, file_size - 1

    if "=" not in range_header:
        raise HTTPException(status_code=416, detail="Invalid Range header format")

    unit, byte_range = range_header.strip().split("=", 1)
    if unit != "bytes":
        raise HTTPException(status_code=416, detail="Unsupported range unit")

    first_range = byte_range.split(",")[0].strip()
    if "-" not in first_range:
        raise HTTPException(status_code=416, detail="Invalid Range header format")

    start_str, end_str = first_range.split("-", 1)
    if start_str == "":
        # suffix-byte-range-spec: bytes=-N
        try:
            length = int(end_str)
        except ValueError as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=416, detail="Invalid range values") from exc
        if length <= 0:
            raise HTTPException(status_code=416, detail="Invalid range values")
        start = max(file_size - length, 0)
        end = file_size - 1
    else:
        try:
            start = int(start_str)
        except ValueError as exc:
            raise HTTPException(status_code=416, detail="Invalid range values") from exc
        if end_str:
            try:
                end = int(end_str)
            except ValueError as exc:
                raise HTTPException(status_code=416, detail="Invalid range values") from exc
        else:
            end = file_size - 1

        if start >= file_size:
            raise HTTPException(status_code=416, detail="Range start out of bounds")
        end = min(end, file_size - 1)
        if start > end:
            raise HTTPException(status_code=416, detail="Invalid range values")

    return start, end


def _iter_file(path: Path, start: int, end: int, chunk_size: int = 1024 * 1024):
    with path.open("rb") as file_obj:
        file_obj.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = file_obj.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


@router.get("/stream")
async def stream_movie(
    file_hash: str,
    range_header: str | None = Header(None, alias="Range"),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Movie).where(Movie.file_hash == file_hash)
    movie = await session.scalar(stmt)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    if not movie.path:
        raise HTTPException(status_code=404, detail="Movie file path unknown")

    file_path = Path(movie.path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Movie file not found on disk")

    file_size = file_path.stat().st_size
    if file_size == 0:
        raise HTTPException(status_code=404, detail="Movie file is empty")

    start, end = _parse_range(range_header, file_size)
    headers = {"Accept-Ranges": "bytes"}
    status_code = 206 if range_header else 200
    content_length = end - start + 1
    headers["Content-Length"] = str(content_length)

    if status_code == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"

    media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    return StreamingResponse(
        _iter_file(file_path, start, end),
        media_type=media_type,
        status_code=status_code,
        headers=headers,
    )


@router.post("/catalog/download", response_model=CatalogDownloadResponse)
async def download_catalog_movie(
    payload: CatalogDownloadRequest,
    session: AsyncSession = Depends(get_session),
    download_service: MovieCatalogDownloadService = Depends(get_movie_catalog_download_service),
) -> CatalogDownloadResponse:
    """Plan or execute a catalog-based download using a match key."""

    destination_path = Path(payload.destination).expanduser().resolve() if payload.destination else None

    if not payload.execute:
        try:
            return download_service.plan(payload.match_key, destination=destination_path)
        except CatalogMatchNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        download_result = download_service.download(payload.match_key, destination=destination_path)
    except CatalogMatchNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    match = get_registered_match(payload.match_key)
    if match is None:
        raise HTTPException(status_code=404, detail="Catalog match no longer available")

    if not download_result.video_path:
        raise HTTPException(status_code=500, detail="Download did not produce a video file")

    poster_path: Path | None = None
    if download_result.cover_art_file:
        base_dir = Path(download_result.video_path).parent
        candidate = base_dir / download_result.cover_art_file
        if candidate.exists():
            poster_path = candidate

    tmdb_movie = match.tmdb_movie
    metadata = {
        "title": tmdb_movie.title,
        "overview": tmdb_movie.overview,
        "genres": tmdb_movie.genres,
        "languages": tmdb_movie.languages,
        "year": tmdb_movie.year,
        "poster_path": str(poster_path) if poster_path else None,
        "poster": tmdb_movie.poster.model_dump() if tmdb_movie.poster else None,
        "backdrop": tmdb_movie.backdrop.model_dump() if tmdb_movie.backdrop else None,
        "runtime_min": tmdb_movie.runtime_min,
        "release_date": tmdb_movie.release_date,
        "vote_average": tmdb_movie.vote_average,
        "vote_count": tmdb_movie.vote_count,
        "cast": tmdb_movie.cast,
        "rating": tmdb_movie.rating,
        "catalog_source": tmdb_movie.catalog_source or "tmdb",
        "catalog_id": tmdb_movie.catalog_id,
        "tmdb_id": match.tmdb_id,
        "ia_identifier": match.best_candidate.identifier,
        "ia_downloads": match.best_candidate.downloads,
        "ia_score": match.best_candidate.score,
    }

    try:
        ingest_result = await ingest_catalog_movie(
            session=session,
            video_path=Path(download_result.video_path),
            metadata=metadata,
        )
        await session.commit()
    except Exception as exc:  # noqa: BLE001
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    download_result.file_hash = ingest_result.file_hash
    download_result.vector_hash = ingest_result.vector_hash
    download_result.vector_row_id = ingest_result.vector_row_id
    download_result.movie_id = ingest_result.movie_id
    download_result.created = ingest_result.created
    return download_result
