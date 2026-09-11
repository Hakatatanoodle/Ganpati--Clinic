import { useState } from 'react'
import { api } from '../api.js'

const AVATAR_COLORS = ['#ff2e63', '#08d9d6', '#9d4edd', '#3ddc97', '#ffc857', '#5b8def']
const INITIAL = [
  { name: 'Grok', provider: 'mock', model: 'grok-sim' },
  { name: 'ChatGPT', provider: 'mock', model: 'chatgpt-sim' },
  { name: 'Claude', provider: 'mock', model: 'claude-sim' },
  { name: 'Gemini', provider: 'mock', model: 'gemini-sim' },
  { name: 'DeepSeek', provider: 'mock', model: 'deepseek-sim' },
]

export default function Setup({ catalog, onLaunched, onOpenSettings, pastGames }) {
  const [players, setPlayers] = useState(INITIAL)
  const [mode, setMode] = useState('elimination')
  const [rounds, setRounds] = useState(5)
  const [factor, setFactor] = useState(0.8)
  const [elimEvery, setElimEvery] = useState(2)
  const [delay, setDelay] = useState(2.5)
  const [rules, setRules] = useState({
    duplicate_penalty: true,
    exact_match_bonus: true,
    sudden_death_paradox: true,
  })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const providers = Object.values(catalog?.providers || {})
  const personas = catalog?.personas || {}
  const keyStatus = catalog?.status || {}

  function setPlayer(i, patch) {
    const next = players.slice()
    next[i] = { ...next[i], ...patch }
    setPlayers(next)
  }

  function onProvider(i, provider) {
    const prof = providers.find((p) => p.id === provider)
    const model = provider === 'mock'
      ? Object.keys(personas)[i % Math.max(1, Object.keys(personas).length)]
      : prof?.default_model || ''
    setPlayer(i, { provider, model })
  }

  function modelOptions(p) {
    if (p.provider === 'mock') {
      return Object.entries(personas).map(([id, per]) => ({ id, label: per.label }))
    }
    const prof = providers.find((x) => x.id === p.provider)
    return (prof?.models || []).map((m) => ({ id: m, label: m }))
  }

  async function launch() {
    setErr('')
    if (players.length < 2) return setErr('Need at least 2 combatants.')
    const names = players.map((p) => p.name.trim())
    if (names.some((n) => !n)) return setErr('Every combatant needs a name.')
    if (new Set(names).size !== names.length) return setErr('Combatant names must be unique.')
    for (const p of players) {
      if (p.provider !== 'mock' && !keyStatus[p.provider]?.configured) {
        return setErr(`${p.name}: add an API key for ${p.provider} in Settings first.`)
      }
    }
    setBusy(true)
    try {
      const config = {
        game_type: 'beauty_contest',
        mode, rounds: Number(rounds), factor: Number(factor),
        eliminate_every: Number(elimEvery), round_delay: Number(delay),
        dynamic_rules: rules,
        players: players.map((p) => ({
          name: p.name.trim(),
          provider: p.provider,
          model: p.model,
          persona: p.provider === 'mock' ? p.model : '',
        })),
      }
      const { game_id } = await api.createGame(config)
      await api.command(game_id, 'start')
      onLaunched(game_id)
    } catch (e) {
      setErr(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <div className="panel">
        <h2>♟ Choose the Battlefield</h2>
        <p className="muted" style={{ marginBottom: 14 }}>
          <b>Keynesian Beauty Contest</b> — secretly guess a number in [0, 100].
          Target = factor × mean of all guesses; your penalty is your distance
          to the target. Hyper-rational models spiral toward the 0 focal point…
          then the dynamic rules hit.
        </p>
        <div className="grid3">
          <label className="field">Game mode
            <select value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="elimination">Elimination — execute the worst, last one standing</option>
              <option value="fixed">Fixed rounds — lowest total penalty wins</option>
            </select>
          </label>
          <label className="field">{mode === 'elimination' ? 'Safety round cap' : 'Rounds'}
            <input type="number" min="1" max="24" value={rounds}
              onChange={(e) => setRounds(e.target.value)} />
          </label>
          <label className="field">Factor (target = factor × mean)
            <input type="number" step="0.05" min="0.1" max="1.5" value={factor}
              onChange={(e) => setFactor(e.target.value)} />
          </label>
          {mode === 'elimination' && (
            <label className="field">Elimination checkpoint (every N rounds)
              <input type="number" min="1" max="6" value={elimEvery}
                onChange={(e) => setElimEvery(e.target.value)} />
            </label>
          )}
          <label className="field">Spectator pacing (seconds / round)
            <input type="number" step="0.5" min="0" max="20" value={delay}
              onChange={(e) => setDelay(e.target.value)} />
          </label>
        </div>
        <div className="sec-title">Dynamic Rule Injections</div>
        <div className="grid3">
          <label className="checkbox">
            <input type="checkbox" checked={rules.duplicate_penalty}
              onChange={(e) => setRules({ ...rules, duplicate_penalty: e.target.checked })} />
            <span>Duplicate Collision Rule
              <small>After round 1: identical guesses each cost +10.</small></span>
          </label>
          <label className="checkbox">
            <input type="checkbox" checked={rules.exact_match_bonus}
              onChange={(e) => setRules({ ...rules, exact_match_bonus: e.target.checked })} />
            <span>Bullseye Bonus
              <small>After round 2: hitting the target within 0.5 pays −15.</small></span>
          </label>
          <label className="checkbox">
            <input type="checkbox" checked={rules.sudden_death_paradox}
              onChange={(e) => setRules({ ...rules, sudden_death_paradox: e.target.checked })} />
            <span>Sudden-Death 0 vs 100 Paradox
              <small>After each elimination: next round is binary {`{0,100}`}.</small></span>
          </label>
        </div>
      </div>

      <div className="panel">
        <h2>☠ Select the Combatants</h2>
        {players.map((p, i) => {
          const prof = providers.find((x) => x.id === p.provider)
          const configured = p.provider === 'mock' || keyStatus[p.provider]?.configured
          return (
            <div className="player-row" key={i}>
              <div className="badge" style={{ background: AVATAR_COLORS[i % 6] }}>
                {p.name[0] || '?'}
              </div>
              <input value={p.name} placeholder="Callsign"
                onChange={(e) => setPlayer(i, { name: e.target.value })} />
              <select value={p.provider} onChange={(e) => onProvider(i, e.target.value)}>
                {providers.map((pr) => (
                  <option value={pr.id} key={pr.id}>{pr.label}</option>
                ))}
              </select>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <input list={`models-${i}`} value={p.model}
                  onChange={(e) => setPlayer(i, { model: e.target.value })}
                  placeholder="model id" />
                <datalist id={`models-${i}`}>
                  {modelOptions(p).map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
                </datalist>
                <span className={`dot ${configured ? 'ok' : 'no'}`}
                  title={configured ? 'ready' : 'API key missing'} />
              </div>
              <button className="del"
                disabled={players.length <= 2}
                onClick={() => setPlayers(players.filter((_, j) => j !== i))}>✕</button>
            </div>
          )
        })}
        <div className="row" style={{ marginTop: 12 }}>
          <button className="ghost"
            disabled={players.length >= 6}
            onClick={() => setPlayers([...players, { name: '', provider: 'mock', model: 'chatgpt-sim' }])}>
            ＋ Add combatant
          </button>
          <button className="ghost" onClick={onOpenSettings}>⚿ API Keys</button>
        </div>
        <div className="hint">
          Simulated personas (DeepSeek = deep level-k, Claude = cautious, ChatGPT = balanced,
          Gemini = empirical, Grok = chaotic bluffer) play a full match with no keys.
          Switch a row to a live model once its key is set.
        </div>
      </div>

      {pastGames?.length > 0 && (
        <div className="panel">
          <h2>⏱ Recent Matches</h2>
          <div className="round-strip">
            {pastGames.map((g) => (
              <button className="round-chip" key={g.game_id} onClick={() => onLaunched(g.game_id)}>
                {g.game_id.slice(0, 5)} · {g.players.join(', ')} ·{' '}
                <b>{g.status}</b>{g.winner_id ? '' : ` R${g.round}`}
              </button>
            ))}
          </div>
        </div>
      )}

      {err && <p className="error-line">⚠ {err}</p>}
      <div style={{ textAlign: 'center', margin: '24px 0' }}>
        <button className="primary" onClick={launch} disabled={busy}>
          {busy ? 'Summoning the players…' : '▶ Begin the Game'}
        </button>
      </div>
    </div>
  )
}
