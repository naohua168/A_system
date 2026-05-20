<template>
  <div class="layer-detail-panel">
    <!-- 加载状态 -->
    <div v-if="loading" class="detail-loading">
      <el-skeleton :rows="6" animated />
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="detail-error">
      <el-result icon="error" title="加载失败" :sub-title="error">
        <template #extra>
          <el-button type="primary" @click="$emit('retry')">重试</el-button>
        </template>
      </el-result>
    </div>

    <!-- 空数据状态 -->
    <div v-else-if="!layer" class="detail-empty">
      <el-result icon="info" title="未选择层" sub-title="请从列表中选择一个层查看详情" />
    </div>

    <!-- 详情内容 -->
    <template v-else>
      <!-- 基本信息 -->
      <section class="panel-section">
        <div class="section-title">基本信息</div>
        <div class="info-grid">
          <div class="info-cell">
            <span class="cell-label">层编号</span>
            <span class="cell-value badge-id">{{ layer.id }}</span>
          </div>
          <div class="info-cell">
            <span class="cell-label">层名称</span>
            <span class="cell-value">{{ layer.name }}</span>
          </div>
          <div class="info-cell">
            <span class="cell-label">项目目录</span>
            <span class="cell-value mono">{{ layer.directory }}</span>
          </div>
          <div class="info-cell">
            <span class="cell-label">状态</span>
            <LayerStatusBadge :status="layer.status" />
          </div>
          <div class="info-cell">
            <span class="cell-label">完成度</span>
            <div class="completion-cell">
              <el-progress
                :percentage="layer.completion"
                :color="statusBarColor"
                :stroke-width="10"
                :text-inside="true"
              />
            </div>
          </div>
          <div class="info-cell">
            <span class="cell-label">最后更新</span>
            <span class="cell-value">{{ layer.lastUpdated }}</span>
          </div>
        </div>
      </section>

      <!-- 角色描述 -->
      <section class="panel-section">
        <div class="section-title">角色定位</div>
        <p class="desc-text">{{ layer.description }}</p>
      </section>

      <!-- 技术栈 -->
      <section class="panel-section">
        <div class="section-title">技术栈</div>
        <div class="tech-tags">
          <el-tag
            v-for="tech in techTags"
            :key="tech"
            type="info"
            effect="plain"
            size="small"
          >
            {{ tech }}
          </el-tag>
        </div>
      </section>

      <!-- 统计概览 -->
      <section class="panel-section">
        <div class="section-title">统计概览</div>
        <div class="stats-grid">
          <div class="stat-card">
            <span class="stat-num">{{ layer.fileCount }}</span>
            <span class="stat-lbl">文件数</span>
          </div>
          <div class="stat-card">
            <span class="stat-num">{{ layer.moduleCount }}</span>
            <span class="stat-lbl">模块数</span>
          </div>
          <div class="stat-card">
            <span class="stat-num">{{ layer.testCount }}</span>
            <span class="stat-lbl">测试用例</span>
          </div>
        </div>
      </section>

      <!-- 功能模块 -->
      <section class="panel-section">
        <div class="section-title">功能模块</div>
        <div class="module-list">
          <div
            v-for="mod in layer.modules"
            :key="mod.name"
            class="module-item"
          >
            <div class="module-header">
              <div class="module-left">
                <span class="module-name">{{ mod.name }}</span>
                <LayerStatusBadge :status="mod.status" />
              </div>
            </div>
            <p class="module-desc">{{ mod.description }}</p>
            <div v-if="mod.files?.length" class="module-files">
              <span
                v-for="f in mod.files"
                :key="f"
                class="file-tag"
              >
                {{ f }}
              </span>
            </div>
          </div>
        </div>
      </section>

      <!-- 待解决项 -->
      <section v-if="layer.issues.length" class="panel-section">
        <div class="section-title">待解决项</div>
        <div class="issue-list">
          <div v-for="(issue, i) in layer.issues" :key="i" class="issue-item">
            <el-icon :size="14" color="#E6A23C"><WarningFilled /></el-icon>
            <span>{{ issue }}</span>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { WarningFilled } from '@element-plus/icons-vue'
import type { LayerInfo } from '@/types'
import { LAYER_STATUS_COLOR } from '@/types'
import LayerStatusBadge from './LayerStatusBadge.vue'

const props = defineProps<{
  layer: LayerInfo | null
  loading: boolean
  error: string | null
}>()

defineEmits<{
  retry: []
}>()

/** 进度条颜色 */
const statusBarColor = computed(() => {
  if (!props.layer) return '#409EFF'
  return LAYER_STATUS_COLOR[props.layer.status]
})

/** 技术栈标签列表 */
const techTags = computed(() => {
  if (!props.layer) return []
  return props.layer.techStack.split(',').map((t) => t.trim()).filter(Boolean)
})
</script>

<style scoped lang="scss">
.layer-detail-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.detail-loading {
  padding: 40px 20px;
}
.detail-error,
.detail-empty {
  padding: 60px 20px;
}

.panel-section {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #ebeef5;

  .section-title {
    font-size: 14px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 16px;
    padding-bottom: 10px;
    border-bottom: 1px solid #f0f2f5;
  }
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;

  @media (max-width: 640px) {
    grid-template-columns: 1fr;
  }

  .info-cell {
    display: flex;
    flex-direction: column;
    gap: 4px;

    .cell-label {
      font-size: 12px;
      color: #909399;
    }

    .cell-value {
      font-size: 14px;
      color: #303133;

      &.badge-id {
        font-weight: 700;
        color: #409eff;
      }

      &.mono {
        font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
        font-size: 13px;
      }
    }

    .completion-cell {
      max-width: 200px;
    }
  }
}

.desc-text {
  margin: 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.8;
}

.tech-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;

  @media (max-width: 480px) {
    grid-template-columns: 1fr 1fr;
  }

  .stat-card {
    text-align: center;
    padding: 12px 8px;
    background: #f5f7fa;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    gap: 4px;

    .stat-num {
      font-size: 24px;
      font-weight: 700;
      color: #409eff;
    }

    .stat-lbl {
      font-size: 12px;
      color: #909399;
    }
  }
}

.module-list {
  display: flex;
  flex-direction: column;
  gap: 12px;

  .module-item {
    padding: 12px;
    background: #f5f7fa;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    gap: 8px;

    .module-header {
      .module-left {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .module-name {
        font-size: 14px;
        font-weight: 600;
        color: #303133;
      }
    }

    .module-desc {
      margin: 0;
      font-size: 13px;
      color: #606266;
      line-height: 1.5;
    }

    .module-files {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;

      .file-tag {
        font-size: 11px;
        font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
        color: #909399;
        background: #eef0f4;
        padding: 1px 6px;
        border-radius: 3px;
        white-space: nowrap;
      }
    }
  }
}

.issue-list {
  display: flex;
  flex-direction: column;
  gap: 8px;

  .issue-item {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    font-size: 13px;
    color: #606266;
    line-height: 1.5;

    .el-icon {
      flex-shrink: 0;
      margin-top: 2px;
    }
  }
}
</style>
