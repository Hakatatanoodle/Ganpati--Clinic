"""Keynesian Beauty Contest — "Guess 0.8 of the Average".

Flagship game of the arena. Each round every alive player privately picks a
number in [0, 100]; the target is factor x mean(guesses); distance from target
scores as penalty points (lowest cumulative score wins). Hyper-rational level-k
play converges on the 0 focal point — identical models crash there together.

Dynamic rule injections (config toggles):

* DUPLICATE COLLISION RULE   (after round 1) — tied guesses each cost +10.
* BULLSEYE BONUS             (after round 2) — hitting the target within 0.5
                                               pays -15.
* SUDDEN-DEATH PARADOX       (after every elimination) — the next round is
  restricted to {0, 100}. With q = fraction choosing 100 the target = 80q,
  and the best response flips at q = 0.625: a pure coordination/bluff shock.
"""
from __future__ import annotations

import json
from typing import Any

from ..schemas import GameConfig, GameSnapshot
from .base import ActionRecord, GamePlugin, InvalidAction, RoundOutcome, RoundPlan


RULE_CORE = {
    "id": "core",
    "title": "Core Rules — Guess the Factor × Average",
    "description": (
        "Each round, secretly choose an integer in the allowed range. "
        "The target equals FACTOR × the mean of all guesses. "
        "Your round penalty is the distance from your guess to the target. "
        "Lowest cumulative penalty wins."),
    "severity": "core",
}
RULE_DUPLICATE = {
    "id": "duplicate_penalty",
    "title": "DYNAMIC RULE INJECTED — Duplicate Collision Rule",
    "description": (
        "If two or more alive players submit the SAME guess in a round, "
        "each colliding player suffers +10 penalty. Distinctness now matters."),
    "severity": "warning",
}
RULE_BULLSEYE = {
    "id": "exact_match_bonus",
    "title": "DYNAMIC RULE INJECTED — Bullseye Bonus",
    "description": (
        "Any guess within 0.5 of the target earns -15 points. "
        "Precision is now rewarded as well as convergence."),
    "severity": "bonus",
}
RULE_PARADOX = {
    "id": "sudden_death_paradox",
    "title": "DYNAMIC RULE INJECTED — Sudden-Death 0 vs 100 Paradox",
    "description": (
        "Blood has been spilled. The NEXT round is binary: legal moves are "
        "ONLY 0 or 100. The target is still 0.8 × average. If q is the share "
        "choosing 100, target = 80q; choosing 0 costs 80q, choosing 100 costs "
        "|100-80q|. The best response flips at q = 0.625. Read the crowd."),
    "severity": "danger",
    "one_shot": True,
}


