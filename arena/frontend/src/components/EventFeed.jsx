export default function EventFeed({ events, snap }) {
  const players = snap.players || {}
  const name = (pid) => players[pid]?.config?.name || pid
  const visible = events.filter((e) =>
    ['rule_injected', 'rule_retracted', 'round_resolved',
     'player_eliminated', 'notice', 'game_started', 'game_paused',
     'game_resumed', 'game_ended'].includes(e.type))
  const reversed = [...visible].reverse()

  return (
    <div className="panel">
      <h2>📜 Arena Feed</h2>
      <div className="feed">
        {reversed.length === 0 && <p className="muted">The arena is quiet…</p>}
        {reversed.map((e) => {
          const p = e.payload
          if (e.type === 'rule_injected') {
            const r = p.rule
            return (
              <div className={`feed-item rule-${r.severity || 'warning'}`} key={e.seq}>
                <span className="r-tag">RULE · R{p.round ?? '?'}</span>
                <b>{r.title}</b>
                <div className="muted" style={{ marginTop: 4 }}>{r.description}</div>
              </div>
            )
          }
          if (e.type === 'rule_retracted') {
            return <div className="feed-item" key={e.seq}>
              <span className="r-tag">RULE</span>One-shot rule retired: {p.rule_id}.
            </div>
          }
          if (e.type === 'round_resolved') {
            return (
              <div className="feed-item" key={e.seq}>
                <span className="r-tag">RESOLVED · R{p.round}{p.special ? ' · BINARY PARADOX' : ''}</span>
                Target = <b>{Number(p.target).toFixed(2)}</b>
                <div className="round-strip">
                  {Object.entries(p.deltas || {}).map(([pid, d]) => (
                    <span className={`round-chip ${p.special ? 'binary' : ''}`} key={pid}>
                      {name(pid)}: {String(d.guess ?? d.action)} →{' '}
                      <b>{d.delta >= 0 ? '+' : ''}{Number(d.delta).toFixed(1)}</b>
                    </span>
                  ))}
                </div>
              </div>
            )
          }
          if (e.type === 'player_eliminated') {
            return (
              <div className="feed-item elimination" key={e.seq}>
                ☠ <b>{name(p.player_id)}</b> was eliminated after round {p.round}.
                <div className="muted" style={{ fontWeight: 400 }}>{p.reason}</div>
              </div>
            )
          }
          if (e.type === 'notice') {
            return (
              <div className={`feed-item ${p.severity === 'danger' ? 'rule-danger' : ''}`} key={e.seq}>
                <span className="r-tag">REFEREE</span>{p.message}
              </div>
            )
          }
          if (e.type === 'game_ended') {
            return (
              <div className="feed-item elimination" key={e.seq}>
                🏁 Game over — <b>{p.winner_id ? name(p.winner_id) : 'no winner'}</b> wins
                ({p.reason}).
              </div>
            )
          }
          if (e.type === 'game_started')
            return <div className="feed-item rule-core" key={e.seq}><span className="r-tag">ARENA</span>The match begins.</div>
          if (e.type === 'game_paused')
            return <div className="feed-item" key={e.seq}><span className="r-tag">ARENA</span>Paused by the operator.</div>
          if (e.type === 'game_resumed')
            return <div className="feed-item" key={e.seq}><span className="r-tag">ARENA</span>Play resumes.</div>
          return null
        })}
      </div>
    </div>
  )
}
