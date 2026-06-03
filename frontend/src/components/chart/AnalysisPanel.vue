<template>
  <section class="analysis-panel">
    <!-- 头部：标题 + 标签切换 -->
    <div class="panel-header">
      <h4 class="panel-title">涨跌排行</h4>
      <el-radio-group v-model="activeTab" size="small" class="tab-group">
        <el-radio-button value="top_gainers">涨幅榜</el-radio-button>
        <el-radio-button value="top_losers">跌幅榜</el-radio-button>
        <el-radio-button value="high_volume">高换手</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 表头 -->
    <div v-if="!loading && list.length" class="list-header">
      <span class="col-rank">#</span>
      <span class="col-name">名称</span>
      <span class="col-code">代码</span>
      <span class="col-price">价格</span>
      <span class="col-chg">涨跌幅</span>
    </div>

    <!-- 加载态 -->
    <div v-if="loading" class="list-body">
      <div v-for="i in 10" :key="i" class="row skeleton">
        <span class="col-rank sk" />
        <span class="col-name sk" />
        <span class="col-code sk" />
        <span class="col-price sk" />
        <span class="col-chg sk" />
      </div>
    </div>

    <!-- 错误态 -->
    <div v-else-if="error" class="panel-empty">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="empty-icon"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
      <p>{{ error }}</p>
    </div>

    <!-- 空数据态 -->
    <div v-else-if="!list.length" class="panel-empty">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="empty-icon"><polyline points="21 12 7 12 3 8 3 4 21 4 21 12"/><path d="M21 12v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/></svg>
      <p>暂无数据</p>
    </div>

    <!-- 数据列表 -->
    <div v-else class="list-body">
      <div
        v-for="(item, idx) in list"
        :key="item.stockCode"
        class="row"
        @click="goStock(item.stockCode)"
      >
        <span class="col-rank" :class="rankBadge(idx)">{{ idx + 1 }}</span>
        <span class="col-name" :title="item.stockName">{{ item.stockName }}</span>
        <span class="col-code">{{ item.stockCode }}</span>
        <span class="col-price">{{ fmtPrice(item.price) }}</span>
        <span class="col-chg" :class="chgCls(item.changePct)">
          {{ fmtChg(item.changePct) }}
        </span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getMarketAnalysis } from '@/api/market'

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
    list.value = Array.isArray(data) ? data : []
  } catch (e: any) {
    error.value = e?.message || '加载失败'
    list.value = []
  } finally {
    loading.value = false
  }
}

watch(activeTab, () => { list.value = []; loadData() })
onMounted(loadData)

function rankBadge(idx: number): string {
  if (activeTab.value === 'top_losers') {
    if (idx === 0) return 'badge-gold'
    if (idx === 1) return 'badge-silver'
    if (idx === 2) return 'badge-bronze'
    return 'badge-rank'
  }
  if (idx === 0) return 'badge-gold'
  if (idx === 1) return 'badge-silver'
  if (idx === 2) return 'badge-bronze'
  return 'badge-rank'
}

function chgCls(v: any): string {
  const n = Number(v)
  if (n > 0) return 'chg-rise'
  if (n < 0) return 'chg-fall'
  return 'chg-flat'
}

function fmtPrice(v: any): string {
  if (v === undefined || v === null) return '--'
  return Number(v).toFixed(2)
}

function fmtChg(v: any): string {
  const n = Number(v)
  if (isNaN(n)) return '--'
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(2)}%`
}

function goStock(code: string) {
  if (code) router.push(`/stock/${code}`)
}
</script>

<style scoped lang="scss">
.analysis-panel {
  background: var(--el-bg-color);
  border-radius: 10px;
  padding: 16px;
}

/* ── 头部 ── */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0;
}
.tab-group {
  :deep(.el-radio-button__inner) {
    padding: 3px 10px;
    font-size: 12px;
  }
}

/* ── 表头 ── */
.list-header,
.row {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}
.list-header {
  color: var(--el-text-color-secondary);
  padding: 0 4px 6px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  margin-bottom: 2px;
  font-size: 11px;
}

/* ── 行 ── */
.row {
  padding: 5px 4px;
  border-radius: 5px;
  cursor: pointer;
  transition: background 0.15s;
  &:hover {
    background: var(--el-fill-color-light);
  }
}
.col-rank  { width: 26px; text-align: center; flex-shrink: 0; }
.col-name  { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500; }
.col-code  { width: 56px; text-align: center; color: var(--el-text-color-secondary); font-family: 'SF Mono', Consolas, monospace; font-size: 11px; }
.col-price { width: 58px; text-align: right; font-variant-numeric: tabular-nums; }
.col-chg   { width: 66px; text-align: right; font-weight: 600; font-variant-numeric: tabular-nums; }

/* ── 排名徽章 ── */
.badge-gold   { color: #fff; background: linear-gradient(135deg,#f5af19,#f12711); border-radius: 4px; font-weight: 700; }
.badge-silver { color: #fff; background: linear-gradient(135deg,#bdc3c7,#2c3e50); border-radius: 4px; font-weight: 700; }
.badge-bronze { color: #fff; background: linear-gradient(135deg,#cd7f32,#8b4513); border-radius: 4px; font-weight: 700; }
.badge-rank   { color: var(--el-text-color-secondary); font-weight: 500; }

/* ── 涨跌色 ── */
.chg-rise { color: var(--el-color-danger); }
.chg-fall { color: var(--el-color-success); }
.chg-flat { color: var(--el-text-color-secondary); }

/* ── 骨架屏 ── */
.skeleton {
  .sk {
    height: 12px;
    border-radius: 3px;
    background: linear-gradient(90deg, var(--el-fill-color) 25%, var(--el-fill-color-light) 50%, var(--el-fill-color) 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
  }
}
@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ── 空/错误态 ── */
.panel-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  gap: 8px;
  .empty-icon { width: 32px; height: 32px; opacity: 0.4; }
}
</style>
