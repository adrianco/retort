import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [
    require('@tailwindcss/vite')()
  ],
  build: {
    outDir: '../priv/static',
    emptyOutDir: true
  }
})
