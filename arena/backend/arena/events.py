"""In-process pub/sub fan-out for live spectator WebSockets."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from .schemas import Event


class EventBus:
    """One queue per subscriber; slow spectators never block the game loop."""

    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue[Event]]] = defaultdict(set)

    def subscribe(self, game_id: str, maxsize: int = 500) -> asyncio.Queue[Event]:
        q: asyncio.Queue[Event] = asyncio.Queue(maxsize=maxsize)
        self._subs[game_id].add(q)
        return q

    def unsubscribe(self, game_id: str, q: asyncio.Queue[Event]) -> None:
        self._subs[game_id].discard(q)

    async def publish(self, event: Event) -> None:
        for q in tuple(self._subs.get(event.game_id, ())):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # Spectator fell too far behind; drop oldest, keep newest.
                try:
                    q.get_nowait()
                    q.put_nowait(event)
                except Exception:
                    pass

    async def flush(self, game_id: str, payload: dict[str, Any]) -> None:
        """Convenience hook kept for symmetry/testing."""
