import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const apiProxy = {
  '/api': 'http://localhost:5000',
};

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    strictPort: true,
    proxy: apiProxy,
    open: false,
  },
  // `npm run start` uses `vite preview`, which does not inherit `server.proxy` unless mirrored here.
  preview: {
    port: 3000,
    strictPort: true,
    proxy: apiProxy,
  },
});