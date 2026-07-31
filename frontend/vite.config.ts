import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Ohne diese Aufteilung landeten pdf.js (≈370 kB) und der
        // Arbeitsstands-Code in einem gemeinsamen Chunk: jede Änderung an
        // einem Werkzeug hätte den kompletten Viewer-Code neu ausgeliefert.
        // Getrennte Chunks bleiben über Releases hinweg im Browser-Cache.
        manualChunks(id: string) {
          if (id.includes('node_modules/pdfjs-dist')) return 'pdfjs'
          if (id.includes('node_modules/vue') || id.includes('node_modules/@vue')) return 'vue'
          return undefined
        },
      },
    },
    // Der pdf.js-Worker ist naturgemäß groß; die Warnschwelle würde sonst
    // bei jedem Build rauschen, ohne dass es etwas zu tun gäbe.
    chunkSizeWarningLimit: 700,
  },
  server: {
    port: 3010,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
