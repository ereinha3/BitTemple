from __future__ import annotations

from fastapi import APIRouter

from features.auth.router import router as auth_router
from features.participants.router import router as participants_router
from features.movies.router import router as movies_router
from features.music.router import router as music_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(participants_router)
api_router.include_router(movies_router)
api_router.include_router(music_router)
