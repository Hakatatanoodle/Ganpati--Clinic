"""Simulated frontier-model personas — fully playable without API keys.

Each persona implements heterogeneous level-k reasoning for the Keynesian
beauty contest, calibrated so the classic phenomena emerge spontaneously:

* DeepSeek  -> deepest recursion, converges toward the 0 focal point
* Claude    -> cautious, rule-aware, avoids collisions, nudges toward 0
* ChatGPT   -> balanced 2-level empiricist
* Gemini    -> history-driven, tracks the empirical mean
* Grok      -> shallow / chaotic level-0-1 reasoner, bluffs and defies

Each persona returns a genuine (if templated) chain of thought so the
spectator dashboard demonstrates the full experience keyless. RNG is seeded
per (game, player, round) so matches are reproducible.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Any

from .base import ModelGateway, ModelResponse, TurnRequest


@dataclass(frozen=True)
class Persona:
    id: str
    label: str
    blurb: str
    depth: tuple[int, int]      # level-k range
    noise: float                # tremble on final guess
    anchor_bias: float          # prior about naive players' average
    rule_awareness: float       # 0..1 how strongly rules alter behavior
    bluff: float                # probability of contrarian defiance
    assumes_others_depth: int   # believed depth of opponents


PERSONAS: dict[str, Persona] = {
    "deepseek-sim": Persona(
        "deepseek-sim", "DeepSeek (sim)", "Hyper-rational recursion engine",
        (5, 6), 0.6, -6.0, 0.95, 0.03, 3),
    "claude-sim": Persona(
        "claude-sim", "Claude (sim)", "Cautious, rule-abiding strategist",
        (3, 4), 1.4, -3.0, 1.0, 0.05, 2),
    "chatgpt-sim": Persona(
        "chatgpt-sim", "ChatGPT (sim)", "Balaced adaptive empiricist",
        (2, 3), 2.2, 0.0, 0.8, 0.10, 2),
    "gemini-sim": Persona(
        "gemini-sim", "Gemini (sim)", "Data-driven pattern matcher",
        (2, 2), 3.0, 1.0, 0.75, 0.12, 1),
    "grok-sim": Persona(
        "grok-sim", "Grok (sim)", "Chaotic provocateur and bluffer",
        (0, 1), 15.0, 8.0, 0.45, 0.38, 1),
}

# How a persona *expects* opponents to behave, keyed by name substrings.
_NAME_PRIOR_DEPTH = {"deepseek": 4, "claude": 3, "gpt": 2, "chatgpt": 2,
                     "gemini": 2, "grok": 1}
_NAME_PRIOR_ANCHOR = {"deepseek": 42.0, "claude": 46.0, "gemini": 50.0,
                      "gpt": 50.0, "chatgpt": 50.0, "grok": 58.0}


def _name_depth(name: str) -> int:
    low = name.lower()
    for key, d in _NAME_PRIOR_DEPTH.items():
        if key in low:
            return d
    return 1


def _name_anchor(name: str) -> float:
    low = name.lower()
    for key, a in _NAME_PRIOR_ANCHOR.items():
        if key in low:
            return a
    return 50.0


class MockGateway(ModelGateway):
    async def generate(self, req: TurnRequest, key: str | None = None) -> ModelResponse:
        persona_id = req.player.model or req.player.persona or "chatgpt-sim"
        persona = PERSONAS.get(persona_id, PERSONAS["chatgpt-sim"])
        view = req.view or {}
        rng = random.Random(req.seed or _seed(view, req))

        spec = req.action_spec
        if spec.get("kind") == "choice":
            action, reasoning = self._binary_round(persona, view, rng)
        elif spec.get("kind") == "number":
            action, reasoning = self._number_round(persona, view, spec, rng)
        else:
            action, reasoning = spec.get("min", 0), "Unfamiliar action space; playing it safe."

        lo = min(spec.get("options", [spec.get("min", action)])) if spec else action
        hi = max(spec.get("options", [spec.get("max", action)])) if spec else action
        action = max(lo, min(hi, action))
        if spec.get("integer", True) and isinstance(action, float):
            action = int(round(action))
        return ModelResponse(reasoning=reasoning, action=action, raw="(simulated)")

    # ------------------------------------------------------------------
    def _number_round(self, persona: Persona, view: dict, spec: dict,
                      rng: random.Random) -> tuple[float, str]:
        factor = float(view["game"].get("factor", 0.8))
        lo, hi = spec.get("min", 0), spec.get("max", 100)
        me_id = view["you"]["player_id"]
        history = view.get("history", [])
        active = {r["id"] for r in view.get("active_rules", [])}

        # --- Model each opponent's level-0 (naive) next guess -------------
        opp_anchors: dict[str, float] = {}
        for opp in view.get("opponents", []):
            prior = _name_anchor(opp["name"]) + persona.anchor_bias * 0.15
            guesses = [r.get("actions", {}).get(opp["player_id"]) for r in history]
            guesses = [g for g in guesses if isinstance(g, (int, float))]
            if guesses:
                if len(guesses) >= 2:
                    momentum = guesses[-1] - guesses[-2]
                    projected = guesses[-1] + 0.5 * momentum
                else:
                    projected = guesses[-1]
                # Empiricists trust history more; ideologues trust priors more.
                trust = 0.85 if persona.id == "gemini-sim" else 0.65
                anchor = trust * projected + (1 - trust) * prior
            else:
                anchor = prior + rng.uniform(-4, 4)
            opp_anchors[opp["player_id"]] = float(anchor)

        anchors = list(opp_anchors.values()) or [50.0]
        naive_mean = sum(anchors) / len(anchors)

        # --- Level-k iteration: best response to best response ... --------
        depth = rng.randint(*persona.depth)
        guess = naive_mean
        steps = []
        for level in range(1, depth + 1):
            guess = factor * guess
            steps.append(round(guess, 2))

        # --- Predict opponents' final guesses (for collision avoidance) ---
        predicted_others: list[float] = []
        for opp in view.get("opponents", []):
            a = opp_anchors.get(opp["player_id"], 50.0)
            d = _name_depth(opp["name"])
            pred = a * (factor ** d)
            pred += rng.uniform(-2.5, 2.5)
            predicted_others.append(pred)

        notes: list[str] = []
        # Duplicate-collision rule response
        if "duplicate_penalty" in active:
            collisions = [o for o in predicted_others if abs(o - guess) <= 1.5]
            if collisions:
                dodge = persona.rule_awareness * rng.uniform(2.0, 5.0)
                guess -= dodge          # pivot downward away from the pack
                notes.append(
                    f"Duplicate rule live: {len(collisions)} opponent(s) projected "
                    f"near {round(guess + dodge, 1)} — I diverge downward by {dodge:.1f}."
                )
            else:
                notes.append("Duplicate rule live: my guess looks distinct; holding.")

        if "exact_match_bonus" in active:
            notes.append("Bullseye bonus active: rounding cleanly to maximize an exact hit.")
            guess = round(guess)

        # Persona tremble / noise
        guess += rng.gauss(0, persona.noise)
        # Grok's signature chaos: occasional defiant high anchor
        if persona.id == "grok-sim" and rng.random() < 0.30:
            guess = rng.uniform(45, hi)
            notes.append("They all spiral toward 0... predictable. I defy the spiral.")

        guess = max(lo, min(hi, guess))
        guess = float(int(round(guess)))

        reasoning = self._narrate(
            persona, naive_mean, factor, depth, steps, notes,
            history, predicted_others, binary=False)
        return guess, reasoning

    # ------------------------------------------------------------------
    def _binary_round(self, persona: Persona, view: dict,
                      rng: random.Random) -> tuple[float, str]:
        """Sudden-death paradox: actions restricted to {0, 100}.

        With q = fraction choosing 100: target = 80q.
        choose 0  -> distance 80q
        choose 100 -> distance |100 - 80q|
        crossover at q = 0.625. Below it, 0 wins; above it, 100 wins.
        """
        history = view.get("history", [])
        qs: list[float] = []
        for opp in view.get("opponents", []):
            guesses = [r.get("actions", {}).get(opp["player_id"]) for r in history]
            guesses = [g for g in guesses if isinstance(g, (int, float))]
            if guesses:
                aggression = sum(1 for g in guesses if g > 50) / len(guesses)
                q = 0.30 + 0.4 * aggression
            else:
                q = {"deepseek": 0.20, "claude": 0.28}.get(
                    next((k for k in _NAME_PRIOR_DEPTH if k in opp["name"].lower()), ""), 0.45)
            qs.append(q)
        q_mean = sum(qs) / len(qs) if qs else 0.45
        q_mean = max(0.0, min(1.0, q_mean + rng.gauss(0, 0.05)))

        rational = 100 if q_mean > 0.625 else 0
        notes = [
            f"Binary paradox: if q={q_mean:.2f} of them pick 100, target = {80*q_mean:.1f}.",
            f"Distances — choosing 0: {80*q_mean:.1f}, choosing 100: {abs(100-80*q_mean):.1f}.",
        ]
        if rng.random() < persona.bluff:
            action = 0 if rational == 100 else 100
            notes.append(
                f"Everyone computes the same equilibrium — I bluff AGAINST it and choose {action}."
            )
        else:
            action = rational
            notes.append(f"Best response at q={q_mean:.2f} is {action}.")
        reasoning = self._narrate(
            persona, q_mean * 100, 0.8, persona.depth[0], [], notes,
            history, [], binary=True)
        return float(action), reasoning

    # ------------------------------------------------------------------
    def _narrate(self, persona: Persona, naive_mean: float, factor: float,
                 depth: int, steps: list[float], notes: list[str],
                 history: list[dict], predicted: list[float],
                 binary: bool) -> str:
        lines = [f"[{persona.label} — internal]"]
        if binary:
            lines.append("Sudden-death {0,100} paradox round. Estimating the crowd's mix.")
        else:
            if history:
                lines.append(
                    f"Round {len(history) + 1}: observed naive mean ≈ {naive_mean:.1f}.")
            else:
                lines.append(
                    f"Opening round: strangers at the table; naive anchor ≈ {naive_mean:.1f}.")
                lines.append(
                    f"The target is {factor}× the average, so raw averages never win.")
            if steps:
                shown = ", ".join(f"L{i+1}→{s:g}" for i, s in enumerate(steps[:6]))
                lines.append(f"Level-k descent ({depth} levels): {shown}.")
            if predicted and not binary:
                lines.append(
                    "Projected final guesses of rivals: "
                    + ", ".join(f"{p:.0f}" for p in predicted[:6]) + ".")
        for n in notes:
            lines.append(n)
        return " ".join(lines)


def _seed(view: dict, req: TurnRequest) -> int:
    raw = f"{view.get('game_id','')}|{req.player.id}|{view.get('round',0)}"
    return int(hashlib.sha256(raw.encode()).hexdigest()[:12], 16)
