export default function Scoreboard({ snap }) {
  const standings = [...Object.values(snap.players || {})].sort((a, b) => {
    if (a.status !== b.status) return a.status === 'alive' ? -1 : 1
    return a.score - b.score || a.config.name.localeCompare(b.config.name)
  })
  const leader = standings.find((p) => p.status === 'alive')?.config.id

  return (
    <div className="panel" style={{ marginBottom: 18 }}>
      <h2>⛳ Scoreboard</h2>
      <p className="muted" style={{ fontSize: 11, marginBottom: 10 }}>
        Cumulative penalty — lowest leads
      </p>
      {standings.map((ps, i) => (
        <div key={ps.config.id}
          className={`sb-row ${ps.status === 'eliminated' ? 'dead' : ''} ${ps.config.id === leader ? 'leader' : ''}`}>
          <span className="sb-rank">{ps.status === 'eliminated' ? '☠' : i + 1}</span>
          <span className="sb-name">
            {ps.config.name}
            <small>{ps.config.provider === 'mock' ? 'simulated' : ps.config.provider} · {ps.config.model}</small>
          </span>
          <span className="sb-score">{ps.score.toFixed(1)}</span>
        </div>
      ))}
    </div>
  )
}
