import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tsconfigPaths from "vite-tsconfig-paths";

// https://vite.dev/config/
export default defineConfig({
  build: {
    outDir: '../static',
    emptyOutDir: true,
    sourcemap: false,
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8765',
    },
  },
  plugins: [react(), tsconfigPaths()],
})
