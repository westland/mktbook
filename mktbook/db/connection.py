from __future__ import annotations

import pathlib

import aiosqlite

from mktbook.config import settings

_db: aiosqlite.Connection | None = None
_SCHEMA = (pathlib.Path(__file__).parent / "schema.sql").read_text()


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        _db = await aiosqlite.connect(settings.database_path)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
        await _db.executescript(_SCHEMA)
        await _db.commit()
        # Migrate existing databases: add workout_id column if missing
        try:
            await _db.execute("ALTER TABLE bots ADD COLUMN workout_id INTEGER NOT NULL DEFAULT 1")
            await _db.commit()
        except Exception:
            pass  # Column already exists
    return _db


async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None
