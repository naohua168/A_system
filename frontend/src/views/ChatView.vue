<template>
  <div class="chat-view">
    <div class="placeholder">
      <el-icon class="icon"><ChatLineSquare /></el-icon>
      <h3>AI 智能分析</h3>
      <p>此功能正在开发中，敬请期待...</p>
      <p class="caption">将集成 DeepSeek / Kimi API，支持股票基金智能问答</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ChatLineSquare } from '@element-plus/icons-vue'
</script>

<style scoped lang="scss">
.chat-view {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.placeholder {
  text-align: center;
  padding: $spacing-xxl;

  .icon {
    font-size: 64px;
    color: $primary;
    opacity: 0.5;
    margin-bottom: $spacing-lg;
  }

  h3 {
    font-size: 24px;
    margin-bottom: $spacing-sm;
  }

  p {
    color: $ink-muted-48;
    font-size: 15px;
    margin-bottom: $spacing-xs;
  }

  .caption {
    font-size: 13px;
    margin-top: $spacing-md;
  }
}
</style>
