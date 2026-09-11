// Thin REST helper for the arena backend.
async function req(path, options = {}) {
  const resp = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!resp.ok) {
    let detail = resp.statusText
    try {
      detail = (await resp.json()).detail || detail
    } catch {}
    throw new Error(detail)
  }
  return resp.json()
}

export const api = {
  catalog: () => req('/api/providers'),
  gamesCatalog: () => req('/api/games-catalog'),
  listGames: () => req('/api/games'),
  getGame: (id) => req(`/api/games/${id}`),
  createGame: (config) =>
    req('/api/games', { method: 'POST', body: JSON.stringify(config) }),
  command: (id, command, body) =>
    req(`/api/games/${id}/${command}`, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    }),
  setKey: (provider, key) =>
    req('/api/keys', { method: 'POST', body: JSON.stringify({ provider, key }) }),
}

// Live event socket with snapshot bootstrap and polling fallback.
export function connectGame(gameId, { onSnapshot, onEvent, onStatus }) {
  let ws = null
  let poll = null
  let closed = false
  let retries = 0
  let polledSeq = -1

  async function pollOnce() {
    try {
      const snap = await api.getGame(gameId)
      onSnapshot(snap)
      const ev = await fetch(`/api/games/${gameId}/events?after=${snap.event_count - 1}`)
        .then((r) => r.json())
      for (const e of ev.events || []) onEvent(e)
    } catch {}
  }

  function connect() {
    if (closed) return
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    ws = new WebSocket(`${proto}://${location.host}/api/ws/games/${gameId}`)
    onStatus?.('connecting')
    ws.onopen = () => {
      retries = 0
      onStatus?.('live')
      if (poll) { clearInterval(poll); poll = null }
    }
    ws.onmessage = (m) => {
      const msg = JSON.parse(m.data)
      if (msg.type === 'snapshot') onSnapshot(msg.snapshot)
      if (msg.type === 'event') onEvent(msg.event)
    }
    ws.onclose = () => {
      if (closed) return
      onStatus?.('replaying')
      pollOnce()
      poll = poll || setInterval(pollOnce, 1200)
      retries += 1
      setTimeout(connect, Math.min(8000, 800 * retries))
    }
    ws.onerror = () => ws?.close()
  }

  connect()
  return () => {
    closed = true
    ws?.close()
    if (poll) clearInterval(poll)
  }
}
