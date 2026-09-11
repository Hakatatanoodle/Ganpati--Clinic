"""Game plugin contract.

A game is a pure-logic plugin: given the snapshot + this round's validated
actions it returns scores, rule injections, eliminations and (eventually) a
winner. The GameMaster owns the loop, LLM calls, events and prompts; the
plugin owns *only* rules. Add a new game by dropping one file in this package
and registering it in ``games/registry.py``.
"""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..schemas import GameConfig, GameSnapshot


class InvalidAction(ValueError):
    """Raised when a player's action cannot be coerced into a legal move."""


def default_action(action_spec: dict[str, Any], player_id: str, round_no: int) -> Any:
    """Deterministic referee-assigned move for dead/invalid responses."""
    if action_spec.get("kind") == "choice":
        options = action_spec["options"]
        h = int(hashlib.sha256(f"{player_id}|{round_no}".encode()).hexdigest(), 16)
        return options[h % len(options)]
    return int(action_spec.get("max", 100))


@dataclass
class RoundPlan:
    special: str | None = None
    action_spec: dict[str, Any] = field(default_factory=dict)
    action_hint: str = ""
    inject: list[dict[str, Any]] = field(default_factory=list)
    retract: list[str] = field(default_factory=list)


@dataclass
class ActionRecord:
    action: Any
    valid: bool = True
    error: str | None = None


@dataclass
class RoundOutcome:
    target: float | None
    deltas: dict[str, dict[str, Any]]
    special: str | None = None
    inject: list[dict[str, Any]] = field(default_factory=list)
    retract: list[str] = field(default_factory=list)
    eliminations: list[dict[str, Any]] = field(default_factory=list)
    notices: list[dict[str, Any]] = field(default_factory=list)
    winner_id: str | None = None
    end_reason: str | None = None


class GamePlugin(ABC):
    id: str = "base"
    title: str = "Base game"
    description: str = ""

    @abstractmethod
    def initial_state(self, config: GameConfig) -> dict[str, Any]: ...

    @abstractmethod
    def intro_rules(self, config: GameConfig) -> list[dict[str, Any]]:
        """Rules announced before round 1."""

    @abstractmethod
    def plan_round(self, state: dict[str, Any], snapshot: GameSnapshot,
                   round_no: int) -> RoundPlan: ...

    @abstractmethod
    def coerce_action(self, raw: Any, plan: RoundPlan,
                      config: GameConfig) -> Any: ...

    @abstractmethod
    def resolve_round(self, state: dict[str, Any], snapshot: GameSnapshot,
                      round_no: int, actions: dict[str, ActionRecord]) -> RoundOutcome: ...

    @abstractmethod
    def build_prompts(self, view: dict[str, Any], plan: RoundPlan) -> tuple[str, str]:
        """Return (system_prompt, user_prompt) for a live LLM player."""
