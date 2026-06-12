import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import viteCompression from 'vite-plugin-compression'

const API_HOST = process.env.API_HOST || 'localhost:8000'

export default defineConfig({
  plugins: [
    react(),
    viteCompression({ algorithm: 'gzip', ext: '.gz' }),
  ],
  optimizeDeps: {
    include: ['recharts', 'react-is'],
  },
  test: {
    environment: 'happy-dom',
    exclude: ['**/node_modules/**', '**/dist/**', 'e2e/**'],
    setupFiles: ['./src/test/setup.js'],
  },
  server: {
    proxy: {
      '/api': {
        target: `http://${API_HOST}`,
        changeOrigin: true,
      },
      '/rooms': {
        target: `http://${API_HOST}`,
        changeOrigin: true,
      },
      '/ws': {
        target: `ws://${API_HOST}`,
        ws: true,
      },
    },
  },
})