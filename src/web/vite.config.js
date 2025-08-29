import { defineConfig } from 'vite'
import { resolve } from 'path'
import tailwindcss from 'tailwindcss'
import autoprefixer from 'autoprefixer'

export default defineConfig({
  root: resolve(process.cwd(), 'static/src'),
  base: '/static/',
  build: {
    outDir: resolve(process.cwd(), 'static/dist'),
    rollupOptions: {
      input: {
        main: resolve(process.cwd(), 'static/src/js/main.js'),
        styles: resolve(process.cwd(), 'static/src/css/main.css')
      },
      output: {
        entryFileNames: 'assets/js/[name]-[hash].js',
        chunkFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: 'assets/[ext]/[name]-[hash].[ext]'
      }
    },
    minify: 'terser',
    sourcemap: true
  },
  server: {
    port: 8097,
    proxy: {
      '/api': {
        target: 'http://localhost:8094',
        changeOrigin: true
      },
      '/ws': {
        target: 'http://localhost:8094',
        ws: true
      }
    }
  },
  css: {
    postcss: {
      plugins: [
        tailwindcss,
        autoprefixer
      ]
    }
  },
  plugins: [],
  resolve: {
    alias: {
      '@': resolve(process.cwd(), 'static/src'),
      '@components': resolve(process.cwd(), 'static/src/js/components'),
      '@services': resolve(process.cwd(), 'static/src/js/services'),
      '@utils': resolve(process.cwd(), 'static/src/js/core')
    }
  }
})
