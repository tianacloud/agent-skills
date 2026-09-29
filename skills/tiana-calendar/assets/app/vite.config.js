import { defineConfig } from 'vite';
export default defineConfig({
  define: { 'process.env.NODE_ENV': JSON.stringify('production') },
  build: {
    lib: { entry: 'src/main.js', formats: ['es'], fileName: 'assets/app', cssFileName: 'assets/app' },
    outDir: 'dist',
    emptyOutDir: true,
  },
});
