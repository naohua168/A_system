<template>
  <div class="layer-detail-view">
    <!-- 页头 -->
    <div class="page-header">
      <div class="page-header-left">
        <el-button text @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <h2>系统架构总览</h2>
      </div>
      <div class="page-header-right">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索层名、目录或技术栈..."
          :prefix-icon="Search"
          clearable
          size="default"
          class="search-input"
          @input="onSearch"
        />
      </div>
    </div>

    <!-- 总体统计栏 -->
    <div class="overall-stats">
      <div class="overall-stat-card">
        <span class="overall-num">L1-L6</span>
        <span class="overall-lbl">架构层级</span>
      </div>
      <div class="overall-stat-card">
        <span class="overall-num">{{ store.overallCompletion }}%</span>
        <span class="overall-lbl">总体完成度</span>
      </div>
      <div class="overall-stat-card">
        <span class="overall-num">{{ store.totalFiles }}</span>
        <span class="overall-lbl">总文件数</span>
      </div>
      <div class="overall-stat-card">
        <span class="overall-num">{{ store.totalModules }}</span>
        <span class="overall-lbl">总模块数</span>
      </div>
      <div class="overall-stat-card">
        <span class="overall-num">{{ store.totalTests }}</span>
        <span class="overall-lbl">测试用例</span>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="store.loading" class="loading-area">
      <el-skeleton :rows="3" animated />
    </div>

    <!-- 加载失败 -->
    <div v-else-if="store.error" class="error-area">
      <el-result
        icon="error"
        title="加载失败"
        :sub-title="store.error"
      >
        <template #extra>
          <el-button type="primary" @click="store.init()">重试</el-button>
        </template>
      </el-result>
    </div>

    <!-- 主内容区 -->
    <template v-else>
      <div class="main-layout">
        <!-- 左侧：层列表 -->
        <aside class="layer-sidebar">
          <div class="sidebar-title">
            层列表
            <span class="layer-count">{{ filteredLayers.length }}层</span>
          </div>

          <!-- 空搜索 -->
          <div v-if="filteredLayers.length === 0" class="sidebar-empty">
            <p>未找到匹配层</p>
            <el-button text type="primary" @click="clearSearch">清除筛选</el-button>
          </div>

          <!-- 层列表 -->
          <nav v-else class="layer-nav">
            <div
              v-for="layer in filteredLayers"
              :key="layer.id"
              class="layer-nav-item"
              :class="{ active: selectedId === layer.id }"
              @click="selectLayer(layer.id)"
            >
              <div class="nav-item-top">
                <span class="nav-badge" :style="{ background: badgeColor(layer.status) }">
                  {{ layer.id }}
                </span>
                <span class="nav-name">{{ layer.name }}</span>
                <span class="nav-pct">{{ layer.completion }}%</span>
              </div>
              <div class="nav-bar">
                <div class="nav-bar-fill" :style="barFillStyle(layer)" />
              </div>
            </div>
          </nav>
        </aside>

        <!-- 右侧：详情面板 -->
        <main class="detail-main">
          <!-- 数据流图 -->
          <section class="flow-section" v-if="!selectedId">
            <div class="flow-title">层间数据流</div>
            <div class="flow-chain">
              <div
                v-for="(flow, i) in store.flows"
                :key="i"
                class="flow-step"
              >
                <div class="flow-node from">{{ flow.from }}</div>
                <div class="flow-arrow">
                  <el-icon color="#409EFF"><ArrowRight /></el-icon>
                  <div class="flow-via">{{ flow.via }}</div>
                </div>
                <div class="flow-node to">{{ flow.to }}</div>
              </div>
            </div>
          </section>

          <!-- 选中层详情 -->
          <LayerDetailPanel
            v-if="selectedId"
            :layer="store.currentLayer"
            :loading="store.detailLoading"
            :error="store.error"
            @retry="store.fetchLayerDetail(selectedId)"
          />

          <!-- 未选择时的概览卡片 -->
          <div v-if="!selectedId" class="overview-grid">
            <LayerSectionCard
              v-for="layer in filteredLayers"
              :key="layer.id"
              :layer="layer"
              @select="selectLayer"
            />
          </div>
        </main>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight, Search } from '@element-plus/icons-vue'
import type { LayerStatus } from '@/types'
import { LAYER_STATUS_COLOR } from '@/types'
import { useLayerStore } from '@/stores/layer'
import LayerSectionCard from '@/components/layer/LayerSectionCard.vue'
import LayerDetailPanel from '@/components/layer/LayerDetailPanel.vue'

const router = useRouter()
const store = useLayerStore()

// ============================================================
// State
// ============================================================
const selectedId = ref<string | null>(null)
const searchKeyword = ref('')

// ============================================================
// Computed
// ============================================================
const filteredLayers = computed(() => {
  const kw = searchKeyword.value.toLowerCase().trim()
  if (!kw) return store.sortedLayers
  return store.sortedLayers.filter(
    (l) =>
      l.id.toLowerCase().includes(kw) ||
      l.name.includes(kw) ||
      l.directory.toLowerCase().includes(kw) ||
      l.techStack.toLowerCase().includes(kw),
  )
})

// ============================================================
// Methods
// ============================================================
function goBack() {
  router.back()
}

