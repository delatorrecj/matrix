import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/vitest.setup.ts'],
    globals: true,
    include: ['tests/unit/**/*.{test,spec}.?(c|m)[jt]s?(x)'],
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
