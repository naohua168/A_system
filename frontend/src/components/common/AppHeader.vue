<template>
  <header class="app-header">
    <div class="header-inner">
      <!-- Logo -->
      <router-link to="/home" class="logo">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <path d="M3 3V21H21" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
          <path d="M7 15L11 9L15 13L21 5" stroke="#1890FF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span class="logo-text">StockAI</span>
      </router-link>

      <!-- 导航栏 -->
      <nav class="main-nav">
        <!-- 主菜单项 -->
        <router-link
          v-for="item in mainNavItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
        >
          <component :is="item.icon" class="nav-icon" />
          <span>{{ item.label }}</span>
        </router-link>

        <!-- 数据中心下拉 -->
        <div class="nav-dropdown" @mouseenter="openDropdown = 'data'" @mouseleave="openDropdown = ''">
          <button class="nav-item" :class="{ active: openDropdown === 'data' || isSignalActive }">
            <el-icon class="nav-icon"><DataBoard /></el-icon>
            <span>数据中心</span>
            <el-icon class="dropdown-arrow" :class="{ open: openDropdown === 'data' }"><ArrowDown /></el-icon>
          </button>
          <transition name="dropdown-slide">
            <div v-if="openDropdown === 'data'" class="dropdown-panel" @mouseenter="openDropdown = 'data'" @mouseleave="openDropdown = ''">
              <div class="dropdown-header">信号层数据</div>
              <router-link v-for="item in dataItems" :key="item.path" :to="item.path" class="dropdown-item"
                :class="{ active: $route.path === item.path }"
              >
                <component :is="item.icon" class="dropdown-icon" />
                <div class="dropdown-content">
                  <div class="dropdown-title">{{ item.label }}</div>
                  <div class="dropdown-desc">{{ item.desc }}</div>
                </div>
              </router-link>
            </div>
          </transition>
        </div>
      </nav>

      <!-- 右侧区域 -->
      <div class="header-right">
        <AlertBell />
        <div class="user-area" @click="handleUserClick" v-click-outside="closeUserMenu">
          <div class="avatar" :class="{ unlogin: !isLoggedIn }">{{ userInitial }}</div>
          <transition name="dropdown-slide">
            <div v-if="showUserMenu && isLoggedIn" class="dropdown-panel user-panel" @click.stop>
              <div class="panel-header">
                <div class="avatar lg">{{ userInitial }}</div>
                <div>
                  <div class="panel-username">{{ userStore.userInfo?.username || '访客' }}</div>
                  <div class="panel-role">{{ userStore.userInfo?.role || '普通用户' }}</div>
                </div>
              </div>
              <div class="panel-divider" />
              <div class="panel-item" @click="router.push('/watchlist')">
                <el-icon><Star /></el-icon>
                <span>我的自选</span>
              </div>
              <div class="panel-divider" />
              <div class="panel-item danger" @click="handleLogout">
                <el-icon><SwitchButton /></el-icon>
                <span>退出登录</span>
              </div>
            </div>
          </transition>
        </div>
      </div>
    </div>

    <!-- 搜索（已移除） -->
  </header>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import AlertBell from '@/components/common/AlertBell.vue'
import {
  ArrowDown, SwitchButton, Star,
  TrendCharts, DataAnalysis, Aim, Histogram, Reading,
} from '@element-plus/icons-vue'

const userStore = useUserStore()
const route = useRoute()
const router = useRouter()
const showUserMenu = ref(false)
const openDropdown = ref('')

const DATA_ICON = { template: '<svg.../>' }

const isLoggedIn = computed(() => !!userStore.token)

const userInitial = computed(() => {
  const name = userStore.userInfo?.username
  return name ? name.charAt(0).toUpperCase() : (isLoggedIn.value ? 'U' : '?')
})

function handleUserClick() {
  if (isLoggedIn.value) {
    showUserMenu.value = !showUserMenu.value
  } else {
    router.push('/login')
  }
}

