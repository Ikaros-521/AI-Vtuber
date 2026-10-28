import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// 开发期：vite 5173，/api 与旧兼容接口代理到本地的 webui_server（默认 8082）
const backend = process.env.WEBUI_V3_PORT || '8082'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': `http://127.0.0.1:${backend}`,
      '/callback': `http://127.0.0.1:${backend}`,
      '/set_config': `http://127.0.0.1:${backend}`,
      '/sys_cmd': `http://127.0.0.1:${backend}`,
      '/send': `http://127.0.0.1:${backend}`,
    },
  },
})
