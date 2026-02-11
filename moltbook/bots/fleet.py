"""Manages the fleet of Discord bot clients."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from openai import AsyncOpenAI

from moltbook.bots.bot_client import SingleBot
from moltbook.db import queries
from moltbook.db.models import Bot

if TYPE_CHECKING:
    from moltbook.web.websocket import WSManager

log = logging.getLogger(__name__)


class BotFleet:
    """Manages all active Discord bot instances."""

    def __init__(self, openai_client: AsyncOpenAI, ws: WSManager | None = None) -> None:
        self.openai = openai_client
        self.ws = ws
        self._bots: dict[int, SingleBot] = {}  # bot_id -> SingleBot
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

        client = SingleBot(bot_row, self.openai, self.ws)
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
        log.info("Launched bot %s (id=%d)", bot_row.bot_name, bot_row.id)

    async def stop_bot(self, bot_id: int) -> None:
        client = self._bots.pop(bot_id, None)
        task = self._tasks.pop(bot_id, None)
        if client:
            await client.close()
            log.info("Stopped bot id=%d", bot_id)
        if task and not task.done():
            task.cancel()

    async def start_all(self) -> None:
        bots = await queries.get_active_bots()
        for bot in bots:
            await self.start_bot(bot)

    async def stop_all(self) -> None:
        bot_ids = list(self._bots.keys())
        for bid in bot_ids:
            await self.stop_bot(bid)

    async def reload_bot(self, bot_id: int) -> None:
        """Stop and restart a bot with fresh config from DB."""
        await self.stop_bot(bot_id)
        bot_row = await queries.get_bot(bot_id)
        if bot_row and bot_row.is_active:
            await self.start_bot(bot_row)