function closeUserMenu() {
  showUserMenu.value = false
}

// ── 主菜单 ──
const mainNavItems = [
  { path: '/home', label: '行情', icon: TrendCharts },
  { path: '/stocks', label: '股票', icon: DataAnalysis },
  { path: '/news', label: '资讯', icon: Reading },
  { path: '/watchlist', label: '自选', icon: Star },
  { path: '/chat', label: 'AI分析', icon: undefined },
]

// ── 数据中心 ──
const dataItems = [
  { path: '/hot-reason', label: '题材热点', desc: '每日强势股题材归因', icon: DataAnalysis },
  { path: '/industry-compare', label: '行业对比', desc: '90 行业涨跌排行·资金流向', icon: Histogram },
  { path: '/northbound', label: '北向资金', desc: '沪深港通实时资金流向', icon: TrendCharts },
  { path: '/dragon-tiger', label: '龙虎榜', desc: '席位数据·净买入排行', icon: Aim },
  { path: '/lockup', label: '限售解禁', desc: '解禁日历·个股查询', icon: Reading },
]

// ── 活跃判断 ──
function isActive(path: string) {
  return route.path === path || route.path.startsWith(path + '/')
}

const isSignalActive = computed(() =>
  dataItems.some(s => route.path.startsWith(s.path))
)

function handleLogout() {
  showUserMenu.value = false
  userStore.logout()
  router.push('/login')
}

// Click outside directive
const vClickOutside = {
  mounted(el: HTMLElement, binding: any) {
    (el as any).__clickOutside = (event: MouseEvent) => {
      if (!el.contains(event.target as Node)) binding.value()
    }
    document.addEventListener('click', (el as any).__clickOutside)
  },
  unmounted(el: HTMLElement) {
    document.removeEventListener('click', (el as any).__clickOutside)
  },
}
</script>

<style scoped lang="scss">
/* ── Header ── */
.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  height: $nav-height;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: saturate(180%) blur(24px);
  -webkit-backdrop-filter: saturate(180%) blur(24px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.header-inner {
  display: flex;
  align-items: center;
  height: 100%;
  padding: 0 20px;
  max-width: 1440px;
  margin: 0 auto;
}

/* ── Logo ── */
.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  flex-shrink: 0;
  margin-right: 24px;

  .logo-text {
    font-family: $font-display;
    font-size: 15px;
    font-weight: 700;
    color: white;
    letter-spacing: -0.3px;
  }
}

/* ── 主导航 ── */
.main-nav {
  display: flex;
  align-items: center;
  gap: 2px;
  flex: 1;
  justify-content: center;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
  font-weight: 500;
  text-decoration: none;
  border: none;
  background: transparent;
  border-radius: $rounded-pill;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  white-space: nowrap;
  position: relative;

  .nav-icon {
    font-size: 16px;
    transition: transform 0.2s;
  }

  &:hover {
    color: rgba(255, 255, 255, 0.8);
    background: rgba(255, 255, 255, 0.06);

    .nav-icon { transform: scale(1.05); }
  }

  &.active {
    color: white;
    background: rgba(255, 255, 255, 0.12);
  }
}

.more-btn {
  padding: 6px 10px;
}

.dropdown-arrow {
  font-size: 10px !important;
  transition: transform 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94);

  &.open { transform: rotate(180deg); }
}

/* ── 下拉面板 ── */
.nav-dropdown {
  position: relative;
}

.dropdown-panel {
  position: absolute;
  top: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  min-width: 220px;
  background: rgba(28, 28, 30, 0.96);
  backdrop-filter: blur(32px);
  -webkit-backdrop-filter: blur(32px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  padding: 8px;
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.5);
  z-index: 100;
  overflow: hidden;
}

.more-panel { min-width: 180px; }

