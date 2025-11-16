from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from sqlalchemy import inspect, text

from db.base import Base
from db.session import engine
import db.models  # noqa: F401


async def init_db(custom_engine: AsyncEngine | None = None) -> None:
    target_engine = custom_engine or engine
    async with target_engine.begin() as conn:
        def ensure_columns(connection):
            inspector = inspect(connection)
            columns = {col["name"] for col in inspector.get_columns("admin_participant_links")}
            if "role" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE admin_participant_links "
                        "ADD COLUMN role TEXT DEFAULT 'viewer' NOT NULL"
                    )
                )

        tables = await conn.run_sync(lambda connection: inspect(connection).get_table_names())
        if "admin_participant_links" in tables:
            await conn.run_sync(ensure_columns)
        await conn.run_sync(Base.metadata.create_all)

