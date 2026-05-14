<template>
  <header class="app-header">
    <div class="header-inner">
      <!-- Logo -->
      <router-link to="/home" class="logo">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M3 3V21H21" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
          <path d="M7 15L11 9L15 13L21 5" stroke="#2997ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span class="logo-text">StockAI</span>
      </router-link>

      <!-- Spacer left to push nav to center -->
      <div class="header-spacer"></div>

      <!-- Main Nav (centered) -->
      <nav class="main-nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-link"
          :class="{ active: $route.path.startsWith(item.path) }"
        >
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
        <!-- 信号层下拉菜单 -->
        <div class="nav-dropdown" @mouseenter="showSignalMenu = true" @mouseleave="showSignalMenu = false">
          <router-link to="/hot-reason" class="nav-link" :class="{ active: signalItems.some(s => $route.path.startsWith(s.path)) }">
            <span class="nav-label">信号</span>
            <el-icon style="margin-left:2px;font-size:11px;"><CaretBottom /></el-icon>
          </router-link>
          <transition name="fade">
            <div v-if="showSignalMenu" class="dropdown-menu">
              <router-link v-for="item in signalItems" :key="item.path" :to="item.path" class="dropdown-item">
                {{ item.label }}
              </router-link>
            </div>
          </transition>
        </div>
      </nav>

      <!-- Right Side -->
      <div class="header-right">
        <button class="search-btn" @click="showSearch = !showSearch">
          <el-icon><Search /></el-icon>
        </button>
        <AlertBell />
        <div class="user-info" @click="showUserMenu = !showUserMenu" v-click-outside="() => showUserMenu = false">
          <div class="avatar">{{ userInitial }}</div>
          <span class="username">{{ userStore.userInfo?.username || '登录' }}</span>
          <el-icon><CaretBottom /></el-icon>
          <transition name="fade">
            <div v-if="showUserMenu" class="user-menu">
              <div class="menu-item">
                <el-icon><User /></el-icon>
                <span>个人中心</span>
              </div>
              <div class="menu-item">
                <el-icon><Setting /></el-icon>
                <span>设置</span>
              </div>
              <div class="menu-divider"></div>
              <div class="menu-item text-rise" @click="handleLogout">
                <el-icon><SwitchButton /></el-icon>
                <span>退出登录</span>
              </div>
            </div>
          </transition>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import AlertBell from '@/components/common/AlertBell.vue'

const userStore = useUserStore()
const route = useRoute()
const router = useRouter()
const showUserMenu = ref(false)

const userInitial = computed(() => {
  const name = userStore.userInfo?.username || 'U'
  return name.charAt(0).toUpperCase()
})

const navItems = [
  { path: '/home', label: '行情', icon: 'TrendCharts' },
  { path: '/stocks', label: '股票', icon: 'DataAnalysis' },
  { path: '/watchlist', label: '自选', icon: 'Star' },
  { path: '/news', label: '资讯', icon: 'Reading' },
  { path: '/chat', label: 'AI分析', icon: 'ChatLineSquare' },
]

// 信号层页面（导航栏下拉子菜单用，或独立入口）
const signalItems = [
  { path: '/hot-reason', label: '题材热点' },
  { path: '/northbound', label: '北向资金' },
  { path: '/dragon-tiger', label: '龙虎榜' },
  { path: '/industry-compare', label: '行业对比' },
  { path: '/fund-flow', label: '资金流向' },
  { path: '/lockup', label: '限售解禁' },
  { path: '/consensus-eps', label: '一致预期' },
]

const showSignalMenu = ref(false)

function handleLogout() {
  showUserMenu.value = false
  userStore.logout()
  router.push('/login')
}

// Click outside directive
const vClickOutside = {
  mounted(el: HTMLElement, binding: any) {
    el.__clickOutside = (event: MouseEvent) => {
      if (!el.contains(event.target as Node)) {
        binding.value()
      }
    }
    document.addEventListener('click', el.__clickOutside)
  },
  unmounted(el: HTMLElement) {
    document.removeEventListener('click', el.__clickOutside)
  },
}
</script>

<style scoped lang="scss">
.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  height: $nav-height;
  background: $surface-black;
  backdrop-filter: saturate(180%) blur(20px);
}

.header-inner {
  display: flex;
  align-items: center;
  height: 100%;
  padding: 0 $spacing-lg;
  max-width: 1440px;
  margin: 0 auto;
}

.logo {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  text-decoration: none;
  flex-shrink: 0;

  .logo-text {
    font-family: $font-display;
    font-size: 16px;
    font-weight: 600;
    color: white;
    letter-spacing: -0.374px;
  }
}

.header-spacer {
  flex: 1;
}

.main-nav {
  display: flex;
  gap: 2px;
  align-items: center;
  background: rgba(255, 255, 255, 0.06);
  border-radius: $rounded-pill;
  padding: 2px;
}

.nav-link {
  display: flex;
  align-items: center;
  padding: 7px 22px;
  color: rgba(255, 255, 255, 0.55);
  font-size: 13px;
  font-weight: 500;
  text-decoration: none;
  border-radius: $rounded-pill;
  transition: all 0.2s;
  white-space: nowrap;

  &:hover {
    color: rgba(255, 255, 255, 0.85);
    background: rgba(255, 255, 255, 0.08);
  }

  &.active {
    color: white;
    background: rgba(255, 255, 255, 0.15);
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  flex-shrink: 0;
}

.search-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    color: white;
    background: rgba(255, 255, 255, 0.1);
  }

  .el-icon { font-size: 18px; }
}

.user-info {
  position: relative;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 5px 10px;
  border-radius: $rounded-pill;
  transition: background 0.2s;

  &:hover { background: rgba(255, 255, 255, 0.08); }

  .el-icon { color: rgba(255, 255, 255, 0.5); font-size: 12px; }
}

.avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: $primary;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
}

.username {
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
}

.user-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  background: rgba(30, 30, 30, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: $rounded-md;
  padding: $spacing-xs 0;
  min-width: 160px;
  z-index: 100;
}

/* 信号层下拉菜单 */
.nav-dropdown {
  position: relative;
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  background: rgba(30, 30, 30, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: $rounded-md;
  padding: 4px 0;
  min-width: 140px;
  z-index: 100;
  overflow: hidden;
}

.dropdown-item {
  display: block;
  padding: 8px 16px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.75);
  text-decoration: none;
  transition: all 0.15s;
  white-space: nowrap;

  &:hover {
    background: rgba(255, 255, 255, 0.08);
    color: white;
  }

  &.router-link-active {
    color: $primary;
    background: rgba($primary, 0.1);
  }
}

.menu-item {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  padding: 10px 16px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.85);
  cursor: pointer;
  transition: background 0.15s;

  &:hover { background: rgba(255, 255, 255, 0.08); }
  .el-icon { font-size: 16px; }
}

.menu-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.1);
  margin: 4px 0;
}
</style>
