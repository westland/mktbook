from __future__ import annotations

import logging
import pathlib

import aiosqlite

from mktbook.config import settings

log = logging.getLogger(__name__)

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

        # Migrate: change global UNIQUE on bot_name to per-workout UNIQUE(bot_name, workout_id)
        # Also ensures discord_token has a DEFAULT '' and removes any orphan bots_new table.
        # Uses individual execute() calls instead of executescript() so PRAGMA foreign_keys
        # is properly respected and errors are not swallowed silently.
        try:
            cur = await _db.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='bots'"
            )
            row = await cur.fetchone()
            if row and "unique(bot_name, workout_id)" not in row["sql"].lower():
                await _db.execute("PRAGMA foreign_keys=OFF")
                await _db.execute("DROP TABLE IF EXISTS bots_new")
                await _db.execute("""
                    CREATE TABLE bots_new (
                        id              INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_name    TEXT    NOT NULL,
                        bot_name        TEXT    NOT NULL,
                        discord_token   TEXT    NOT NULL DEFAULT '',
                        personality     TEXT    NOT NULL DEFAULT '',
                        objective       TEXT    NOT NULL DEFAULT '',
                        behavior_rules  TEXT    NOT NULL DEFAULT '',
                        is_active       INTEGER NOT NULL DEFAULT 1,
                        workout_id      INTEGER NOT NULL DEFAULT 1,
                        created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
                        UNIQUE(bot_name, workout_id)
                    )
                """)
                await _db.execute("""
                    INSERT OR IGNORE INTO bots_new
                        SELECT id, student_name, bot_name,
                               COALESCE(discord_token, '') as discord_token,
                               personality, objective, behavior_rules,
                               is_active, workout_id, created_at
                        FROM bots
                """)
                await _db.execute("DROP TABLE bots")
                await _db.execute("ALTER TABLE bots_new RENAME TO bots")
                await _db.commit()
                await _db.execute("PRAGMA foreign_keys=ON")
                log.info("Migrated bots table: unique constraint is now per-workout (bot_name, workout_id)")
        except Exception as exc:
            log.warning("bots unique-constraint migration skipped: %s", exc)
            await _db.execute("PRAGMA foreign_keys=ON")
    return _db


async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None
