import { useState } from 'react'
import { api } from '../api.js'

export default function SettingsModal({ catalog, onClose, onSaved }) {
  const [keys, setKeys] = useState({})
  const [saved, setSaved] = useState({})
  const liveProviders = Object.values(catalog?.providers || {}).filter(
    (p) => p.kind !== 'mock'
  )
  const status = catalog?.status || {}

  async function save(provider) {
    try {
      const res = await api.setKey(provider, keys[provider] || '')
      setSaved({ ...saved, [provider]: true })
      onSaved?.(res.status)
      setKeys({ ...keys, [provider]: '' })
    } catch (e) {
      alert(e.message)
    }
  }

  return (
    <div className="modal-back" onClick={onClose}>
      <div className="panel modal modal-wrap" onClick={(e) => e.stopPropagation()}>
        <button className="close-x" onClick={onClose}>✕</button>
        <h2>⚿ Model Gateway — API Keys</h2>
        <p className="muted">
          Keys are held in the referee's memory only (never written to disk,
          never returned to the browser). Simulated personas need no keys.
        </p>
        {liveProviders.map((p) => {
          const st = status[p.id] || {}
          return (
            <div className="key-row" key={p.id}>
              <div className="nm">
                {p.label}
                <small>{p.docs}</small>
              </div>
              <input
                type="password"
                placeholder={st.configured ? `configured (${st.masked || '✓'})` : 'paste API key…'}
                value={keys[p.id] || ''}
                onChange={(e) => setKeys({ ...keys, [p.id]: e.target.value })}
              />
              <span className={`dot ${st.configured ? 'ok' : 'no'}`} title={st.source} />
              <button onClick={() => save(p.id)}>Save</button>
            </div>
          )
        })}
        <p className="hint">
          Environment variables (.env) are picked up automatically — the green
          dot shows either source. Models per provider are selected on the
          player roster.
        </p>
      </div>
    </div>
  )
}
