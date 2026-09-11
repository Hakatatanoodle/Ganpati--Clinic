"""Bulletproof, event-sourced game store.

Every state mutation is an append-only Event. Events are mirrored to
``arena_data/games/<id>.jsonl`` so a crashed referee can be replayed to the
exact state. The reducer below is the *only* place state changes are applied.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from .events import EventBus
from .schemas import Event, GameConfig, GameSnapshot, PlayerState, RoundRecord


class GameStore:
    def __init__(self, data_dir: str | Path, bus: Optional[EventBus] = None) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "games").mkdir(exist_ok=True)
        self.bus = bus or EventBus()
        self._events: dict[str, list[Event]] = {}
        self._snapshots: dict[str, GameSnapshot] = {}
        self._replay_all()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _path(self, game_id: str) -> Path:
        return self.data_dir / "games" / f"{game_id}.jsonl"

    def _replay_all(self) -> None:
        for f in sorted((self.data_dir / "games").glob("*.jsonl")):
            game_id = f.stem
            for line in f.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                event = Event(**json.loads(line))
                self._events.setdefault(game_id, []).append(event)
            if game_id in self._events:
                self._snapshots[game_id] = self.reduce(game_id)

    def _append(self, event: Event) -> None:
        self._events.setdefault(event.game_id, []).append(event)
        with self._path(event.game_id).open("a") as fh:
            fh.write(event.model_dump_json() + "\n")
        self._snapshots[event.game_id] = self.reduce(event.game_id)

    async def emit(self, game_id: str, type_: str, payload: dict) -> Event:
        seq = len(self._events.get(game_id, []))
        event = Event(seq=seq, game_id=game_id, type=type_, payload=payload)
        self._append(event)
        await self.bus.publish(event)
        return event

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------
    def get(self, game_id: str) -> GameSnapshot:
        if game_id not in self._snapshots:
            raise KeyError(game_id)
        return self._snapshots[game_id]

    def list_games(self) -> list[GameSnapshot]:
        return sorted(self._snapshots.values(), key=lambda s: s.game_id)

    def events(self, game_id: str, after: int = -1) -> list[Event]:
        return [e for e in self._events.get(game_id, []) if e.seq > after]

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------
    def create(self, game_id: str, config: GameConfig) -> GameSnapshot:
        self._events[game_id] = []
        self._path(game_id).touch()
        snap = GameSnapshot(game_id=game_id, config=config, status="setup")
        for pc in config.players:
            snap.players[pc.id] = PlayerState(config=pc)
        self._snapshots[game_id] = snap
        return snap

    # ------------------------------------------------------------------
    # Reducer — pure function of the event log
    # ------------------------------------------------------------------
    def reduce(self, game_id: str) -> GameSnapshot:
        events = self._events.get(game_id, [])
        if not events:
            raise KeyError(game_id)

        created = events[0]
        if created.type != "game_created":
            raise ValueError(f"corrupt log for {game_id}: first event {created.type}")
        snap = GameSnapshot(
            game_id=game_id,
            config=GameConfig(**created.payload["config"]),
            status="setup",
        )
        for pid, pdata in created.payload["players"].items():
            snap.players[pid] = PlayerState.model_validate(pdata)

        for e in events[1:]:
            p = e.payload
            t = e.type

            if t == "game_started":
                snap.status = "running"
                if p.get("plugin_state") is not None:
                    snap.plugin_state = p["plugin_state"]

            elif t == "game_paused":
                if snap.status == "running":
                    snap.status = "paused"

            elif t == "game_resumed":
                if snap.status == "paused":
                    snap.status = "running"

            elif t == "round_started":
                snap.current_round = p["round"]
                record = RoundRecord(
                    round=p["round"],
                    special=p.get("special"),
                    active_rules=p.get("active_rules", []),
                )
                snap.rounds.append(record)
                if p.get("plugin_state") is not None:
                    snap.plugin_state = p["plugin_state"]

            elif t == "rule_injected":
                snap.active_rules = [r for r in snap.active_rules if r["id"] != p["rule"]["id"]]
                snap.active_rules.append(p["rule"])
                snap.announcements.append(
                    {"round": p.get("round"), "kind": "rule", **p["rule"]}
                )

            elif t == "rule_retracted":
                snap.active_rules = [r for r in snap.active_rules
                                     if r["id"] != p["rule_id"]]

            elif t == "player_thinking":
                ps = snap.players[p["player_id"]]
                ps.last_error = None
                ps.thinking = True

            elif t == "player_acted":
                ps = snap.players[p["player_id"]]
                ps.last_action = p["action"]
                ps.last_reasoning = p.get("reasoning", "")
                ps.last_latency_ms = p.get("latency_ms")
                ps.last_error = p.get("error")
                ps.thinking = False
                ps.reasoning_log.append({
                    "round": snap.current_round,
                    "action": p["action"],
                    "reasoning": p.get("reasoning", ""),
                    "error": p.get("error"),
                    "fallback": p.get("fallback", False),
                    "provider": p.get("provider"),
                    "model": p.get("model"),
                    "latency_ms": p.get("latency_ms"),
                })
                if snap.rounds:
                    snap.rounds[-1].actions[p["player_id"]] = p["action"]

            elif t == "round_resolved":
                rec = snap.rounds[-1]
                rec.resolved = True
                rec.target = p["target"]
                rec.special = p.get("special", rec.special)
                rec.deltas = p["deltas"]
                for pid, delta in p["deltas"].items():
                    snap.players[pid].score = round(
                        snap.players[pid].score + delta["delta"], 4
                    )
                if p.get("plugin_state") is not None:
                    snap.plugin_state = p["plugin_state"]

            elif t == "player_eliminated":
                ps = snap.players[p["player_id"]]
                ps.status = "eliminated"
                ps.eliminated_round = p["round"]
                snap.announcements.append({"round": p["round"], "kind": "elimination", **p})

            elif t == "game_ended":
                snap.status = "finished"
                snap.winner_id = p.get("winner_id")
                snap.end_reason = p.get("reason")
                if p.get("plugin_state") is not None:
                    snap.plugin_state = p["plugin_state"]

            elif t == "notice":
                snap.announcements.append({"round": snap.current_round, "kind": "notice", **p})

        snap.event_count = len(events)
        return snap
