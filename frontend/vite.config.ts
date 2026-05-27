import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import vitePluginCompression from 'vite-plugin-compression'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    // 生产环境下启用 gzip/brotli 压缩
    vitePluginCompression({ algorithm: 'gzip', ext: '.gz' }),
    vitePluginCompression({ algorithm: 'brotliCompress', ext: '.br' }),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8082',
        changeOrigin: true,
      },
      // WebSocket 代理 — Vite 开发服务器将 /ws 请求转发到后端
      '/ws': {
        target: 'ws://localhost:8082',
        ws: true,
        changeOrigin: true,
      },
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@use "@/styles/variables.scss" as *;\n`,
      },
    },
  },
  build: {
    // 生产环境分包优化 — 将第三方库拆分为独立 chunk，利用浏览器并行加载
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-vue': ['vue', 'vue-router', 'pinia'],           // Vue 全家桶
          'vendor-ui': ['element-plus', '@element-plus/icons-vue'], // UI 组件库
          'vendor-chart': ['echarts', 'vue-echarts'],               // 图表库
          'vendor-axios': ['axios'],                                 // HTTP 客户端
        },
      },
    },
    // 构建产物的 chunk 大小警告阈值（超过 500KB 会告警）
    chunkSizeWarningLimit: 500,
    // 启用 CSS 代码分割
    cssCodeSplit: true,
    // 生产环境使用 esbuild 压缩（内置，无需额外依赖）
    minify: 'esbuild',
  },
})
