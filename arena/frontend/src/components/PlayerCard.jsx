const COLORS = ['#ff2e63', '#08d9d6', '#9d4edd', '#3ddc97', '#ffc857', '#5b8def']

export default function PlayerCard({ ps, index, currentRound }) {
  const p = ps.config
  const color = COLORS[index % COLORS.length]
  const dead = ps.status === 'eliminated'
  const currentGuess = ps.last_action
  const reasoning = ps.last_reasoning
  const err = ps.last_error
  const log = (ps.reasoning_log || []).slice(0, -1).reverse()

  return (
    <div className={`card ${dead ? 'dead' : ''} ${ps.thinking ? 'thinking' : ''}`}>
      <div className="card-head">
        <div className="av" style={{ background: color }}>{p.name[0] || '?'}</div>
        <div className="nm">
          <b>{p.name}</b>
          <small>
            {p.provider === 'mock' ? 'simulated' : p.provider} · {p.model}
            {dead && ps.eliminated_round ? ` · ☠ eliminated R${ps.eliminated_round}` : ''}
          </small>
        </div>
        <div className="card-score" title="cumulative penalty (lower = better)">
          {ps.score.toFixed(1)}
        </div>
      </div>

      {!dead && (
        <div className="card-action">
          <span>R{currentRound} move</span>
          <b>{ps.thinking ? '…' : (currentGuess ?? '—')}</b>
        </div>
      )}

      <div className={`card-think ${err || ps.thinking ? '' : ''}`}>
        {ps.thinking ? (
          <span><span className="spinner" /><span className="lbl">Private reasoning</span>
            {p.name} is calculating…</span>
        ) : reasoning ? (
          <>
            <span className={`lbl ${err ? '' : ''}`} style={{ color: err ? undefined : undefined }}>
              {err || ps.reasoning_log?.at(-1)?.fallback ? '⚠ Referee report' : 'Private reasoning (rivals cannot see this)'}
            </span>
            {reasoning}
          </>
        ) : (
          <span className="muted">Awaiting the arena…</span>
        )}
      </div>

      {log.length > 0 && (
        <details>
          <summary>▸ Reasoning archive ({log.length})</summary>
          {log.map((e, i) => (
            <div className="history-entry" key={i}>
              <div className="h-hd">
                ROUND {e.round} · PLAYED {String(e.action)} · {e.latency_ms}ms
                {e.fallback ? ' · FALLBACK' : ''}
              </div>
              <div className="h-bd">{e.reasoning}</div>
            </div>
          ))}
        </details>
      )}
    </div>
  )
}
