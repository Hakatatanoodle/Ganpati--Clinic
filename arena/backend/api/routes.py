"""HTTP + WebSocket surface for the spectator dashboard."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from config import PROVIDERS, VAULT
from arena.engine import GameMaster
from arena.games.registry import GAMES, get_game
from arena.gateway.registry import REGISTRY
from arena.schemas import GameConfig, PlayerConfig
from arena.store import GameStore

router = APIRouter(prefix="/api")


def build_api(store: GameStore, master: GameMaster) -> APIRouter:

    # -----------------------------------------------------------------
    # Catalog
    # -----------------------------------------------------------------
    @router.get("/health")
    async def health() -> dict:
        return {"ok": True, "games": list(GAMES)}

    @router.get("/providers")
    async def providers() -> dict[str, Any]:
        out = {}
        for pid, prof in PROVIDERS.items():
            out[pid] = {
                "id": pid, "label": prof.label, "kind": prof.kind,
                "default_model": prof.default_model, "models": list(prof.models),
                "docs": prof.docs,
            }
        return {"providers": out, "status": VAULT.status(),
                "personas": REGISTRY.persona_catalog()}

    @router.get("/games-catalog")
    async def games_catalog() -> dict:
        return {"games": [
            {"id": g.id, "title": g.title, "description": g.description}
            for g in GAMES.values()
        ]}

    class KeyIn(BaseModel):
        provider: str
        key: str

    @router.post("/keys")
    async def set_key(body: KeyIn) -> dict:
        try:
            VAULT.set_key(body.provider, body.key)
        except KeyError as exc:
            raise HTTPException(404, str(exc))
        return {"status": VAULT.status()}

    # -----------------------------------------------------------------
    # Games
    # -----------------------------------------------------------------
    @router.post("/games")
    async def create_game(config: GameConfig) -> dict:
        if config.game_type not in GAMES:
            raise HTTPException(400, f"unknown game {config.game_type}")
        if len(config.players) < 2:
            raise HTTPException(400, "at least 2 players are required")
        names = [p.name for p in config.players]
        if len(set(names)) != len(names):
            raise HTTPException(400, "player names must be unique")
        for p in config.players:
            if p.provider not in PROVIDERS:
                raise HTTPException(400, f"unknown provider {p.provider}")
            if p.provider != "mock" and not VAULT.get_key(p.provider):
                raise HTTPException(
                    400,
                    f"player {p.name}: no API key for "
                    f"{PROVIDERS[p.provider].label} — add it in Settings")
        game_id = uuid.uuid4().hex[:10]
        store.create(game_id, config)
        await store.emit(game_id, "game_created", {
            "config": config.model_dump(),
            "players": {pc.id: {"config": pc.model_dump()} for pc in config.players},
        })
        return {"game_id": game_id, "snapshot": store.get(game_id).model_dump()}

    @router.get("/games")
    async def list_games() -> dict:
        return {"games": [
            {"game_id": s.game_id, "status": s.status,
             "game_type": s.config.game_type,
             "players": [p.config.name for p in s.players.values()],
             "round": s.current_round, "winner_id": s.winner_id}
            for s in store.list_games()
        ]}

    @router.get("/games/{game_id}")
    async def get_game(game_id: str) -> dict:
        try:
            return store.get(game_id).model_dump()
        except KeyError:
            raise HTTPException(404, "unknown game")

    @router.get("/games/{game_id}/events")
    async def get_events(game_id: str, after: int = -1) -> dict:
        try:
            return {"events": [e.model_dump() for e in store.events(game_id, after)]}
        except KeyError:
            raise HTTPException(404, "unknown game")

    class SpeedIn(BaseModel):
        delay: float

    @router.post("/games/{game_id}/{command}")
    async def command(game_id: str, command: str, body: SpeedIn | None = None) -> dict:
        try:
            store.get(game_id)
        except KeyError:
            raise HTTPException(404, "unknown game")
        if command == "start":
            await master.start(game_id)
        elif command == "pause":
            await master.pause(game_id)
        elif command == "resume":
            await master.resume(game_id)
        elif command == "step":
            await master.step(game_id)
        elif command == "speed":
            master.set_speed(game_id, body.delay if body else 2.5)
        else:
            raise HTTPException(400, f"unknown command {command}")
        return store.get(game_id).model_dump()

    # -----------------------------------------------------------------
    # Live stream
    # -----------------------------------------------------------------
    @router.websocket("/ws/games/{game_id}")
    async def ws_game(websocket: WebSocket, game_id: str) -> None:
        try:
            store.get(game_id)
        except KeyError:
            await websocket.close(code=4404)
            return
        await websocket.accept()
        q = store.bus.subscribe(game_id)
        try:
            # Replay everything the subscriber missed, then stream live.
            await websocket.send_json({"type": "snapshot",
                                       "snapshot": store.get(game_id).model_dump()})
            for e in store.events(game_id):
                await websocket.send_json({"type": "event", "event": e.model_dump()})
            while True:
                event = await q.get()
                await websocket.send_json({"type": "event", "event": event.model_dump()})
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            store.bus.unsubscribe(game_id, q)

    return router
