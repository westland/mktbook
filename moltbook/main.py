"""MoltBook Bot Marketplace — entry point.

Runs three concurrent subsystems on one asyncio event loop:
1. FastAPI web server (Uvicorn)
2. Discord bot fleet
3. Autonomous conversation scheduler
"""
from __future__ import annotations

import asyncio
import logging
import signal
import sys

import uvicorn
from openai import AsyncOpenAI

from moltbook.bots.fleet import BotFleet
from moltbook.config import settings
from moltbook.db.connection import close_db, get_db
from moltbook.scheduler.loop import ConversationScheduler
from moltbook.web.app import create_app
from moltbook.web.websocket import WSManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
log = logging.getLogger("moltbook")


async def main() -> None:
    # Shared resources
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    ws = WSManager()

    # Initialize database
    await get_db()
    log.info("Database initialized at %s", settings.database_path)

    # Create subsystems
    fleet = BotFleet(openai_client, ws)
    scheduler = ConversationScheduler(fleet, ws)
    app = create_app(ws)
    app.state.fleet = fleet
    app.state.scheduler = scheduler
    app.state.openai = openai_client

    # Uvicorn server config
    config = uvicorn.Config(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info",
        loop="asyncio",
    )
    server = uvicorn.Server(config)

    # Graceful shutdown
    shutdown_event = asyncio.Event()

    def _signal_handler() -> None:
        log.info("Shutdown signal received")
        shutdown_event.set()
        scheduler.stop()

    loop = asyncio.get_running_loop()
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _signal_handler)

    async def run_server() -> None:
        await server.serve()

    async def run_fleet() -> None:
        await fleet.start_all()
        log.info("Bot fleet started (%d bots)", len(fleet.active_bots))
        await shutdown_event.wait()
        await fleet.stop_all()
        log.info("Bot fleet stopped")

    async def run_scheduler() -> None:
        # Brief delay to let fleet connect first
        await asyncio.sleep(5)
        await scheduler.run()

    try:
        await asyncio.gather(
            run_server(),
            run_fleet(),
            run_scheduler(),
        )
    except asyncio.CancelledError:
        pass
    finally:
        await close_db()
        log.info("MoltBook shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
