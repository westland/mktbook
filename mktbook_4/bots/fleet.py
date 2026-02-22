"""Manages the fleet of Discord bot clients for mktbook_4."""
from __future__ import annotations

import asyncio
import logging

from openai import AsyncOpenAI

from mktbook_4.bots.bot_client import SingleBot
from mktbook.db import queries
from mktbook.db.models import Bot

log = logging.getLogger(__name__)


class BotFleet:
    """Manages all active Discord bot instances (mktbook_4)."""

    def __init__(self, openai_client: AsyncOpenAI) -> None:
        self.openai = openai_client
        self._bots: dict[int, SingleBot] = {}
        self._tasks: dict[int, asyncio.Task[None]] = {}

    @property
    def active_bots(self) -> dict[int, SingleBot]:
        return dict(self._bots)

    def get_bot(self, bot_id: int) -> SingleBot | None:
        return self._bots.get(bot_id)

    async def start_bot(self, bot_row: Bot) -> None:
        if bot_row.id in self._bots:
            log.warning("Bot %s already running", bot_row.bot_name)
            return
        client = SingleBot(bot_row, self.openai)
        self._bots[bot_row.id] = client

        async def _run() -> None:
            try:
                await client.start(bot_row.discord_token)
            except Exception:
                log.exception("Bot %s crashed", bot_row.bot_name)
            finally:
                self._bots.pop(bot_row.id, None)
                self._tasks.pop(bot_row.id, None)

        self._tasks[bot_row.id] = asyncio.create_task(_run())
        log.info("Launched mktbook_4 bot %s (id=%d)", bot_row.bot_name, bot_row.id)

    async def stop_bot(self, bot_id: int) -> None:
        client = self._bots.pop(bot_id, None)
        task = self._tasks.pop(bot_id, None)
        if client:
            await client.close()
            log.info("Stopped bot id=%d", bot_id)
        if task and not task.done():
            task.cancel()

    async def start_all(self) -> None:
        bots = await queries.get_active_bots(workout_id=4)
        for bot in bots:
            await self.start_bot(bot)

    async def stop_all(self) -> None:
        for bid in list(self._bots.keys()):
            await self.stop_bot(bid)

    async def reload_bot(self, bot_id: int) -> None:
        await self.stop_bot(bot_id)
        bot_row = await queries.get_bot(bot_id)
        if bot_row and bot_row.is_active:
            await self.start_bot(bot_row)

    async def poll_new_bots(self, interval: int = 30) -> None:
        while True:
            await asyncio.sleep(interval)
            try:
                bots = await queries.get_active_bots(workout_id=4)
                for bot in bots:
                    if bot.id not in self._bots:
                        log.info("New bot detected: %s — starting", bot.bot_name)
                        await self.start_bot(bot)
            except Exception:
                log.exception("Error polling for new bots")
