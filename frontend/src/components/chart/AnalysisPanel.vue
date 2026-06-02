<template>
  <section class="section analysis-section">
    <div class="section-header">
      <h4>涨跌排行</h4>
      <el-radio-group v-model="activeTab" size="small" class="tab-switch">
        <el-radio-button value="top_gainers">涨幅榜</el-radio-button>
        <el-radio-button value="top_losers">跌幅榜</el-radio-button>
        <el-radio-button value="high_volume">高换手</el-radio-button>
      </el-radio-group>
    </div>
    <template v-if="loading">
      <div class="analysis-grid">
        <div v-for="i in 10" :key="i" class="analysis-item skeleton-item">
          <div class="sk-rank" />
          <div class="sk-name" />
          <div class="sk-price" />
        </div>
      </div>
    </template>
    <template v-else-if="error">
      <EmptyState type="error" title="加载失败" :desc="error" inline size="sm" />
    </template>
    <template v-else-if="!list.length">
      <EmptyState type="empty" title="暂无数据" inline size="sm" />
    </template>
    <template v-else>
      <div class="analysis-grid">
        <div
          v-for="(item, idx) in list.slice(0, 15)"
          :key="item.stockCode || item.stock_code"
          class="analysis-item"
          @click="goStock(item.stockCode || item.stock_code)"
        >
          <span class="rank" :class="rankClass(idx)">{{ idx + 1 }}</span>
          <span class="name">{{ item.stockName || item.stock_name }}</span>
          <span class="price">{{ fmtPrice(item.price) }}</span>
          <span class="change" :class="changeClass(item.changePct ?? item.change_pct)">
            {{ fmtPercent(item.changePct ?? item.change_pct) }}
          </span>
        </div>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getMarketAnalysis } from '@/api/market'
import { formatPrice, formatPercent } from '@/utils/format'
import EmptyState from '@/components/common/EmptyState.vue'

const router = useRouter()
const activeTab = ref<'top_gainers' | 'top_losers' | 'high_volume'>('top_gainers')
const list = ref<any[]>([])
const loading = ref(true)
const error = ref('')

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const data = await getMarketAnalysis(activeTab.value)
    if (Array.isArray(data)) {
      list.value = data
    } else if (data && Array.isArray((data as any).records)) {
      list.value = (data as any).records
    } else {
      list.value = []
    }
  } catch (e: any) {
    error.value = e?.message || '请求失败'
    list.value = []
  } finally {
    loading.value = false
  }
}

watch(activeTab, loadData)
onMounted(loadData)

function rankClass(idx: number) {
  if (activeTab.value === 'top_losers') {
    if (idx < 3) return 'rank-bad'
    return ''
  }
  if (idx < 3) return 'rank-good'
  return ''
}

function changeClass(val: number | string) {
  const n = Number(val)
  if (n > 0) return 'rise'
  if (n < 0) return 'fall'
  return ''
}

function fmtPrice(v: any) {
  return v ? formatPrice(Number(v)) : '--'
}

function fmtPercent(v: any) {
  const n = Number(v)
  if (v === undefined || v === null || isNaN(n)) return '--'
  return (n > 0 ? '+' : '') + n.toFixed(2) + '%'
}

function goStock(code: string | number) {
  router.push(`/stock/${code}`)
}
</script>

<style scoped lang="scss">
.analysis-section {
  margin-top: 8px;
}
.tab-switch {
  :deep(.el-radio-button__inner) {
    padding: 4px 12px;
    font-size: 12px;
  }
}
.analysis-grid {
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 2px;
  margin-top: 12px;
}
.analysis-item {
  display: flex;
  align-items: center;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  gap: 8px;
  &:hover { background: var(--el-fill-color-light); }
  .rank {
    width: 22px; height: 22px; line-height: 22px; text-align: center;
    border-radius: 4px; font-size: 11px; font-weight: 600; flex-shrink: 0;
    background: var(--el-fill-color);
    &.rank-good { background: var(--el-color-danger-light-7); color: var(--el-color-danger); }
    &.rank-bad  { background: var(--el-color-success-light-7); color: var(--el-color-success); }
  }
  .name {
    flex: 1; font-size: 13px; font-weight: 500;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .price { font-size: 12px; color: var(--el-text-color-secondary); width: 60px; text-align: right; }
  .change { font-size: 12px; font-weight: 600; width: 70px; text-align: right; }
}
.rise { color: var(--el-color-danger); }
.fall { color: var(--el-color-success); }

/* Skeleton */
.skeleton-item {
  .sk-rank, .sk-name, .sk-price {
    height: 14px; border-radius: 4px;
    background: linear-gradient(90deg, var(--el-fill-color) 25%, var(--el-fill-color-light) 50%, var(--el-fill-color) 75%);
    background-size: 200% 100%; animation: shimmer 1.5s infinite;
  }
  .sk-rank { width: 22px; }
  .sk-name { flex: 1; }
  .sk-price { width: 50px; }
}
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
</style>
