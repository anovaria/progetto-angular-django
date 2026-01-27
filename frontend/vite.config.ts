import { defineConfig } from 'vite';

export default defineConfig({
    server: {
        port: 4200,
        proxy: {
            '/api': {
                target: 'http://127.0.0.1:8002',
                changeOrigin: true,
                secure: false,
                configure: (proxy, options) => {
                    console.log('[PROXY] /api -> http://127.0.0.1:8002');
                }
            }
        }
    }
});