from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from domain.catalog import CatalogDownloadRequest, CatalogDownloadResponse

from .download import (
    CatalogMatchNotFoundError,
    TvCatalogDownloadService,
    get_tv_catalog_download_service,
)
from .ingest import ingest_catalog_tv
from .local_search import (
    LocalTvSearchResponse,
    TvLocalSearchService,
    get_tv_local_search_service,
)
from .search import (
    TvCatalogMatchResponse,
    TvCatalogSearchService,
    get_registered_match,
    get_tv_catalog_search_service,
)

router = APIRouter(prefix="/tv", tags=["tv"])


@router.get("/catalog/search", response_model=TvCatalogMatchResponse)
async def search_catalog_tv(
    query: str = Query(..., min_length=1, description="Series title to search in catalog sources"),
    limit: int = Query(10, ge=1, le=50),
    year: int | None = Query(None, description="Restrict matches to a specific first-air year"),
    search_service: TvCatalogSearchService = Depends(get_tv_catalog_search_service),
) -> TvCatalogMatchResponse:
    try:
        return await search_service.search(query=query, limit=limit, year=year)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/search/local", response_model=LocalTvSearchResponse)
async def search_local_tv(
    query: str = Query(..., min_length=1, description="Search term for local TV library"),
    limit: int = Query(10, ge=1, le=50),
    min_score: float | None = Query(
        0.2,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity score required for a hit (0-1).",
    ),
    session: AsyncSession = Depends(get_session),
    search_service: TvLocalSearchService = Depends(get_tv_local_search_service),
) -> LocalTvSearchResponse:
    return await search_service.search(session=session, query=query, limit=limit, min_score=min_score)


@router.post("/catalog/download", response_model=CatalogDownloadResponse)
async def download_catalog_tv(
    payload: CatalogDownloadRequest,
    session: AsyncSession = Depends(get_session),
    download_service: TvCatalogDownloadService = Depends(get_tv_catalog_download_service),
) -> CatalogDownloadResponse:
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

    metadata = download_service.build_metadata(match, match.best_candidate, download_result)

    try:
        ingest_result = await ingest_catalog_tv(
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
    download_result.movie_id = ingest_result.episode_id
    download_result.created = ingest_result.created
    return download_result
