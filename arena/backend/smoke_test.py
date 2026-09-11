"""Headless verification: full mock games, isolation + replay invariants."""
import asyncio
import json
import tempfile

from arena.engine import GameMaster
from arena.perception import build_player_view
from arena.schemas import GameConfig, PlayerConfig
from arena.store import GameStore
from arena.games.registry import get_game


def make_players(n=5):
    personas = ["grok-sim", "chatgpt-sim", "claude-sim", "gemini-sim", "deepseek-sim"]
    names = ["Grok", "ChatGPT", "Claude", "Gemini", "DeepSeek"]
    return [PlayerConfig(name=names[i], provider="mock", model=personas[i],
                         persona=personas[i]) for i in range(n)]


async def run_game(mode, n=5, rounds=4, rules=None):
    tmp = tempfile.mkdtemp()
    store = GameStore(tmp)
    master = GameMaster(store)
    master_turn_delay = 0
    cfg = GameConfig(mode=mode, rounds=rounds, round_delay=0,
                     dynamic_rules=rules or GameConfig().dynamic_rules,
                     players=make_players(n))
    gid = "testgame01"
    store.create(gid, cfg)
    await store.emit(gid, "game_created", {
        "config": cfg.model_dump(),
        "players": {pc.id: {"config": pc.model_dump()} for pc in cfg.players},
    })
    await master.start(gid)
    # wait for finish
    for _ in range(600):
        if store.get(gid).status == "finished":
            break
        await asyncio.sleep(0.05)
    return store, master, gid


def assert_isolation(store, gid):
    """No player view may ever contain another player's private reasoning."""
    snap = store.get(gid)
    plugin = get_game("beauty_contest")
    for rec in snap.rounds:
        plan = plugin.plan_round(
            {"pending_special": "sudden_death_binary" if rec.special else None,
             "paradox_rounds": [rec.round] if rec.special else []},
            snap, rec.round)
    for ps in snap.players.values():
        view = build_player_view(snap, ps, 1, plan.action_spec, plugin.title)
        blob = json.dumps(view)
        # Everyone else's reasoning must be absent; own appears only under you.
        for other in snap.players.values():
            if other.config.id == ps.config.id:
                continue
            for entry in other.reasoning_log:
                secret = entry["reasoning"][:40]
                if secret and secret in blob:
                    raise AssertionError(
                        f"LEAK: {other.config.name}'s reasoning visible to "
                        f"{ps.config.name}")
    print("  ✓ perception isolation: zero cross-player reasoning leakage")


async def main():
    print("=== ELIMINATION MODE (5 players) ===")
    store, master, gid = await run_game("elimination", n=5)
    snap = store.get(gid)
    assert snap.status == "finished", snap.status
    for rec in snap.rounds:
        tag = " [BINARY PARADOX]" if rec.special else ""
        guesses = ", ".join(
            f"{snap.players[pid].config.name}:{rec.actions.get(pid)}"
            for pid in snap.players)
        print(f"  R{rec.round}{tag} target={rec.target:>6}  {guesses}")
    print("  eliminations:", [
        f"{snap.players[e.payload['player_id']].config.name}@R{e.payload['round']}"
        for e in store.events(gid) if e.type == "player_eliminated"])
    winner = snap.players[snap.winner_id]
    print(f"  WINNER: {winner.config.name} ({snap.end_reason}), "
          f"{len(snap.rounds)} rounds")
    assert len([e for e in store.events(gid) if e.type == "player_eliminated"]) == 4
    paradoxes = [r for r in snap.rounds if r.special == "sudden_death_binary"]
    print(f"  paradox rounds: {[r.round for r in paradoxes]}")
    assert paradoxes, "elimination mode should trigger paradox rounds"
    for r in paradoxes:
        assert set(r.actions.values()) <= {0, 100}
    assert_isolation(store, gid)

    # Event replay must reconstruct an identical snapshot.
    replayed = store.reduce(gid)
    assert replayed.model_dump() == snap.model_dump()
    print("  ✓ event-log replay reproduces identical state")

    print("=== FIXED MODE (3 players, 3 rounds, all rules off) ===")
    from arena.schemas import DynamicRules
    rules = DynamicRules(duplicate_penalty=False, exact_match_bonus=False,
                         sudden_death_paradox=False)
    store2, _, gid2 = await run_game("fixed", n=3, rounds=3, rules=rules)
    snap2 = store2.get(gid2)
    assert snap2.status == "finished"
    assert len(snap2.rounds) == 3
    assert not any(r.special for r in snap2.rounds)
    print(f"  WINNER: {snap2.players[snap2.winner_id].config.name} "
          f"after {len(snap2.rounds)} rounds")
    print("  ✓ fixed mode respects round count and rule toggles")

    print("=== PAUSE / STEP ===")
    tmp = tempfile.mkdtemp()
    s3 = GameStore(tmp)
    m3 = GameMaster(s3)
    cfg3 = GameConfig(mode="fixed", rounds=4, round_delay=0, players=make_players(2))
    s3.create("g3", cfg3)
    await s3.emit("g3", "game_created", {
        "config": cfg3.model_dump(),
        "players": {pc.id: {"config": pc.model_dump()} for pc in cfg3.players}})
    await m3.step("g3")
    await asyncio.sleep(0.3)
    assert s3.get("g3").current_round == 1 and s3.get("g3").status == "paused"
    await m3.step("g3")
    await asyncio.sleep(0.3)
    assert s3.get("g3").current_round == 2
    print("  ✓ step mode advances exactly one round and re-pauses")
    print("\nALL SMOKE TESTS PASSED")


asyncio.run(main())
