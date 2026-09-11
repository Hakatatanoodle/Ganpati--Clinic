import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev mode proxies API + WebSocket to the FastAPI game master (uvicorn on :8000).
// Production: `npm run build` emits to dist/, which FastAPI serves directly.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/ws': { target: 'ws://127.0.0.1:8000', ws: true }
    }
  },
  build: { outDir: 'dist' }
})
