<template>
  <div class="ai-signal-summary">
    <div class="title">
      <el-icon :size="14"><ChatLineSquare /></el-icon>
      AI 信号摘要
    </div>
    <div class="signal" :class="signal">
      <el-icon :size="18" v-if="signal === 'bullish'"><Top /></el-icon>
      <el-icon :size="18" v-else-if="signal === 'bearish'"><Bottom /></el-icon>
      <el-icon :size="18" v-else><Minus /></el-icon>
      <span class="text">{{ text }}</span>
    </div>
    <div class="detail" v-if="detail">{{ detail }}</div>
  </div>
</template>

<script setup lang="ts">
import { ChatLineSquare, Top, Bottom, Minus } from '@element-plus/icons-vue'
defineProps<{
  signal: 'bullish' | 'bearish' | 'neutral'
  text: string
  detail?: string
}>()
</script>

<style scoped lang="scss">
.ai-signal-summary { border: 1px solid $divider-soft; border-radius: $rounded-md; padding: 12px; margin-bottom: 12px; }
.title { font-size: 13px; color: $ink-muted-48; margin-bottom: 8px; display: flex; align-items: center; gap: 6px; }
.signal { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 6px; }
.signal.bullish { background: #e8f5e9; color: #2e7d32; }
.signal.bearish { background: #fce4ec; color: #c62828; }
.signal.neutral { background: #fff3e0; color: #e65100; }
.text { font-weight: 600; font-size: 15px; }
.detail { margin-top: 8px; font-size: 13px; color: $ink-muted-48; line-height: 1.5; }
</style>
