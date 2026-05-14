<template>
  <div class="alert-bell" v-click-outside="() => showPanel = false">
    <button class="bell-btn" @click="showPanel = !showPanel" :class="{ hasAlert: unreadCount > 0 }">
      <el-icon><Bell /></el-icon>
      <span v-if="unreadCount > 0" class="badge">{{ unreadCount > 9 ? '9+' : unreadCount }}</span>
    </button>

    <transition name="alert-fade">
      <div v-if="showPanel" class="alert-panel">
        <div class="panel-header">
          <span class="panel-title">价格异动提醒</span>
          <button class="clear-btn" @click="markAllRead" v-if="unreadCount > 0">全部已读</button>
        </div>

        <div class="alert-list" v-if="alerts.length">
          <div v-for="alert in alerts" :key="alert.id"
            :class="['alert-item', { unread: !alert.read }]"
            @click="handleClickAlert(alert)"
          >
            <div class="alert-icon" :class="alert.type">
              <el-icon v-if="alert.type === 'price'"><Top /></el-icon>
              <el-icon v-else-if="alert.type === 'drop'"><Bottom /></el-icon>
              <el-icon v-else><Warning /></el-icon>
            </div>
            <div class="alert-body">
              <div class="alert-title">{{ alert.title }}</div>
              <div class="alert-desc">{{ alert.desc }}</div>
              <div class="alert-time">{{ alert.time }}</div>
            </div>
            <div class="alert-change" :class="alert.change >= 0 ? 'rise' : 'fall'">
              {{ alert.change >= 0 ? '+' : '' }}{{ alert.change.toFixed(2) }}%
            </div>
          </div>
        </div>

        <div class="panel-empty" v-else>
          <el-icon><Check /></el-icon>
          <span>暂无提醒</span>
        </div>

        <div class="panel-footer">
          <router-link to="/watchlist" class="footer-link">管理自选预警</router-link>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Bell, Top, Bottom, Warning, Check } from '@element-plus/icons-vue'

const router = useRouter()

interface AlertItem {
  id: string
  type: 'price' | 'drop' | 'tech'
  title: string
  desc: string
  time: string
  change: number
  read: boolean
  code: string
}

const showPanel = ref(false)

const alerts = ref<AlertItem[]>([])

const unreadCount = computed(() => alerts.value.filter(a => !a.read).length)

function markAllRead() {
  alerts.value.forEach(a => a.read = true)
}

function handleClickAlert(alert: AlertItem) {
  alert.read = true
  showPanel.value = false
  router.push(`/stock/${alert.code}`)
}

// Click outside directive
const vClickOutside = {
  mounted(el: HTMLElement, binding: any) {
    el.__clickOutside = (event: MouseEvent) => {
      if (!el.contains(event.target as Node)) binding.value()
    }
    document.addEventListener('click', el.__clickOutside)
  },
  unmounted(el: HTMLElement) {
    document.removeEventListener('click', el.__clickOutside)
  },
}
</script>

<style scoped lang="scss">
.alert-bell {
  position: relative;
}

.bell-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: rgba(255,255,255,0.5);
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s;

  &:hover { color: white; background: rgba(255,255,255,0.1); }
  &.hasAlert { color: #ff6b6b; animation: bell-shake 0.5s ease-in-out; }

  .el-icon { font-size: 18px; }

  .badge {
    position: absolute;
    top: -2px;
    right: -2px;
    min-width: 16px;
    height: 16px;
    border-radius: 8px;
    background: #ff4757;
    color: white;
    font-size: 10px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 4px;
    box-shadow: 0 2px 6px rgba(255,71,87,0.4);
  }
}

@keyframes bell-shake {
  0%, 100% { transform: rotate(0); }
  25% { transform: rotate(10deg); }
  50% { transform: rotate(-10deg); }
  75% { transform: rotate(5deg); }
}

.alert-panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 360px;
  max-height: 420px;
  background: rgba(30,30,30,0.96);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: $rounded-md;
  overflow: hidden;
  z-index: 100;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $spacing-md $spacing-lg;
  border-bottom: 1px solid rgba(255,255,255,0.06);

  .panel-title { font-size: 14px; font-weight: 600; color: rgba(255,255,255,0.9); }
  .clear-btn { font-size: 12px; color: rgba(41,151,255,0.8); background: none; border: none; cursor: pointer;
    &:hover { color: #2997ff; }
  }
}

.alert-list {
  max-height: 320px;
  overflow-y: auto;
}

.alert-item {
  display: flex;
  gap: $spacing-sm;
  padding: $spacing-md $spacing-lg;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  cursor: pointer;
  transition: background 0.15s;

  &:hover { background: rgba(255,255,255,0.05); }
  &.unread { background: rgba(41,151,255,0.04); }
}

.alert-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 16px;

  &.price { background: rgba(231,76,60,0.15); color: $rise; }
  &.drop { background: rgba(39,174,96,0.15); color: $fall; }
  &.tech { background: rgba(41,151,255,0.15); color: #2997ff; }
}

.alert-body {
  flex: 1;
  min-width: 0;

  .alert-title { font-size: 13px; font-weight: 600; color: rgba(255,255,255,0.9); margin-bottom: 2px; }
  .alert-desc { font-size: 12px; color: rgba(255,255,255,0.5); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 2px; }
  .alert-time { font-size: 11px; color: rgba(255,255,255,0.3); }
}

.alert-change {
  font-family: $font-display;
  font-size: 14px;
  font-weight: 700;
  white-space: nowrap;
  align-self: center;

  &.rise { color: $rise; }
  &.fall { color: $fall; }
}

.panel-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-xl;
  color: rgba(255,255,255,0.3);

  .el-icon { font-size: 32px; }
  span { font-size: 13px; }
}

.panel-footer {
  padding: $spacing-sm $spacing-lg;
  border-top: 1px solid rgba(255,255,255,0.06);
  text-align: center;

  .footer-link { font-size: 12px; color: rgba(41,151,255,0.7); text-decoration: none;
    &:hover { color: #2997ff; }
  }
}

/* Transition */
.alert-fade-enter-active, .alert-fade-leave-active { transition: all 0.2s ease; }
.alert-fade-enter-from, .alert-fade-leave-to { opacity: 0; transform: translateY(-8px) scale(0.96); }
</style>
