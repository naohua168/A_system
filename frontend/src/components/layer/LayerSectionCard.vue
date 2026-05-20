<template>
  <div class="layer-section-card" @click="$emit('select', layer.id)">
    <!-- 头部 -->
    <div class="card-header">
      <div class="header-left">
        <span class="layer-badge-id">{{ layer.id }}</span>
        <div class="header-info">
          <h3 class="layer-name">{{ layer.name }}</h3>
          <span class="layer-dir">{{ layer.directory }}</span>
        </div>
      </div>
      <div class="header-right">
        <LayerStatusBadge :status="layer.status" />
      </div>
    </div>

    <!-- 描述 -->
    <p class="layer-desc">{{ layer.description }}</p>

    <!-- 进度与统计 -->
    <div class="layer-stats">
      <div class="stat-bar">
        <div class="stat-bar-fill" :style="barStyle" />
      </div>
      <div class="stat-numbers">
        <span class="stat-item">
          <em>{{ layer.completion }}%</em> 完成度
        </span>
        <span class="stat-divider">|</span>
        <span class="stat-item">
          <em>{{ layer.fileCount }}</em> 文件
        </span>
        <span class="stat-divider">|</span>
        <span class="stat-item">
          <em>{{ layer.moduleCount }}</em> 模块
        </span>
        <span class="stat-divider">|</span>
        <span class="stat-item">
          <em>{{ layer.testCount }}</em> 测试
        </span>
      </div>
    </div>

    <!-- 技术栈 -->
    <div class="tech-stack">
      <el-icon :size="14"><Monitor /></el-icon>
      <span>{{ layer.techStack }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Monitor } from '@element-plus/icons-vue'
import type { LayerInfo } from '@/types'
import { LAYER_STATUS_COLOR } from '@/types'
import LayerStatusBadge from './LayerStatusBadge.vue'

const props = defineProps<{
  layer: LayerInfo
}>()

defineEmits<{
  select: [id: string]
}>()

const barStyle = computed(() => ({
  width: `${props.layer.completion}%`,
  backgroundColor: LAYER_STATUS_COLOR[props.layer.status],
}))
</script>

<style scoped lang="scss">
.layer-section-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px 24px;
  cursor: pointer;
  transition: all 0.25s ease;
  border: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
  gap: 12px;

  &:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
    border-color: #c6e2ff;
    transform: translateY(-2px);
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
  }

  .layer-badge-id {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 42px;
    height: 42px;
    border-radius: 10px;
    background: linear-gradient(135deg, #409eff 0%, #337ecc 100%);
    color: #fff;
    font-size: 16px;
    font-weight: 700;
    flex-shrink: 0;
  }

  .header-info {
    min-width: 0;
  }

  .layer-name {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    line-height: 1.4;
  }

  .layer-dir {
    font-size: 12px;
    color: #909399;
    font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  }
}

.layer-desc {
  margin: 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.layer-stats {
  display: flex;
  flex-direction: column;
  gap: 6px;

  .stat-bar {
    height: 6px;
    background: #f0f2f5;
    border-radius: 4px;
    overflow: hidden;

    .stat-bar-fill {
      height: 100%;
      border-radius: 4px;
      transition: width 0.6s ease;
    }
  }

  .stat-numbers {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: #909399;
    flex-wrap: wrap;

    .stat-item em {
      font-style: normal;
      font-weight: 600;
      color: #303133;
    }

    .stat-divider {
      color: #dcdfe6;
    }
  }
}

.tech-stack {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #909399;
  line-height: 1.4;

  .el-icon {
    color: #409eff;
    flex-shrink: 0;
  }
}
</style>
