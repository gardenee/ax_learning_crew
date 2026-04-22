import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Docker (특히 macOS) bind-mount 는 inotify 이벤트가 전달되지 않아 HMR 이 죽는다.
// 해결: chokidar polling 강제 + HMR websocket 을 호스트 퍼블리시 포트로 재연결.
const clientPort = Number(process.env.WEB_HMR_CLIENT_PORT ?? process.env.WEB_PORT ?? 3000)

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    host: '0.0.0.0',
    watch: {
      usePolling: true,
      interval: 300,
    },
    hmr: {
      host: 'localhost',
      clientPort,
    },
    proxy: {
      '/api': {
        target: 'http://api:8000',
        changeOrigin: true,
      },
    },
  },
})
