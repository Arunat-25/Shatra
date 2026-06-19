import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import viteCompression from 'vite-plugin-compression'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const API_HOST = process.env.API_HOST || 'localhost:8000'
const rootDir = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  resolve: {
    alias: {
      '@shatra/rules': path.resolve(rootDir, 'packages/shatra-rules/src/index.js'),
    },
  },
  esbuild: {
    jsx: 'automatic',
  },
  plugins: [
    react({ jsxRuntime: 'automatic' }),
    viteCompression({ algorithm: 'gzip', ext: '.gz' }),
  ],
  optimizeDeps: {
    include: ['recharts', 'react-is'],
  },
  test: {
    environment: 'happy-dom',
    exclude: ['**/node_modules/**', '**/dist/**', 'e2e/**'],
    setupFiles: ['./src/test/setup.js'],
    include: ['src/**/*.test.{js,jsx}', 'packages/**/*.test.js'],
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