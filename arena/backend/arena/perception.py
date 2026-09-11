"""Information isolation — builds one player's permitted perception.

GUARANTEE: the returned view contains only
  1. public game configuration and active public rules;
  2. the public scoreboard and public per-round action history;
  3. public arena announcements (rule injections, eliminations);
  4. the requesting player's OWN private state and reasoning history.

No other player's reasoning, prompts, raw outputs, provider settings or
private state is ever present. The same view object is rendered into text for
live LLMs and used directly by simulated personas, so every player — human or
machine — is provably playing from the same information boundary.
"""
from __future__ import annotations

from typing import Any

from .schemas import GameSnapshot, PlayerConfig, PlayerState

SPECIAL_LABELS = {
    "sudden_death_binary": "SUDDEN-DEATH 0 vs 100 PARADOX",
}


def build_player_view(snapshot: GameSnapshot, player: PlayerState,
                      next_round: int, action_spec: dict[str, Any],
                      game_title: str) -> dict[str, Any]:
    cfg = snapshot.config
    pid = player.config.id

    # ---- Public scoreboard ------------------------------------------
    scoreboard = []
    for rank, ps in enumerate(snapshot.standings(), 1):
        scoreboard.append({
            "rank": rank,
            "player_id": ps.config.id,
            "name": ps.config.name,
            "provider": ps.config.provider,
            "model": ps.config.model,
            "score": ps.score,
            "status": ps.status,
            "eliminated_round": ps.eliminated_round,
        })

    # ---- Public round history (actions + outcomes, NO reasoning) ----
    history = []
    for rec in snapshot.rounds:
        if not rec.resolved:
            continue
        history.append({
            "round": rec.round,
            "special": rec.special,
            "special_label": SPECIAL_LABELS.get(rec.special or "", ""),
            "target": rec.target,
            "actions": dict(rec.actions),
            "deltas": {
                pid: {
                    "action": d.get("action"),
                    "distance": d.get("distance"),
                    "delta": d.get("delta"),
                    "line_items": d.get("line_items", []),
                    "valid": d.get("valid", True),
                }
                for pid, d in rec.deltas.items()
            },
        })

    # ---- Public announcements ---------------------------------------
    announcements = [
        {k: v for k, v in a.items() if k not in ("player_id",)}
        for a in snapshot.announcements
    ]

    # ---- Your OWN private state (never shared with rivals) ----------
    private_log = [
        e for e in player.reasoning_log
    ]

    opponents = []
    for ps in snapshot.players.values():
        if ps.config.id == pid:
            continue
        opponents.append({
            "player_id": ps.config.id,
            "name": ps.config.name,
            "provider": ps.config.provider,
            "model": ps.config.model,
            "score": ps.score,
            "status": ps.status,
        })

    return {
        "game_id": snapshot.game_id,
        "round": next_round,
        "game": {
            "type": cfg.game_type,
            "title": game_title,
            "mode": cfg.mode,
            "factor": cfg.factor,
            "guess_min": cfg.guess_min,
            "guess_max": cfg.guess_max,
            "rounds": cfg.rounds,
            "action_spec": action_spec,
        },
        "you": {
            "player_id": pid,
            "name": player.config.name,
            "provider": player.config.provider,
            "model": player.config.model,
            "score": player.score,
            "log": private_log,
        },
        "opponents": opponents,
        "scoreboard": scoreboard,
        "history": history,
        "active_rules": [dict(r) for r in snapshot.active_rules],
        "announcements": announcements,
    }
