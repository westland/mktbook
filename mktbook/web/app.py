"""FastAPI application factory."""
from __future__ import annotations

import pathlib

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from mktbook.web.websocket import WSManager

_WEB_DIR = pathlib.Path(__file__).parent
TEMPLATES = Jinja2Templates(directory=str(_WEB_DIR / "templates"))


def create_app(ws: WSManager) -> FastAPI:
    app = FastAPI(title="MktBook Bot Marketplace")

    app.mount("/static", StaticFiles(directory=str(_WEB_DIR / "static")), name="static")

    # Store shared objects on app state
    app.state.ws = ws
    app.state.fleet = None       # set by main.py
    app.state.scheduler = None   # set by main.py
    app.state.openai = None      # set by main.py

    # Register routes
    from mktbook.web.routes_api import router as api_router
    from mktbook.web.routes_pages import router as pages_router

    app.include_router(api_router)
    app.include_router(pages_router)

    # WebSocket endpoint
    from fastapi import WebSocket as WS, WebSocketDisconnect

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WS) -> None:
        await ws.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            ws.disconnect(websocket)

    return app
