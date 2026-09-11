"""FastAPI entrypoint for the Autonomous AI Game Referee & Spectator Platform.

Run (from arena/):
    .venv/bin/uvicorn --app-dir backend main:app --host 0.0.0.0 --port 8000

The built React dashboard (frontend/dist) is served at / when present; run
`npm run dev` in frontend/ for hot-reload development (proxied to :8000).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import build_api
from arena.engine import GameMaster
from arena.events import EventBus
from arena.store import GameStore

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "arena_data"
DIST_DIR = BASE_DIR.parent / "frontend" / "dist"

bus = EventBus()
store = GameStore(DATA_DIR, bus=bus)
master = GameMaster(store)

app = FastAPI(title="Multi-LLM Arena Engine", version="0.1.0")
app.include_router(build_api(store, master))


@app.on_event("startup")
async def _resume_note() -> None:
    # Replayed games stay in their last status; only "running" games that
    # were interrupted are reset to "paused" for manual resumption.
    for snap in store.list_games():
        if snap.status == "running":
            await store.emit(snap.game_id, "game_paused", {})


if DIST_DIR.exists():
    # Static assets (hashed js/css); SPA index served as fallback below.
    app.mount(
        "/assets",
        StaticFiles(directory=DIST_DIR / "assets"),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        if full_path.startswith(("api/", "ws/")):
            from fastapi import HTTPException
            raise HTTPException(404)
        candidate = DIST_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST_DIR / "index.html")
