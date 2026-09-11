"""The Game Master — autonomous round loop.

Responsibilities:
  * fan out one isolated prompt per alive player, in parallel;
  * validate / repair / default every action so play can never stall;
  * hand actions to the game plugin and publish every outcome as events;
  * honour dynamic-rule injections, eliminations and endgame triggers;
  * autoplay with a spectator-friendly delay, plus pause / resume / step.

The engine never puts one player's reasoning into another player's prompt:
views are built per-player by the perception layer from the public snapshot.
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .games.base import (ActionRecord, InvalidAction, RoundPlan,
                         default_action)
from .games.registry import get_game
from .gateway.base import ModelResponse, TurnRequest
from .gateway.registry import REGISTRY
from .perception import build_player_view
from .schemas import GameSnapshot, PlayerState
from .store import GameStore


@dataclass
class _Control:
    paused: bool = False
    step_requested: bool = False
    wake: asyncio.Event = field(default_factory=asyncio.Event)
    task: Optional[asyncio.Task] = None
    delay_override: Optional[float] = None


class GameMaster:
    def __init__(self, store: GameStore) -> None:
        self.store = store
        self._controls: dict[str, _Control] = {}

    # ------------------------------------------------------------------
    # Lifecycle commands
    # ------------------------------------------------------------------
    def _ctrl(self, game_id: str) -> _Control:
        return self._controls.setdefault(game_id, _Control())

    async def start(self, game_id: str) -> None:
        snap = self.store.get(game_id)
        if snap.status in ("running",):
            return
        ctrl = self._ctrl(game_id)
        ctrl.paused = False
        ctrl.step_requested = False
        ctrl.wake.set()
        plugin = get_game(snap.config.game_type)
        plugin_state = plugin.initial_state(snap.config)
        await self.store.emit(game_id, "game_started",
                              {"plugin_state": plugin_state})
        for rule in plugin.intro_rules(snap.config):
            await self.store.emit(game_id, "rule_injected",
                                  {"round": 0, "rule": rule})
        if ctrl.task is None or ctrl.task.done():
            ctrl.task = asyncio.create_task(self._run(game_id))

    async def pause(self, game_id: str) -> None:
        ctrl = self._ctrl(game_id)
        ctrl.paused = True
        ctrl.step_requested = False
        await self.store.emit(game_id, "game_paused", {})

    async def resume(self, game_id: str) -> None:
        snap = self.store.get(game_id)
        if snap.status == "finished":
            return
        if snap.status == "setup":
            await self.start(game_id)
            return
        ctrl = self._ctrl(game_id)
        ctrl.paused = False
        ctrl.step_requested = False
        ctrl.wake.set()
        await self.store.emit(game_id, "game_resumed", {})
        if ctrl.task is None or ctrl.task.done():
            ctrl.task = asyncio.create_task(self._run(game_id))

    async def step(self, game_id: str) -> None:
        """Advance exactly one round, then (re)pause."""
        snap = self.store.get(game_id)
        if snap.status == "finished":
            return
        ctrl = self._ctrl(game_id)
        ctrl.paused = True
        ctrl.step_requested = True
        ctrl.wake.set()
        if ctrl.task is None or ctrl.task.done():
            # Bootstrap from setup: intro events, park in paused state, then
            # the single granted step plays exactly one round.
            plugin = get_game(snap.config.game_type)
            plugin_state = plugin.initial_state(snap.config)
            await self.store.emit(game_id, "game_started",
                                  {"plugin_state": plugin_state})
            for rule in plugin.intro_rules(snap.config):
                await self.store.emit(game_id, "rule_injected",
                                      {"round": 0, "rule": rule})
            await self.store.emit(game_id, "game_paused", {})
            ctrl.task = asyncio.create_task(self._run(game_id))

    def set_speed(self, game_id: str, delay: float) -> None:
        self._ctrl(game_id).delay_override = max(0.0, delay)

    # ------------------------------------------------------------------
    # The loop
    # ------------------------------------------------------------------
    async def _gate(self, ctrl: _Control) -> None:
        while ctrl.paused and not ctrl.step_requested:
            ctrl.wake.clear()
            await ctrl.wake.wait()
        if ctrl.step_requested:
            ctrl.step_requested = False
            ctrl.paused = True

    async def _interruptible_sleep(self, ctrl: _Control, seconds: float) -> None:
        waited = 0.0
        while waited < seconds:
            if ctrl.paused:
                return
            await asyncio.sleep(min(0.1, seconds - waited))
            waited += 0.1

    async def _run(self, game_id: str) -> None:
        ctrl = self._ctrl(game_id)
        try:
            while True:
                snap = self.store.get(game_id)
                if snap.status == "finished":
                    return
                await self._gate(ctrl)
                if self.store.get(game_id).status == "finished":
                    return

                round_no = snap.current_round + 1
                await self._play_round(game_id, round_no)

                snap = self.store.get(game_id)
                if snap.status == "finished":
                    return
                cap = self._round_cap(snap)
                if round_no >= cap:
                    alive = snap.alive_players()
                    winner = min(alive, key=lambda p: (p.score, p.config.id)).config.id
                    await self.store.emit(game_id, "game_ended", {
                        "winner_id": winner,
                        "reason": f"round cap {cap} reached",
                        "plugin_state": snap.plugin_state,
                    })
                    return
                delay = (ctrl.delay_override if ctrl.delay_override is not None
                         else snap.config.round_delay)
                await self._interruptible_sleep(ctrl, delay)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # never let a game die silently
            await self.store.emit(game_id, "notice",
                                  {"message": f"Referee error: {exc!r}",
                                   "severity": "danger"})
            raise

    @staticmethod
    def _round_cap(snap: GameSnapshot) -> int:
        cfg = snap.config
        if cfg.mode == "fixed":
            return cfg.rounds
        return min(24, max(cfg.rounds, (len(cfg.players) - 1) * cfg.eliminate_every))

    # ------------------------------------------------------------------
    # One round
    # ------------------------------------------------------------------
    async def _play_round(self, game_id: str, round_no: int) -> None:
        snap = self.store.get(game_id)
        cfg = snap.config
        plugin = get_game(cfg.game_type)
        state = copy.deepcopy(snap.plugin_state or plugin.initial_state(cfg))

        plan = plugin.plan_round(state, snap, round_no)
        for rule in plan.inject:
            await self.store.emit(game_id, "rule_injected",
                                  {"round": round_no, "rule": rule})
        for rid in plan.retract:
            await self.store.emit(game_id, "rule_retracted",
                                  {"round": round_no, "rule_id": rid})
        await self.store.emit(game_id, "round_started", {
            "round": round_no,
            "special": plan.special,
            "active_rules": state.get("active_rule_ids", []),
            "plugin_state": state,
        })

        alive = [p for p in snap.players.values() if p.status == "alive"]
        await asyncio.gather(*(
            self._take_turn(game_id, plugin, plan, state, ps, round_no)
            for ps in alive
        ))

        # Resolve from the pre-resolution snapshot (scores not yet applied).
        snap = self.store.get(game_id)
        records: dict[str, ActionRecord] = {}
        for ps in snap.alive_players():
            # Rebuild records from the actions just stored this round.
            current = snap.rounds[-1].actions.get(ps.config.id)
            # validity is carried via the player's last_error fallback flag;
            # ActionRecord is reconstructed by re-reading the acted event.
            valid = ps.last_error is None
            records[ps.config.id] = ActionRecord(action=current, valid=valid,
                                                 error=ps.last_error)

        outcome = plugin.resolve_round(state, snap, round_no, records)

        for rule in outcome.inject:
            await self.store.emit(game_id, "rule_injected",
                                  {"round": round_no, "rule": rule})
        for rid in outcome.retract:
            await self.store.emit(game_id, "rule_retracted",
                                  {"round": round_no, "rule_id": rid})
        await self.store.emit(game_id, "round_resolved", {
            "round": round_no,
            "special": outcome.special,
            "target": outcome.target,
            "deltas": outcome.deltas,
            "plugin_state": state,
        })
        for notice in outcome.notices:
            await self.store.emit(game_id, "notice",
                                  {"round": round_no, **notice})
        for elim in outcome.eliminations:
            await self.store.emit(game_id, "player_eliminated", elim)
        if outcome.winner_id:
            await self.store.emit(game_id, "game_ended", {
                "winner_id": outcome.winner_id,
                "reason": outcome.end_reason or "endgame triggered",
                "plugin_state": state,
            })

    # ------------------------------------------------------------------
    # One player turn (isolated prompt context)
    # ------------------------------------------------------------------
    async def _take_turn(self, game_id: str, plugin, plan: RoundPlan,
                         state: dict, ps: PlayerState, round_no: int) -> None:
        cfg = self.store.get(game_id).config
        await self.store.emit(game_id, "player_thinking",
                              {"player_id": ps.config.id, "round": round_no})

        view = build_player_view(self.store.get(game_id), ps, round_no,
                                 plan.action_spec, plugin.title)
        system_prompt, user_prompt = plugin.build_prompts(view, plan)
        seed = int(hashlib.sha256(
            f"{game_id}|{ps.config.id}|{round_no}".encode()).hexdigest()[:12], 16)
        req = TurnRequest(
            player=ps.config,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            action_hint=plan.action_hint,
            action_spec=plan.action_spec,
            view=view,
            seed=seed,
            temperature=ps.config.temperature,
        )
        gw, key = REGISTRY.gateway_for(ps.config.provider)

        resp: Optional[ModelResponse] = None
        err: Optional[str] = None
        started = time.perf_counter()
        try:
            resp = await gw.generate(req, key)
        except Exception as exc:  # network, auth, parse, timeout ...
            err = f"{type(exc).__name__}: {exc}"[:400]

        action = None
        if resp is not None and err is None:
            try:
                action = plugin.coerce_action(resp.action, plan, cfg)
            except InvalidAction as exc:
                err = f"illegal action {resp.action!r}: {exc}"

        # One repair attempt with explicit feedback (live LLMs only; mocks
        # always emit legal actions).
        if err is not None and resp is not None and ps.config.provider != "mock":
            repair = TurnRequest(
                player=req.player,
                system_prompt=req.system_prompt,
                user_prompt=(req.user_prompt +
                             f"\n\n⚠ YOUR PREVIOUS REPLY WAS REJECTED ({err}). "
                             "Respond again with ONLY the required JSON and a "
                             f"legal action. {plan.action_hint}"),
                action_hint=plan.action_hint, action_spec=plan.action_spec,
                view=view, seed=seed + 1, temperature=req.temperature)
            try:
                resp2 = await gw.generate(repair, key)
                action2 = plugin.coerce_action(resp2.action, plan, cfg)
                resp, action, err = resp2, action2, None
            except Exception as exc:
                err = f"{err} | repair failed: {type(exc).__name__}: {exc}"[:400]

        latency = int((time.perf_counter() - started) * 1000)
        if resp is not None and resp.latency_ms and ps.config.provider != "mock":
            latency = resp.latency_ms

        fallback = action is None
        if fallback:
            action = self._default_action(plan, ps.config.id, round_no)
            reasoning = (
                f"⚠ NO VALID RESPONSE — {err or 'unknown failure'}. "
                "The referee assigned a default legal move and a +10 "
                "invalid-response violation.")
            await self.store.emit(game_id, "player_acted", {
                "player_id": ps.config.id, "round": round_no,
                "action": action, "reasoning": reasoning,
                "latency_ms": latency, "tokens_in": 0, "tokens_out": 0,
                "retries": 1, "provider": ps.config.provider,
                "model": ps.config.model, "error": err, "fallback": True,
            })
        else:
            await self.store.emit(game_id, "player_acted", {
                "player_id": ps.config.id, "round": round_no,
                "action": action,
                "reasoning": (resp.reasoning if resp and resp.reasoning
                              else "(model returned no reasoning)"),
                "latency_ms": latency,
                "tokens_in": getattr(resp, "tokens_in", 0),
                "tokens_out": getattr(resp, "tokens_out", 0),
                "retries": getattr(resp, "retries", 0),
                "provider": ps.config.provider,
                "model": ps.config.model,
                "error": None, "fallback": False,
            })

    @staticmethod
    def _default_action(plan: RoundPlan, pid: str, round_no: int) -> int:
        return default_action(plan.action_spec, pid, round_no)
