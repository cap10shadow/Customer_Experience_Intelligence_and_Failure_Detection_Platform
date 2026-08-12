import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '0.0.0.0',
    // Must match docker-compose.yml's frontend port mapping
    // ("${FRONTEND_PORT:-3000}:3000") -- Vite's own default (5173) doesn't,
    // which otherwise makes the container unreachable at localhost:3000
    // as compose maps it.
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://gateway_service:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/tests/setup.ts'],
    css: true,
  },
})
