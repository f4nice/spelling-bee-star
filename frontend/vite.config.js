import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  base: '/static/vue/',
  plugins: [vue()],
  build: {
    outDir: '../app/static/vue',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        challenge: 'src/challenge/main.js',
        app: 'src/app/main.js',
      },
      output: {
        manualChunks(id) {
          if (id.includes('/node_modules/phaser/')) {
            return 'phaser-vendor';
          }
        },
        entryFileNames: (chunk) => (chunk.name === 'app' ? 'speakeasy-app.js' : 'challenge-app.js'),
        chunkFileNames: '[name]-[hash].js',
        assetFileNames: '[name][extname]',
      },
    },
  },
});
