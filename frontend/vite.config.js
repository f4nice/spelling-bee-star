import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: '../app/static/vue',
    emptyOutDir: true,
    rollupOptions: {
      input: 'src/challenge/main.js',
      output: {
        entryFileNames: 'challenge-app.js',
        chunkFileNames: '[name].js',
        assetFileNames: '[name][extname]',
      },
    },
  },
});
