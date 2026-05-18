import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'happy-dom',
    environmentOptions: {
      happyDOM: {
        url: 'http://localhost:3000'
      }
    },
    globals: true,
    setupFiles: ['./src/__tests__/setup.js']
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  }
})
