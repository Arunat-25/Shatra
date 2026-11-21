import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import viteCompression from 'vite-plugin-compression'
import { VitePWA } from 'vite-plugin-pwa'
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
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'sounds/**/*.ogg', 'icons/**/*.png'],
      manifest: {
        name: 'Шатра — Алтайская народная игра',
        short_name: 'Шатра',
        description: 'Онлайн-версия алтайской настольной игры «Шатра»',
        lang: 'ru',
        start_url: '/',
        scope: '/',
        display: 'standalone',
        background_color: '#F0E8D3',
        theme_color: '#F0E8D3',
        icons: [
          { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: '/icons/maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        // Прекэш сборки и статических ресурсов: хотсит играбелен офлайн.
        globPatterns: ['**/*.{js,css,html,svg,png,ogg,woff2}'],
        navigateFallback: '/index.html',
        runtimeCaching: [
          {
            // Динамика игры и REST — только онлайн, кэш не отвечает.
            urlPattern: ({ url }) => url.pathname.startsWith('/ws/') || url.pathname.startsWith('/rooms'),
            handler: 'NetworkOnly',
          },
        ],
      },
    }),
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