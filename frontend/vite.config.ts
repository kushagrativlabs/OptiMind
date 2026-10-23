import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    allowedHosts: process.env.VITE_ALLOWED_HOSTS
      ? process.env.VITE_ALLOWED_HOSTS.split(',').map((host) => host.trim()).filter(Boolean)
      : undefined,
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        // Keep the proxy on the same IPv4 loopback address as Uvicorn.
        // On some systems `localhost` resolves to IPv6 first, which makes
        // the UI appear offline even while the API is healthy.
        target: process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})

