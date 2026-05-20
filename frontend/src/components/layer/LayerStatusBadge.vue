<template>
  <span class="layer-badge" :class="statusClass">
    <span class="dot" :style="{ backgroundColor: color }" />
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { LayerStatus } from '@/types'
import {
  LAYER_STATUS_LABEL,
  LAYER_STATUS_CLASS,
  LAYER_STATUS_COLOR,
} from '@/types'

const props = defineProps<{
  status: LayerStatus
}>()

const label = computed(() => LAYER_STATUS_LABEL[props.status])
const statusClass = computed(() => LAYER_STATUS_CLASS[props.status])
const color = computed(() => LAYER_STATUS_COLOR[props.status])
</script>

<style scoped lang="scss">
.layer-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  border: 1px solid transparent;

  &.status-completed {
    color: #67c23a;
    background: #f0f9eb;
    border-color: #c2e7b0;
  }
  &.status-in-progress {
    color: #409eff;
    background: #ecf5ff;
    border-color: #b3d8ff;
  }
  &.status-blocked {
    color: #f56c6c;
    background: #fef0f0;
    border-color: #fab6b6;
  }
  &.status-pending {
    color: #909399;
    background: #f4f4f5;
    border-color: #e9e9eb;
  }

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
  }
}
</style>
