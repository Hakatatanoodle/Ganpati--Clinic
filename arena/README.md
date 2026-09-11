# ♠ Multi-LLM Arena — Autonomous AI Game Referee & Spectator Platform

An autonomous, multi-agent game-theory arena. Frontier models (Gemini,
ChatGPT, DeepSeek, Grok, Claude) face off in high-stakes strategy games while
a **Game Master engine** replaces the human messenger: it fans out isolated
prompts in parallel, does all the math, tracks scores, injects dynamic rules
on eliminations, detects endgame, and streams every player's private
reasoning to a spectator dashboard.

The flagship game is the **Keynesian Beauty Contest** ("guess 0.8 × the
average"), where hyper-rational models spiral into the 0 focal point,
identical models destroy each other on symmetric equilibria, and sudden rule
changes force instant psychological adaptation.

---

## Quick start

```bash
cd arena
./run.sh                     # installs deps, builds UI, serves on :8000
# open http://localhost:8000
```

Manual equivalents:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
.venv/bin/uvicorn --app-dir backend main:app --host 0.0.0.0 --port 8000
```

Frontend dev mode with hot reload (run both):

```bash
.venv/bin/uvicorn --app-dir backend main:app --reload --port 8000
cd frontend && npm run dev    # http://localhost:5173 (API/WS proxied)
```

**No API keys are required to play** — five simulated model personas
(level-k reasoners with distinct personalities) run complete matches. Add
real keys via the dashboard **⚿ API Keys** modal, or a `.env` file
(`.env.example` provided), then switch players to live models.

## The spectator experience

1. **Lobby** — pick the mode (elimination / fixed rounds), the factor, the
   dynamic-rule toggles, pacing, and the combatant roster (callsign,
   provider, model id).
2. **Begin the Game** — the referee takes over. Cards show each model's
   private chain of thought *live* ("thinking…" spinners included), the
   move it commits, latency and token stats, and a full per-player reasoning
   archive.
3. Watch the **scoreboard** update, dynamic rules get injected over the
   arena feed, eliminations execute, and paradox rounds detonate.
4. Pause/resume, single-step rounds, or change pacing at any time. Finished
   matches stay in the lobby's recent-matches list.

## The Beauty Contest rules

* Every alive player privately picks an integer in `[0, 100]`.
* `target = factor × mean(guesses)`; round penalty = `|guess − target|`.
* Penalties accumulate; **lowest total wins**.

Dynamic injections (toggleable, timing is by round/elimination event):

| Rule | Trigger | Effect |
|---|---|---|
| Duplicate Collision | after round 1 | players submitting identical guesses each take **+10** |
| Bullseye Bonus | after round 2 | a guess within 0.5 of target pays **−15** |
| Sudden-Death 0 vs 100 Paradox | after every elimination | the *next* round allows **only {0, 100}**. With `q` the share choosing 100, target = `80q`; choosing 0 costs `80q`, choosing 100 costs `|100−80q|`; the best response **flips at q = 0.625** — pure coordination/bluff warfare |

In **elimination mode** the highest cumulative penalty is executed at
checkpoints (every N rounds) until one model stands; **fixed mode** runs a
set number of rounds.

## Architecture

```
arena/
├── backend/
│   ├── main.py                  # FastAPI app; serves API, WS and the built SPA
│   ├── config.py                # provider profiles + write-only API key vault
│   ├── api/routes.py            # REST + /api/ws/games/{id}
│   └── arena/
│       ├── engine.py            # THE GAME MASTER: autopilot loop, fan-out,
│       │                        #   validation/repair/fallback, pause/step
│       ├── perception.py        # INFORMATION ISOLATION: per-player view builder
│       ├── store.py             # EVENT-SOURCED state: append-only JSONL + reducer
│       ├── events.py            # pub/sub bus for live WebSockets
│       ├── schemas.py           # config / events / state snapshots (Pydantic)
│       ├── gateway/
│       │   ├── base.py          # unified ModelGateway interface + JSON parser
│       │   ├── openai_compat.py # OpenAI, DeepSeek, xAI Grok, Gemini-compat
│       │   ├── anthropic.py     # native Claude Messages API
│       │   ├── mock.py          # 5 simulated level-k personas (keyless play)
│       │   └── registry.py
│       └── games/
│           ├── base.py          # GamePlugin contract
│           ├── beauty_contest.py
│           └── registry.py
├── frontend/                    # React + Vite spectator dashboard
└── arena_data/games/*.jsonl     # append-only match logs (gitignored)
```

### Core guarantees

* **Information isolation** — `perception.build_player_view()` is the only
  path by which game state reaches a player. A view contains public rules,
  the public scoreboard, public action history, public announcements, and
  that player's *own* reasoning log — never another player's reasoning,
  prompt, or raw output. Each LLM call gets a freshly rendered, stateless
  prompt (no shared conversation), and reasoning is fanned out to
  spectators only. `smoke_test.py` asserts zero leakage for every round.
* **Bulletproof state** — every mutation is an append-only event, mirrored
  to `arena_data/games/<id>.jsonl`. State is a pure reduction of the log;
  replay is byte-for-byte identical (asserted in the smoke test), so
  interrupted matches survive restarts and every match is fully auditable.
* **Never stalls** — per-player timeouts, structured-JSON parsing with
  repair retries, and a deterministic default move with a +10 violation
  penalty mean a dead/keyless/malformed model can never freeze the game;
  its failure is narrated on its spectator card.
* **Parallel fan-out** — all alive players are prompted concurrently
  (`asyncio.gather`); results resolve into one deterministic scoring pass.

### Model gateway

Every provider returns the same `ModelResponse(reasoning, action, tokens,
latency, …)`:

| Provider | Adapter | Env / key name |
|---|---|---|
| Simulated personas | `mock.py` (no key) | — |
| OpenAI (ChatGPT) | OpenAI-compatible | `OPENAI_API_KEY` |
| DeepSeek | OpenAI-compatible | `DEEPSEEK_API_KEY` |
| xAI (Grok) | OpenAI-compatible | `XAI_API_KEY` |
| Google (Gemini) | OpenAI-compatibility endpoint | `GEMINI_API_KEY` |
| Anthropic (Claude) | native Messages adapter | `ANTHROPIC_API_KEY` |

Runtime keys from the Settings modal live in memory only; env keys are the
fallback. The dashboard never receives key values — only masked
availability.

## Adding a new game

One file, `backend/arena/games/your_game.py`, implementing the `GamePlugin`
contract in `games/base.py`:

* `initial_state` / `intro_rules` — private state and opening rulebook;
* `plan_round` — declare the round's action spec (number range, discrete
  choices, …) and any rule injections/retractions;
* `coerce_action` — validate/parse raw model output;
* `resolve_round` — pure function from snapshot + actions → scores,
  line items, injections, eliminations, winner;
* `build_prompts` — render a system/user prompt from the isolated view.

Then register it in `games/registry.py`. The engine, gateway, perception
layer, event log, WebSockets and dashboard all work unchanged.

## Testing

```bash
.venv/bin/python backend/smoke_test.py
```

Runs a 5-player elimination match and a fixed match headlessly, asserts the
elimination schedule, paradox binary rounds, pause/step semantics,
cross-player reasoning isolation, and event-log replay equality.
