import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Mirrors the /api rewrite used in production (see vercel.json) so the
    // frontend can always call relative /api/* paths in both environments.
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        // Keep the browser's Host (localhost:5173) so the backend builds the
        // Google OAuth redirect_uri for the address the user is actually on.
        changeOrigin: false,
      },
    },
  },
})