.dropdown-header {
  padding: 8px 12px 6px;
  font-size: 11px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.3);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  text-decoration: none;
  transition: all 0.15s;
  cursor: pointer;

  &:hover {
    background: rgba(255, 255, 255, 0.08);
  }

      &.active {
        background: rgba(24, 144, 255, 0.15);
      }

      .dropdown-icon {
        flex-shrink: 0;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.06);
        color: rgba(255, 255, 255, 0.7);
        font-size: 15px;
      }

      &.active .dropdown-icon {
        background: rgba(24, 144, 255, 0.2);
        color: #40A9FF;
      }

  .dropdown-content {
    flex: 1;
    min-width: 0;
  }

  .dropdown-title {
    font-size: 13px;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.85);
    line-height: 1.3;
  }

  .dropdown-desc {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.3);
    margin-top: 1px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

/* ── 右侧 ── */
.header-right {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  margin-left: 24px;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.4);
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    color: white;
    background: rgba(255, 255, 255, 0.08);
  }

  .el-icon { font-size: 18px; }
}

/* ── 用户区域 ── */
.user-area {
  position: relative;
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 4px;
  border-radius: 50%;
  transition: background 0.2s;

  &:hover { background: rgba(255, 255, 255, 0.06); }
}

.avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #40A9FF, #1890FF);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
  transition: all 0.2s;

  &.lg { width: 36px; height: 36px; font-size: 15px; }

  &.unlogin {
    background: rgba(255, 255, 255, 0.15);
    color: rgba(255, 255, 255, 0.4);
    font-size: 14px;
    &:hover { background: rgba(255, 255, 255, 0.25); color: rgba(255, 255, 255, 0.6); }
  }
}

/* ── 用户下拉面板 ── */
.user-panel {
  left: auto;
  right: 0;
  transform: none;
  min-width: 200px;
  padding: 12px;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 4px 8px;
}

.panel-username { font-size: 14px; font-weight: 600; color: white; }
.panel-role { font-size: 12px; color: rgba(255, 255, 255, 0.35); margin-top: 2px; }

.panel-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.06);
  margin: 4px -4px;
}

.panel-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 8px;
  border-radius: 10px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.75);
  cursor: pointer;
  transition: all 0.15s;

  &:hover { background: rgba(255, 255, 255, 0.08); color: white; }

  .el-icon { font-size: 16px; }

  &.danger:hover {
    color: #ec4d4c;
    background: rgba(236, 77, 76, 0.1);
  }
}

/* ── 搜索覆盖 ── */
.search-overlay {
  position: fixed;
  top: $nav-height;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  z-index: 999;
  display: flex;
  justify-content: center;
  padding-top: 60px;
}

.search-box {
  width: 520px;
  max-width: 90vw;
}

.search-results {
  margin-top: 8px;
  background: rgba(28,28,30,0.96);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  overflow: hidden;
}

.search-result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.15s;
  &:hover { background: rgba(255,255,255,0.08); }
  &:not(:last-child) { border-bottom: 1px solid rgba(255,255,255,0.04); }
  .sr-code { font-family: monospace; font-size: 13px; color: #2997ff; font-weight: 500; }
  .sr-name { flex: 1; font-size: 13px; color: rgba(255,255,255,0.85); }
  .sr-market { font-size: 11px; color: rgba(255,255,255,0.3); padding: 2px 8px; border-radius: 4px; background: rgba(255,255,255,0.06); }
}

.search-empty {
  margin-top: 8px;
  padding: 20px;
  text-align: center;
  font-size: 13px;
  color: rgba(255,255,255,0.3);
  background: rgba(28,28,30,0.96);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
}

/* ── 过渡动画 ── */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.dropdown-slide-enter-active {
  transition: all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
.dropdown-slide-leave-active {
  transition: all 0.15s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
.dropdown-slide-enter-from {
  opacity: 0;
  transform: translateX(-50%) translateY(-6px) scale(0.96);
}
.dropdown-slide-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-4px) scale(0.97);
}

.user-panel.dropdown-slide-enter-from,
.user-panel.dropdown-slide-leave-to {
  transform: translateY(-6px) scale(0.96);
}
</style>
