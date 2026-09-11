import { useEffect, useState } from 'react'
import { api } from './api.js'
import Setup from './components/Setup.jsx'
import Arena from './components/Arena.jsx'
import SettingsModal from './components/SettingsModal.jsx'

export default function App() {
  const [catalog, setCatalog] = useState(null)
  const [pastGames, setPastGames] = useState([])
  const [gameId, setGameId] = useState(null)
  const [settings, setSettings] = useState(false)

  async function refreshCatalog() {
    const c = await api.catalog()
    setCatalog(c)
  }
  async function refreshGames() {
    const g = await api.listGames()
    setPastGames(g.games.slice(-8).reverse())
  }

  useEffect(() => {
    refreshCatalog()
    refreshGames()
  }, [gameId])

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="spade">♠</span>
          <div>
            <h1>Multi-LLM Arena</h1>
            <small>Autonomous AI Game Referee &amp; Spectator Platform</small>
          </div>
        </div>
        <div className="top-actions">
          <button className="ghost" onClick={() => setSettings(true)}>⚿ API Keys</button>
          {gameId && <button className="ghost" onClick={() => setGameId(null)}>⌂ Lobby</button>}
        </div>
      </header>

      {gameId ? (
        <Arena gameId={gameId}
          onExit={() => { setGameId(null); refreshGames() }}
          onOpenSettings={() => setSettings(true)} />
      ) : (
        <Setup catalog={catalog}
          pastGames={pastGames}
          onLaunched={(id) => setGameId(id)}
          onOpenSettings={() => setSettings(true)} />
      )}

      {settings && (
        <SettingsModal catalog={catalog}
          onClose={() => { setSettings(false); refreshCatalog() }}
          onSaved={(status) => setCatalog({ ...catalog, status })} />
      )}

      <footer className="muted" style={{ textAlign: 'center', marginTop: 40, fontSize: 11 }}>
        No human messenger. The referee fans out isolated prompts, scores the
        math, injects the rules, and executes the condemned.
      </footer>
    </div>
  )
}