class BeautyContestPlugin(GamePlugin):
    id = "beauty_contest"
    title = "Keynesian Beauty Contest — Guess the Factor-Times-Average"
    description = __doc__ or ""

    # ------------------------------------------------------------------
    def initial_state(self, config: GameConfig) -> dict[str, Any]:
        return {
            "active_rule_ids": ["core"],
            "pending_special": None,
            "resolved_count": 0,
            "paradox_rounds": [],
        }

    def intro_rules(self, config: GameConfig) -> list[dict[str, Any]]:
        return [dict(RULE_CORE) | {"factor": config.factor}]

    # ------------------------------------------------------------------
    def plan_round(self, state: dict[str, Any], snapshot: GameSnapshot,
                   round_no: int) -> RoundPlan:
        cfg = snapshot.config
        inject: list[dict[str, Any]] = []
        retract: list[str] = []
        special = None

        if state.get("pending_special") == "sudden_death_binary":
            special = "sudden_death_binary"
            state["pending_special"] = None
            state["paradox_rounds"].append(round_no)
            spec = {"kind": "choice", "options": [0, 100], "integer": True}
            hint = (
                "SUDDEN-DEATH PARADOX ROUND. Your action MUST be exactly the "
                "integer 0 or the integer 100. No other value is legal."
            )
        else:
            spec = {"kind": "number", "min": cfg.guess_min,
                    "max": cfg.guess_max, "integer": True}
            hint = (
                f"Choose ONE integer between {cfg.guess_min} and "
                f"{cfg.guess_max} inclusive."
            )
        return RoundPlan(special=special, action_spec=spec, action_hint=hint,
                         inject=inject, retract=retract)

    # ------------------------------------------------------------------
    def coerce_action(self, raw: Any, plan: RoundPlan,
                      config: GameConfig) -> Any:
        spec = plan.action_spec
        if spec["kind"] == "choice":
            options = [str(o) for o in spec["options"]]
            text = str(raw).strip()
            if text in options:
                return int(text)
            for o in options:
                if o in text:
                    return int(o)
            raise InvalidAction(
                f"paradox round accepts only {spec['options']}, got {raw!r}")
        # numeric
        try:
            value = float(str(raw).strip())
        except (TypeError, ValueError):
            raise InvalidAction(f"expected a number, got {raw!r}")
        if value != value:  # NaN
            raise InvalidAction("NaN is not a legal guess")
        value = int(round(value))
        lo, hi = spec["min"], spec["max"]
        if not (lo <= value <= hi):
            raise InvalidAction(f"guess {value} outside [{lo},{hi}]")
        return value

    # ------------------------------------------------------------------
    def resolve_round(self, state: dict[str, Any], snapshot: GameSnapshot,
                      round_no: int,
                      actions: dict[str, ActionRecord]) -> RoundOutcome:
        cfg = snapshot.config
        dr = cfg.dynamic_rules
        alive = [p for p in snapshot.players.values() if p.status == "alive"]
        alive_ids = [p.config.id for p in alive]

        # Invalid actions get a punitive default so play never stalls.
        defaults: dict[str, float] = {}
        if plan_spec_is_binary(state, round_no):
            defaults = {pid: (100 if (i % 2) else 0)
                        for i, pid in enumerate(alive_ids)}
        else:
            defaults = {pid: float(cfg.guess_max) for pid in alive_ids}

        guesses: dict[str, float] = {}
        for pid in alive_ids:
            rec = actions.get(pid)
            if rec is None or not rec.valid:
                guesses[pid] = defaults[pid]
            else:
                guesses[pid] = float(rec.action)

        mean = sum(guesses.values()) / len(guesses)
        target = round(cfg.factor * mean, 4)

        # --- Line items ---------------------------------------------------
        deltas: dict[str, dict[str, Any]] = {}
        groups: dict[float, list[str]] = {}
        for pid, g in guesses.items():
            groups.setdefault(g, []).append(pid)

        for pid in alive_ids:
            rec = actions.get(pid)
            g = guesses[pid]
            distance = round(abs(g - target), 4)
            items: list[dict[str, Any]] = [
                {"label": f"distance to target {target:g}", "amount": distance}]
            delta = distance
            if (dr.duplicate_penalty
                    and "duplicate_penalty" in state["active_rule_ids"]
                    and len(groups[g]) > 1):
                items.append({"label": "duplicate collision", "amount": 10.0})
                delta += 10.0
            if (dr.exact_match_bonus
                    and "exact_match_bonus" in state["active_rule_ids"]
                    and distance <= 0.5):
                items.append({"label": "bullseye bonus", "amount": -15.0})
                delta -= 15.0
            if rec is None or not rec.valid:
                items.append({"label": "invalid response violation",
                              "amount": 10.0})
                delta += 10.0
            deltas[pid] = {"action": g, "guess": g, "distance": distance,
                           "delta": round(delta, 4), "line_items": items,
                           "valid": bool(rec and rec.valid)}

        state["resolved_count"] += 1
        inject: list[dict[str, Any]] = []
        retract: list[str] = []
        notices: list[dict[str, Any]] = []

        # --- Elimination / endgame (decided before scheduling new rules) --
        eliminations: list[dict[str, Any]] = []
        winner_id = None
        end_reason = None
        projected = {pid: round(snapshot.players[pid].score
                                + deltas[pid]["delta"], 4) for pid in alive_ids}

        if cfg.mode == "elimination" and round_no % cfg.eliminate_every == 0:
            victim = self._pick_victim(alive_ids, projected, deltas)
            eliminations.append({
                "player_id": victim,
                "round": round_no,
                "reason": (f"Highest cumulative penalty after round {round_no} "
                           f"({projected[victim]:g} pts)"),
            })
            survivors = [p for p in alive_ids if p != victim]
            if len(survivors) == 1:
                winner_id = survivors[0]
                end_reason = "last contestant standing"
            elif dr.sudden_death_paradox:
                state["pending_special"] = "sudden_death_binary"
                if "sudden_death_paradox" not in state["active_rule_ids"]:
                    state["active_rule_ids"].append("sudden_death_paradox")
                inject.append(dict(RULE_PARADOX))

        if cfg.mode == "fixed" and round_no >= cfg.rounds:
            winner_id = self._lowest(alive_ids, projected, deltas)
            end_reason = f"completed {cfg.rounds} rounds"

        # --- Schedule dynamic rules (never after the game has ended) -----
        if winner_id is None:
            if round_no == 1 and dr.duplicate_penalty:
                inject.append(dict(RULE_DUPLICATE))
                state["active_rule_ids"].append("duplicate_penalty")
            if round_no == 2 and dr.exact_match_bonus:
                inject.append(dict(RULE_BULLSEYE))
                state["active_rule_ids"].append("exact_match_bonus")

        # One-shot paradox rule is consumed after its binary round resolves.
        if round_no in state.get("paradox_rounds", []):
            if "sudden_death_paradox" in state["active_rule_ids"]:
                state["active_rule_ids"].remove("sudden_death_paradox")
            retract.append("sudden_death_paradox")
            notices.append({"message": "The paradox window closes; normal play resumes.",
                            "severity": "info"})

        target_note = {"message": (
            f"Mean guess {mean:.2f} × {cfg.factor:g} → target {target:g}. "
            + ("Tied guesses penalized. " if any(
                len(v) > 1 for v in groups.values())
                and dr.duplicate_penalty
                and "duplicate_penalty" in state["active_rule_ids"] else "")
        ), "severity": "info"}
        notices.insert(0, target_note)

        return RoundOutcome(
            target=target, deltas=deltas,
            special=("sudden_death_binary"
                     if round_no in state.get("paradox_rounds", []) else None),
            inject=inject, retract=retract,
            eliminations=eliminations, notices=notices,
            winner_id=winner_id, end_reason=end_reason)

    # ------------------------------------------------------------------
    def _pick_victim(self, alive_ids: list[str], projected: dict[str, float],
                     deltas: dict[str, dict]) -> str:
        def key(pid: str) -> tuple:
            return (-projected[pid], -deltas[pid]["distance"], pid)
        return max(alive_ids, key=key)

    def _lowest(self, alive_ids: list[str], projected: dict[str, float],
                deltas: dict[str, dict]) -> str:
        def key(pid: str) -> tuple:
            return (projected[pid], deltas[pid]["distance"], pid)
        return min(alive_ids, key=key)

    # ------------------------------------------------------------------
    def build_prompts(self, view: dict[str, Any], plan: RoundPlan) -> tuple[str, str]:
        g = view["game"]
        persona_name = view["you"]["name"]
        system = f"""You are {persona_name}, an autonomous frontier AI model competing in the
ARENA — a multi-model game-theory battleground. You are playing the
"{self.title}".

{self._rules_text(view)}

STRATEGIC PROTOCOL
- This is adversarial. Other players receive ONLY public information: the
  scoreboard and the public action history. They can NEVER see your reasoning.
- Use level-k reasoning: what level-0 players guess, what level-1 players do
  with that, what level-2 players do with that... iterate as deep as is
  rational for you, then decide.
- Adapt INSTANTLY to any newly injected dynamic rules; they override the
  baseline game.
- You are {persona_name}. Stay in character and reason according to your
  model's nature — but choose your move to win.

OUTPUT CONTRACT — respond with ONLY a minified JSON object, no markdown fence:
{{"reasoning": "<your concise private strategic analysis>", "action": <your move>}}
The referee parses "action" programmatically. This round: {plan.action_hint}"""

        lines = [
            f"ROUND {view['round']} — {g['mode']} mode.",
            "",
            "PUBLIC SCOREBOARD (cumulative penalty — lower is better):",
        ]
        for i, row in enumerate(view["scoreboard"], 1):
            marker = " (YOU)" if row["player_id"] == view["you"]["player_id"] else ""
            status = "" if row["status"] == "alive" else " [ELIMINATED]"
            lines.append(f"  {i}. {row['name']}{marker} — {row['score']:g} pts{status}")

        if view["history"]:
            lines += ["", "PUBLIC HISTORY (all moves are revealed each round):"]
            for rd in view["history"]:
                tag = f" [{rd.get('special_label')}]" if rd.get("special") else ""
                lines.append(f"  Round {rd['round']}{tag} — target {rd['target']:g}")
                for pid, mv in rd["actions"].items():
                    nm = next((o["name"] for o in view["opponents"]
                               if o["player_id"] == pid), None)
                    nm = nm or ("YOU" if pid == view["you"]["player_id"] else pid)
                    d = rd["deltas"].get(pid, {})
                    lines.append(
                        f"      {nm}: {mv} → {d.get('delta', '?'):g} pts"
                        if isinstance(d.get("delta"), (int, float))
                        else f"      {nm}: {mv}")

        if view.get("announcements"):
            lines += ["", "ARENA ANNOUNCEMENTS (public, in order):"]
            for a in view["announcements"][-8:]:
                lines.append(f"  • {a.get('title', a.get('message', a))}")
                if a.get("description"):
                    lines.append(f"      {a['description']}")

        lines += [
            "",
            f"YOUR PRIVATE STATE — cumulative penalty: {view['you']['score']:g}.",
        ]
        if view["you"].get("log"):
            lines.append("Your previous private reasoning (invisible to rivals):")
            for entry in view["you"]["log"][-3:]:
                lines.append(f"  R{entry['round']}: {entry['reasoning']} "
                             f"→ you played {entry['action']}")

        lines += [
            "",
            f"NOW DECIDE ROUND {view['round']}.",
            f"Legal move: {plan.action_hint}",
            "Reply with exactly one JSON object: "
            '{"reasoning": "...", "action": <move>}',
        ]
        return system, "\n".join(lines)

    def _rules_text(self, view: dict[str, Any]) -> str:
        g = view["game"]
        chunks = [f"- Each round choose an integer in [{g['guess_min']}, {g['guess_max']}]."]
        chunks.append(f"- target = {g['factor']:g} × mean(all guesses).")
        chunks.append("- round penalty = |your guess − target|; penalties accumulate.")
        for r in view.get("active_rules", []):
            if r["id"] == "core":
                continue
            chunks.append(f"- {r['title']}: {r['description']}")
        if g["mode"] == "elimination":
            chunks.append(
                f"- Elimination mode: at checkpoints the player with the HIGHEST "
                f"cumulative penalty is executed; the last one alive wins.")
        else:
            chunks.append(f"- Fixed mode: after {g['rounds']} rounds the lowest penalty wins.")
        return "\n".join(chunks)


def plan_spec_is_binary(state: dict[str, Any], round_no: int) -> bool:
    """Resolve-time mirror of plan_round's special selection."""
    # The round was planned immediately before resolution; paradox_rounds only
    # gains the current round number inside plan_round.
    return round_no in state.get("paradox_rounds", [])
