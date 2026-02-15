import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      injectRegister: false,
      registerType: 'autoUpdate',
      workbox: {
        // Exclude large viewer chunks from precaching (they're lazy-loaded anyway)
        globPatterns: ['**/*.{js,css,ico,png,svg,woff2}'],
        globIgnores: ['**/pdf-viewer*.js', '**/xlsx-viewer*.js', '**/docx-viewer*.js'],
        maximumFileSizeToCacheInBytes: 3 * 1024 * 1024, // 3MB limit
        // Deny all routes from precache NavigationRoute so navigation
        // is handled only by the NetworkFirst runtime caching below.
        // This prevents serving stale index.html from precache on deploy.
        navigateFallbackDenylist: [/./],
        runtimeCaching: [
          {
            // Navigation requests (HTML pages) - serve from cache quickly when offline
            urlPattern: ({ request }) => request.mode === 'navigate',
            handler: 'NetworkFirst',
            options: {
              cacheName: 'html-cache',
              networkTimeoutSeconds: 2, // Short timeout for fast offline fallback
            }
          },
          {
            // Exclude /chat (SSE streaming) - only cache REST endpoints
            urlPattern: /^\/(?:jobs|conversations|artifacts)/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              networkTimeoutSeconds: 10
            }
          },
          {
            urlPattern: /\.(?:js|css|woff2?|png|jpg|svg)$/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'static-assets',
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 60 * 60 * 24 * 7 // 7 days
              }
            }
          }
        ],
        skipWaiting: true,
        clientsClaim: true
      },
      manifest: false // Use existing manifest.json
    })
  ],
  server: {
    port: 5173,
    host: true, // Expose to network for mobile testing
    allowedHosts: ['.ngrok-free.app', '.ngrok.io'],
    proxy: {
      // Proxy API endpoints to backend running in Docker (port 8000 in container → 18000 on host)
      '/chat': 'http://localhost:18000',
      '/jobs': 'http://localhost:18000',
      '/conversations': 'http://localhost:18000',
      '/artifacts': 'http://localhost:18000',
      '/apps': 'http://localhost:18000',
      '/health': 'http://localhost:18000',
      '/container': 'http://localhost:18000',
      '/scheduled-jobs': 'http://localhost:18000',
      '/integrations': 'http://localhost:18000',
      '/oauth': 'http://localhost:18000',
      '/auth': 'http://localhost:18000',  // JWT callback from central
      '/admin': 'http://localhost:18000',
      '/settings': 'http://localhost:18000',
      '/login': 'http://localhost:8080',
      '/register': 'http://localhost:8080',
      '/logout': 'http://localhost:8080'
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    target: 'es2020',
    rollupOptions: {
      output: {
        manualChunks: {
          'vue-core': ['vue', 'vue-i18n'],
          'tiptap': ['@tiptap/vue-3', '@tiptap/starter-kit', 'tiptap-markdown', '@tiptap/extension-placeholder'],
          'xlsx-viewer': ['xlsx'],
          'docx-viewer': ['mammoth'],
          'pdf-viewer': ['vue-pdf-embed'],
          'highlight': ['marked-highlight'],
          'markdown': ['marked', 'dompurify']
        }
      }
    }
  }
})
