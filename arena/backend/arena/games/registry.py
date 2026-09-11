"""Catalog of installed game plugins."""
from __future__ import annotations

from .base import GamePlugin
from .beauty_contest import BeautyContestPlugin

GAMES: dict[str, GamePlugin] = {
    BeautyContestPlugin.id: BeautyContestPlugin(),
}


def get_game(game_type: str) -> GamePlugin:
    if game_type not in GAMES:
        raise KeyError(f"unknown game type {game_type!r}; installed: {list(GAMES)}")
    return GAMES[game_type]
