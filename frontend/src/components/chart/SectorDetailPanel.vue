<template>
  <div class="sector-detail-panel" :class="{ visible: modelValue }">
    <div class="panel-header">
      <div class="sector-info">
        <h3 class="sector-name">{{ sectorName }}</h3>
        <div class="sector-change" :class="changeClass">
          {{ changeSign }}{{ sectorChange?.toFixed(2) }}%
        </div>
      </div>
      <el-button class="close-btn" text @click="$emit('update:modelValue', false)">
        <el-icon><Close /></el-icon>
      </el-button>
    </div>
    <div class="panel-body">
      <div class="empty-hint">
        <el-icon :size="48" color="rgba(255,255,255,0.2)"><PieChart /></el-icon>
        <p>云图数据实时更新</p>
        <p class="sub">点击云图查看行业概览</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Close, PieChart } from '@element-plus/icons-vue'

const props = defineProps<{
  modelValue: boolean
  sectorName: string
  sectorChange?: number
}>()

defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const changeClass = computed(() => {
  const change = props.sectorChange || 0
  return change >= 0 ? 'rise' : 'fall'
})

const changeSign = computed(() => {
  const change = props.sectorChange || 0
  return change >= 0 ? '+' : ''
})
</script>

<style scoped lang="scss">
.sector-detail-panel {
  position: fixed;
  right: 0;
  top: 0;
  width: 320px;
  height: 100vh;
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  border-left: 1px solid rgba(255, 255, 255, 0.08);
  z-index: 1000;
  transform: translateX(100%);
  transition: transform 0.3s ease;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  &.visible {
    transform: translateX(0);
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    flex-shrink: 0;

    .sector-info {
      display: flex;
      align-items: center;
      gap: 12px;

      .sector-name {
        margin: 0;
        font-size: 18px;
        font-weight: 600;
        color: #fff;
      }

      .sector-change {
        font-size: 14px;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 4px;

        &.rise {
          color: #ef5350;
          background: rgba(239, 83, 80, 0.1);
        }

        &.fall {
          color: #66bb6a;
          background: rgba(102, 187, 106, 0.1);
        }
      }
    }

    .close-btn {
      color: rgba(255, 255, 255, 0.5);

      &:hover {
        color: #fff;
      }
    }
  }

  .panel-body {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;

    .empty-hint {
      text-align: center;
      color: rgba(255, 255, 255, 0.4);

      p {
        margin: 8px 0 0;
        font-size: 14px;
      }

      .sub {
        font-size: 12px;
        opacity: 0.6;
      }
    }
  }
}
</style>
