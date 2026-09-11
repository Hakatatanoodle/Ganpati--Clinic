import { useEffect, useMemo, useState } from 'react'
import { api, connectGame } from '../api.js'
import Scoreboard from './Scoreboard.jsx'
import EventFeed from './EventFeed.jsx'
import PlayerCard from './PlayerCard.jsx'

const AVATAR_ORDER = ['Grok', 'ChatGPT', 'Claude', 'Gemini', 'DeepSeek']

export default function Arena({ gameId, onExit, onOpenSettings }) {
  const [snap, setSnap] = useState(null)
  const [events, setEvents] = useState([])
  const [conn, setConn] = useState('connecting')
  const [speed, setSpeed] = useState(2.5)

  useEffect(() => {
    const evMap = new Map()
    const stop = connectGame(gameId, {
      onSnapshot: (s) => setSnap(s),
      onEvent: (e) => {
        evMap.set(e.seq, e)
        setEvents([...evMap.values()].sort((a, b) => a.seq - b.seq))
      },
      onStatus: setConn,
    })
    return stop
  }, [gameId])

  const cmd = async (c, body) => {
    const s = await api.command(gameId, c, body)
    setSnap(s)
  }

  const players = useMemo(() => {
    if (!snap) return []
    return Object.values(snap.players).sort(
      (a, b) =>
        (AVATAR_ORDER.indexOf(a.config.name) === -1 ? 99 : AVATAR_ORDER.indexOf(a.config.name))
        - (AVATAR_ORDER.indexOf(b.config.name) === -1 ? 99 : AVATAR_ORDER.indexOf(b.config.name)))
  }, [snap])

  if (!snap) return <div className="panel">Entering the arena…</div>

  const cfg = snap.config
  const cap = cfg.mode === 'fixed'
    ? cfg.rounds
    : Math.min(24, Math.max(cfg.rounds, (cfg.players.length - 1) * cfg.eliminate_every))
  const liveRound = snap.rounds.find((r) => !r.resolved)
  const paradox =
    liveRound?.special === 'sudden_death_binary' ||
    snap.plugin_state?.pending_special === 'sudden_death_binary'
  const winner = snap.winner_id ? snap.players[snap.winner_id] : null

  return (
    <div>
      <div className="panel" style={{ padding: '14px 20px' }}>
        <div className="stat-bar" style={{ marginBottom: 0 }}>
          <div>
            <div style={{ fontFamily: 'Orbitron', fontWeight: 800, letterSpacing: 1.5 }}>
              BEAUTY CONTEST
            </div>
            <div className="muted mono" style={{ fontSize: 11 }}>
              match {gameId} · {cfg.mode} · factor {cfg.factor}
            </div>
          </div>
          <span className={`pill ${snap.status}`}>{snap.status}</span>
          <span className={`pill ${conn}`}>{conn === 'live' ? '● live feed' : '◌ ' + conn}</span>
          <div className="stat">
            <div className="k">Round</div>
            <div className="v">{snap.current_round}<span className="muted" style={{ fontSize: 13 }}>/{cap}</span></div>
          </div>
          <div className="stat">
            <div className="k">Alive</div>
            <div className="v">{players.filter((p) => p.status === 'alive').length}</div>
          </div>
          <div style={{ flex: 1 }} />
          {snap.status === 'setup' && <button className="primary" onClick={() => cmd('start')}>▶ Start</button>}
          {snap.status === 'running' && <button onClick={() => cmd('pause')}>⏸ Pause</button>}
          {snap.status === 'paused' && (
            <>
              <button className="primary" onClick={() => cmd('resume')}>▶ Resume</button>
              <button onClick={() => cmd('step')}>⏭ Step</button>
            </>
          )}
          {snap.status === 'finished' && (
            <button className="primary" onClick={onExit}>↻ New Match</button>
          )}
          <label className="field" style={{ marginBottom: 0, minWidth: 170 }}>
            Pacing {speed}s
            <input type="range" min="0" max="10" step="0.5" value={speed}
              onChange={(e) => { setSpeed(Number(e.target.value)); cmd('speed', { delay: Number(e.target.value) }) }} />
          </label>
          <button className="ghost" onClick={onOpenSettings}>⚿</button>
          <button className="ghost" onClick={onExit}>✕ Exit</button>
        </div>
      </div>

      {winner && (
        <div className="banner">
          <div className="crown">👑</div>
          <h2>{winner.config.name} Wins</h2>
          <p>{snap.end_reason} · final penalty {winner.score.toFixed(1)}</p>
        </div>
      )}

      {paradox && (
        <div className="paradox-banner">
          ⚠ SUDDEN-DEATH PARADOX — LEGAL MOVES: ONLY 0 OR 100 ⚠
        </div>
      )}

      <div className="arena-grid">
        <div>
          <Scoreboard snap={snap} />
          <EventFeed events={events} snap={snap} />
        </div>
        <div>
          <div className="cards">
            {players.map((ps, i) => (
              <PlayerCard key={ps.config.id} ps={ps} index={i} currentRound={snap.current_round} />
            ))}
          </div>
          <div className="panel" style={{ marginTop: 18 }}>
            <h2>⌁ Active Rule Set</h2>
            {(snap.active_rules || []).length === 0 && <p className="muted">Core rules only.</p>}
            <div className="round-strip">
              {(snap.active_rules || []).map((r) => (
                <span key={r.id} className={`round-chip ${r.severity === 'danger' ? 'binary' : ''}`}>
                  {r.title.replace('DYNAMIC RULE INJECTED — ', '')}
                </span>
              ))}
            </div>
            <p className="hint" style={{ marginTop: 10 }}>
              Information isolation enforced: each player's prompt contains only
              the public scoreboard/history plus their own private state. The
              reasoning shown on cards is delivered to spectators only.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
