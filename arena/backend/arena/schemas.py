"""Pydantic schemas: configuration, events, and derived game state snapshots."""
from __future__ import annotations

import time
import uuid
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class PlayerConfig(BaseModel):
    """One contestant in the arena.

    provider="mock" selects a built-in simulated persona; every other value
    routes through the unified model gateway to a live LLM API.
    """

    id: str = ""
    name: str
    provider: str = "mock"
    model: str = ""          # model id, or mock persona id (e.g. "grok-sim")
    persona: str = ""        # human-readable persona label
    temperature: float = 0.8

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if not self.id:
            self.id = f"p_{uuid.uuid4().hex[:8]}"
        if not self.model:
            self.model = self.persona or self.name


class DynamicRules(BaseModel):
    """Toggles for the rule injections that make games evolve mid-flight."""

    duplicate_penalty: bool = True       # identical guesses cost +10
    exact_match_bonus: bool = True       # hitting the target exactly pays -15
    sudden_death_paradox: bool = True    # post-elimination {0,100} round


class GameConfig(BaseModel):
    game_type: str = "beauty_contest"
    mode: Literal["elimination", "fixed"] = "elimination"
    rounds: int = Field(default=5, ge=1, le=30)          # used by fixed mode / safety cap
    factor: float = Field(default=0.8, ge=0.0, le=2.0)
    guess_min: int = 0
    guess_max: int = 100
    eliminate_every: int = Field(default=2, ge=1, le=6)  # elimination mode
    round_delay: float = Field(default=2.5, ge=0.0, le=30.0)
    dynamic_rules: DynamicRules = Field(default_factory=DynamicRules)
    players: list[PlayerConfig] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Event log (append-only — the single source of truth)
# ---------------------------------------------------------------------------


class Event(BaseModel):
    seq: int
    game_id: str
    type: str
    ts: float = Field(default_factory=lambda: time.time())
    payload: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Derived state
# ---------------------------------------------------------------------------


class PlayerState(BaseModel):
    config: PlayerConfig
    status: Literal["alive", "eliminated"] = "alive"
    score: float = 0.0           # cumulative penalty — LOWER is better
    eliminated_round: Optional[int] = None
    last_action: Any = None
    last_reasoning: str = ""
    last_latency_ms: Optional[int] = None
    last_error: Optional[str] = None
    thinking: bool = False
    reasoning_log: list[dict[str, Any]] = Field(default_factory=list)


class RoundRecord(BaseModel):
    round: int
    special: Optional[str] = None          # e.g. "sudden_death_binary"
    target: Optional[float] = None
    actions: dict[str, Any] = Field(default_factory=dict)   # pid -> action
    deltas: dict[str, dict[str, Any]] = Field(default_factory=dict)
    active_rules: list[str] = Field(default_factory=list)
    resolved: bool = False


class GameSnapshot(BaseModel):
    game_id: str
    status: Literal["setup", "running", "paused", "finished"] = "setup"
    config: GameConfig
    players: dict[str, PlayerState] = Field(default_factory=dict)
    rounds: list[RoundRecord] = Field(default_factory=list)
    active_rules: list[dict[str, Any]] = Field(default_factory=list)
    announcements: list[dict[str, Any]] = Field(default_factory=list)
    current_round: int = 0
    winner_id: Optional[str] = None
    end_reason: Optional[str] = None
    plugin_state: dict[str, Any] = Field(default_factory=dict)
    event_count: int = 0

    def alive_players(self) -> list[PlayerState]:
        return [p for p in self.players.values() if p.status == "alive"]

    def standings(self) -> list[PlayerState]:
        """Alive first by score ascending, then eliminated (most recent last)."""
        alive = sorted(
            (p for p in self.players.values() if p.status == "alive"),
            key=lambda p: (p.score, p.config.name),
        )
        dead = sorted(
            (p for p in self.players.values() if p.status != "alive"),
            key=lambda p: -(p.eliminated_round or 0),
        )
        return alive + dead
