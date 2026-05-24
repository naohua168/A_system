/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

declare module 'vue-echarts' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<any, any, any>
  export default component
}

// ============================================================
// Vite 环境变量类型声明
// ============================================================
interface ImportMetaEnv {
  /** Vite 开发服务器端口 */
  readonly VITE_PORT?: string
  /** WebSocket 连接地址（开发环境指向后端端口） */
  readonly VITE_WS_HOST?: string
  /** API 基础路径 */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
