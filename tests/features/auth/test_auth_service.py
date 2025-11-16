import asyncio
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import db.models  # noqa: F401  ensure models registered
from app.settings import get_settings
from db.base import Base
from domain.auth.auth import AuthSetupRequest, LoginRequest
from domain.auth.participant import ParticipantCreate
from features.auth.service import AuthService
from features.auth.security import verify_password
from db.models import Admin, AdminParticipantLink


def test_bootstrap_admin_creates_admin_and_participants(monkeypatch, tmp_path: Path):
    asyncio.run(_run_bootstrap_admin(monkeypatch, tmp_path))


async def _run_bootstrap_admin(monkeypatch, tmp_path: Path):
    db_url = f"sqlite+aiosqlite:///{tmp_path/'auth.sqlite'}"

    monkeypatch.setenv("BITHARBOR_DB__URL", db_url)
    monkeypatch.setenv("BITHARBOR_SERVER__DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("BITHARBOR_SERVER__POOL_ROOT", str(tmp_path / "pool"))
    monkeypatch.setenv("BITHARBOR_ANN__INDEX_DIRECTORY", str(tmp_path / "index"))
    monkeypatch.setenv("BITHARBOR_ANN__VECTORS_PATH", str(tmp_path / "vectors.fp32"))

    get_settings.cache_clear()

    engine = create_async_engine(db_url, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    monkeypatch.setattr(
        "features.auth.service.create_access_token",
        lambda *args, **kwargs: "test-token",
    )

    service = AuthService()
    payload = AuthSetupRequest(
        email="admin@example.com",
        password="ChangeMe123!",
        display_name="Main Admin",
        participants=[
            ParticipantCreate(
                handle="owner",
                display_name="Owner",
                email="owner@example.com",
                role="owner",
            )
        ],
    )

    async with Session() as session:
        response = await service.bootstrap_admin(session, payload)

    assert response.admin.email == "admin@example.com"
    assert response.participants[0].handle == "owner"

    async with Session() as session:
        admin_row = await session.scalar(select(Admin))
        assert admin_row is not None
        assert admin_row.email == "admin@example.com"
        assert verify_password(payload.password, admin_row.hashed_password)

        link = await session.scalar(select(AdminParticipantLink))
        assert link is not None
        assert link.role == "owner"

    await engine.dispose()


def test_authenticate_returns_token(monkeypatch, tmp_path: Path):
    asyncio.run(_run_authenticate(monkeypatch, tmp_path))


async def _run_authenticate(monkeypatch, tmp_path: Path):
    db_url = f"sqlite+aiosqlite:///{tmp_path/'auth.sqlite'}"

    monkeypatch.setenv("BITHARBOR_DB__URL", db_url)
    monkeypatch.setenv("BITHARBOR_SERVER__DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("BITHARBOR_SERVER__POOL_ROOT", str(tmp_path / "pool"))
    monkeypatch.setenv("BITHARBOR_ANN__INDEX_DIRECTORY", str(tmp_path / "index"))
    monkeypatch.setenv("BITHARBOR_ANN__VECTORS_PATH", str(tmp_path / "vectors.fp32"))

    get_settings.cache_clear()

    engine = create_async_engine(db_url, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    monkeypatch.setattr(
        "features.auth.service.create_access_token",
        lambda *args, **kwargs: "test-token",
    )

    service = AuthService()

    setup_payload = AuthSetupRequest(
        email="admin@example.com",
        password="ChangeMe123!",
        display_name="Main Admin",
        participants=[],
    )

    async with Session() as session:
        await service.bootstrap_admin(session, setup_payload)

    login_payload = LoginRequest(email="admin@example.com", password="ChangeMe123!")
    async with Session() as session:
        token_response = await service.authenticate(session, login_payload)

    assert token_response.access_token
    assert token_response.admin.email == "admin@example.com"

    await engine.dispose()

