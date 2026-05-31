import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import {
  Aim,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Bell,
  Bottom,
  ChatLineSquare,
  Check,
  Close,
  Coin,
  DataAnalysis,
  DataBoard,
  DataLine,
  Delete,
  Histogram,
  Minus,
  Monitor,
  Plus,
  Pointer,
  Search,
  Setting,
  Star,
  SwitchButton,
  Top,
  TrendCharts,
  Wallet,
  Warning,
  WarningFilled,
} from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import './styles/global.scss'

const app = createApp(App)

// Register used Element Plus icons only (reduce bundle from ~300 icons to ~28)
const registeredIcons = {
  Aim, ArrowDown, ArrowLeft, ArrowRight, Bell, Bottom, ChatLineSquare,
  Check, Close, Coin, DataAnalysis, DataBoard, DataLine, Delete,
  Histogram, Minus, Monitor, Plus, Pointer, Search, Setting, Star,
  SwitchButton, Top, TrendCharts, Wallet, Warning, WarningFilled,
}
for (const [key, component] of Object.entries(registeredIcons)) {
  app.component(key, component)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: undefined })

// 全局错误处理器：静默忽略布局测量类非致命异常
app.config.errorHandler = (err) => {
  const msg = String(err)
  if (/getBoundingClientRect|Script error|innerHTML/i.test(msg)) return
  console.error('[Vue Error]', err)
}

// 全局 window 错误拦截：静默忽略布局测量类异常
window.addEventListener('error', (e) => {
  const msg = String(e.error?.message || e.message || '')
  if (/getBoundingClientRect|Script error|ResizeObserver|innerHTML/i.test(msg)) {
    e.preventDefault()
    e.stopPropagation()
  }
})

// 全局未处理 Promise 拒绝拦截
window.addEventListener('unhandledrejection', (e) => {
  const msg = String(e.reason?.message || e.reason || '')
  if (/getBoundingClientRect|Script error|ResizeObserver|innerHTML/i.test(msg)) {
    e.preventDefault()
  }
})

app.mount('#app')
