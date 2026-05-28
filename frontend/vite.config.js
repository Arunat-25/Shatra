import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const API_HOST = process.env.API_HOST || 'localhost:8000'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'node',
  },
  server: {
    proxy: {
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