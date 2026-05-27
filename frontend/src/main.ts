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

app.mount('#app')