async function selectLayer(id: string) {
  selectedId.value = id
  await store.fetchLayerDetail(id)
}

function onSearch() {
  // 搜索时自动清除选中层
  if (searchKeyword.value.trim()) {
    selectedId.value = null
  }
}

function clearSearch() {
  searchKeyword.value = ''
}

function badgeColor(status: LayerStatus): string {
  return LAYER_STATUS_COLOR[status]
}

function barFillStyle(layer: { completion: number; status: LayerStatus }) {
  return {
    width: `${layer.completion}%`,
    backgroundColor: LAYER_STATUS_COLOR[layer.status],
  }
}

// 每当路由参数变化时清除选中状态
watch(
  () => router.currentRoute.value,
  () => {
    selectedId.value = null
  },
)

// 初始化
onMounted(() => {
  store.init()
})
</script>

<style scoped lang="scss">
.layer-detail-view {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 0 0 40px;
}

// ============================================================
// 页头
// ============================================================
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;

  .page-header-left {
    display: flex;
    align-items: center;
    gap: 8px;

    h2 {
      margin: 0;
      font-size: 20px;
      font-weight: 600;
      color: #303133;
    }
  }

  .search-input {
    width: 280px;

    @media (max-width: 480px) {
      width: 100%;
    }
  }
}

// ============================================================
// 总体统计栏
// ============================================================
.overall-stats {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;

  @media (max-width: 768px) {
    grid-template-columns: repeat(3, 1fr);
  }
  @media (max-width: 480px) {
    grid-template-columns: repeat(2, 1fr);
  }

  .overall-stat-card {
    background: linear-gradient(135deg, #409eff 0%, #337ecc 100%);
    border-radius: 10px;
    padding: 16px 12px;
    text-align: center;
    display: flex;
    flex-direction: column;
    gap: 4px;

    .overall-num {
      font-size: 22px;
      font-weight: 700;
      color: #fff;
    }

    .overall-lbl {
      font-size: 12px;
      color: rgba(255, 255, 255, 0.8);
    }
  }
}

// ============================================================
// 加载 & 错误
// ============================================================
.loading-area,
.error-area {
  padding: 80px 20px;
  display: flex;
  justify-content: center;
}

// ============================================================
// 主布局（桌面双栏）
// ============================================================
.main-layout {
  display: flex;
  gap: 20px;
  flex: 1;

  @media (max-width: 900px) {
    flex-direction: column;
  }
}

// ============================================================
// 左侧边栏
// ============================================================
.layer-sidebar {
  width: 260px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  border: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 70vh;
  overflow-y: auto;

  @media (max-width: 900px) {
    width: 100%;
    max-height: none;
  }

  .sidebar-title {
    font-size: 14px;
    font-weight: 600;
    color: #303133;
    display: flex;
    justify-content: space-between;
    align-items: center;

    .layer-count {
      font-size: 12px;
      font-weight: 400;
      color: #909399;
    }
  }

  .sidebar-empty {
    text-align: center;
    padding: 20px;
    color: #909399;
    font-size: 13px;
  }

  .layer-nav {
    display: flex;
    flex-direction: column;
    gap: 6px;

    .layer-nav-item {
      padding: 10px 12px;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s;
      display: flex;
      flex-direction: column;
      gap: 6px;

      &:hover {
        background: #f5f7fa;
      }

      &.active {
        background: #ecf5ff;
        border: 1px solid #b3d8ff;
      }

      .nav-item-top {
        display: flex;
        align-items: center;
        gap: 8px;

        .nav-badge {
          width: 28px;
          height: 28px;
          border-radius: 6px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #fff;
          font-size: 11px;
          font-weight: 700;
          flex-shrink: 0;
        }

        .nav-name {
          flex: 1;
          font-size: 13px;
          color: #303133;
          font-weight: 500;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .nav-pct {
          font-size: 12px;
          color: #909399;
          font-weight: 600;
        }
      }

      .nav-bar {
        height: 4px;
        background: #f0f2f5;
        border-radius: 2px;
        overflow: hidden;

        .nav-bar-fill {
          height: 100%;
          border-radius: 2px;
          transition: width 0.5s ease;
        }
      }
    }
  }
}

// ============================================================
// 右侧详情区
// ============================================================
.detail-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

// ============================================================
// 数据流展示
// ============================================================
.flow-section {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #ebeef5;

  .flow-title {
    font-size: 14px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 16px;
  }

  .flow-chain {
    display: flex;
    flex-direction: column;
    gap: 8px;

    .flow-step {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      background: #f5f7fa;
      border-radius: 8px;

      .flow-node {
        font-size: 12px;
        font-weight: 500;
        white-space: nowrap;

        &.from {
          color: #409eff;
        }
        &.to {
          color: #67c23a;
        }
      }

      .flow-arrow {
        flex: 1;
        display: flex;
        align-items: center;
        gap: 4px;
        min-width: 0;

        .flow-via {
          font-size: 11px;
          color: #909399;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
      }
    }
  }
}

// ============================================================
// 概览卡片网格
// ============================================================
.overview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;

  @media (max-width: 1200px) {
    grid-template-columns: 1fr;
  }
}
</style>
