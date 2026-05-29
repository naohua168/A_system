<template>
  <div class="fund-list-page">
    <!-- 页头 -->
    <div class="page-header glass-card">
      <div class="header-left">
        <div class="header-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
          </svg>
        </div>
        <div>
          <h2>基金</h2>
          <p class="header-subtitle">{{ total }} 只基金 · 最新净值日期 {{ latestNavDate || '--' }}</p>
        </div>
      </div>
      <div class="header-right">
        <div class="search-box">
          <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
          <input v-model="searchQuery" placeholder="搜索基金名称/代码..." @input="handleSearch" />
        </div>
      </div>
    </div>

    <!-- 统计概览栏 -->
    <div class="stats-bar">
      <div v-for="s in fundStats" :key="s.label" class="stat-item glass-card" @click="activeFilter = s.key">
        <span class="stat-value">{{ s.count }}</span>
        <span class="stat-label">{{ s.label }}</span>
        <span v-if="s.key === activeFilter" class="stat-indicator" />
      </div>
    </div>

    <!-- 筛选标签 -->
    <div class="filter-row">
      <button
        v-for="f in fundTypes"
        :key="f.key"
        :class="['filter-chip', { active: activeFilter === f.key }]"
        :style="f.key === activeFilter ? { background: f.gradient } : {}"
        @click="activeFilter = f.key"
      >
        <span class="chip-dot" :style="{ background: f.color }" />
        {{ f.label }}
      </button>
    </div>

    <!-- 加载态 -->
    <template v-if="loading">
      <div class="fund-grid">
        <div v-for="i in 8" :key="i" class="fund-card skeleton">
          <div class="skeleton-line w-40" />
          <div class="skeleton-line w-60 mt-12" />
          <div class="skeleton-row">
            <div class="skeleton-line w-20" />
            <div class="skeleton-line w-24" />
          </div>
          <div class="skeleton-line w-32 mt-12" />
        </div>
      </div>
    </template>

    <!-- 基金卡片网格 -->
    <template v-else-if="filteredFunds.length > 0">
      <div class="fund-grid">
        <div
          v-for="fund in filteredFunds"
          :key="fund.code"
          class="fund-card glass-card"
          :class="{ 'has-negative': (fund.yearReturn ?? 0) < 0 }"
          @click="goToDetail(fund)"
        >
          <div class="card-top">
            <span :class="['type-badge', fund.typeKey]">{{ fund.type }}</span>
            <span class="fund-code">{{ fund.code }}</span>
          </div>
          <h3 class="fund-name">{{ fund.name }}</h3>
          <div class="card-metrics">
            <div class="metric">
              <span class="metric-label">净值</span>
              <span v-if="fund.isMoneyMarket" class="metric-value mono muted">---</span>
              <span v-else class="metric-value mono">{{ fund.nav != null && fund.nav > 0 ? fund.nav.toFixed(4) : '--' }}</span>
            </div>
            <div class="metric-divider" />
            <div class="metric">
              <span class="metric-label">{{ fund.isMoneyMarket ? '7日年化' : (fund.yearReturn != null ? '近1年' : '规模') }}</span>
              <template v-if="fund.isMoneyMarket">
                <span :class="['metric-value', 'mono', (fund.sevenDayYield ?? 0) >= 1 ? '' : 'muted']" style="font-size: 14px;">
                  {{ fund.sevenDayYield != null ? fund.sevenDayYield.toFixed(2) + '%' : '--' }}
                </span>
              </template>
              <template v-else-if="fund.yearReturn != null">
                <span :class="['metric-value', fund.yearReturn >= 0 ? 'text-rise' : 'text-fall']">
                  <svg v-if="fund.yearReturn >= 0" class="trend-icon" width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="m7 14 5-5 5 5H7z"/></svg>
                  <svg v-else class="trend-icon" width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="m7 10 5 5 5-5H7z"/></svg>
                  {{ fund.yearReturn >= 0 ? '+' : '' }}{{ fund.yearReturn.toFixed(2) }}%
                </span>
              </template>
              <span v-else class="metric-value mono">{{ fund.scale > 0 ? fund.scale.toFixed(1) + '亿' : '--' }}</span>
            </div>
          </div>
          <div class="card-footer">
            <span class="footer-item">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
              {{ fund.navDate || '--' }}
            </span>
            <span v-if="fund.manager" class="footer-item">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              {{ fund.manager }}
            </span>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="total > pageSize" class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          :pager-count="5"
          layout="prev, pager, next"
          background
          @current-change="handlePageChange"
        />
      </div>
    </template>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.3">
        <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
      </svg>
      <p>暂无匹配的基金</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getFundList } from '@/api/fund'

interface FundItem {
  code: string
  name: string
  type: string
  typeKey: string
  nav: number | null
  navDate: string
  manager: string
  establishDate: string
  yearReturn: number | null
  scale: number
  isMoneyMarket: boolean
  sevenDayYield: number | null
}

const router = useRouter()
const searchQuery = ref('')
const activeFilter = ref('all')
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const allFunds = ref<FundItem[]>([])
const latestNavDate = ref('')

// 基金类型配置（带颜色标识）
const fundTypes = [
  { key: 'all', label: '全部', color: '#2997ff', gradient: 'linear-gradient(135deg, rgba(41,151,255,0.15), rgba(41,151,255,0.05))' },
  { key: '混合型', label: '混合型', color: '#8b5cf6', gradient: 'linear-gradient(135deg, rgba(139,92,246,0.15), rgba(139,92,246,0.05))' },
  { key: '股票型', label: '股票型', color: '#f59e0b', gradient: 'linear-gradient(135deg, rgba(245,158,11,0.15), rgba(245,158,11,0.05))' },
  { key: '债券型', label: '债券型', color: '#10b981', gradient: 'linear-gradient(135deg, rgba(16,185,129,0.15), rgba(16,185,129,0.05))' },
  { key: '指数型', label: '指数型', color: '#06b6d4', gradient: 'linear-gradient(135deg, rgba(6,182,212,0.15), rgba(6,182,212,0.05))' },
  { key: '货币型', label: '货币型', color: '#ec4899', gradient: 'linear-gradient(135deg, rgba(236,72,153,0.15), rgba(236,72,153,0.05))' },
]

// 统计栏
const fundStats = computed(() => {
  const all = allFunds.value.length
  const counts: Record<string, number> = { all }
  for (const t of fundTypes.slice(1)) {
    counts[t.key] = allFunds.value.filter(f => f.typeKey === t.key).length
  }
  return fundTypes.map(t => ({ key: t.key, label: t.label, count: counts[t.key] ?? 0 }))
})

const filteredFunds = computed(() => {
  let list = allFunds.value
  if (activeFilter.value !== 'all') {
    list = list.filter(f => f.typeKey === activeFilter.value)
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(f => f.code.toLowerCase().includes(q) || f.name.toLowerCase().includes(q))
  }
  return list
})

function goToDetail(row: FundItem) {
  router.push(`/fund/${row.code}`)
}

function handleSearch() {
  currentPage.value = 1
}

function handlePageChange(page: number) {
  currentPage.value = page
  fetchFunds()
}

async function fetchFunds() {
  loading.value = true
  try {
    const res = await getFundList({ page: currentPage.value, size: pageSize.value })
    const pageData = (res as any)?.data || res || {}
    const records = pageData?.records || pageData || []
    const items = (Array.isArray(records) ? records : []).map((r: any) => {
      const t = r.fundType || r.type || ''
      return {
        code: r.fundCode || r.code || '',
        name: r.fundName || r.name || '',
        type: t,
        typeKey: mapType(t),
        nav: r.nav ?? null,
        navDate: r.navDate || '--',
        manager: r.manager || '',
        establishDate: r.establishDate || '',
        yearReturn: r.yearReturn ?? null,
        scale: r.scale ?? 0,
        isMoneyMarket: !!r.isMoneyMarket,
        sevenDayYield: r.sevenDayYield ?? null,
      }
    })
    if (items.length > 0) {
      const dates = items.map(i => i.navDate).filter(d => d && d !== '--').sort().reverse()
      if (dates.length > 0) latestNavDate.value = dates[0]
    }
    allFunds.value = items
    total.value = pageData?.total || items.length
  } catch {
    allFunds.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function mapType(type: string): string {
  if (!type) return 'other'
  if (type.includes('混合')) return '混合型'
  if (type.includes('股票')) return '股票型'
  if (type.includes('债券') || type.includes('债')) return '债券型'
  if (type.includes('指数')) return '指数型'
  if (type.includes('货币')) return '货币型'
  return 'other'
}

onMounted(async () => {
  fetchFunds()
})
</script>

<style scoped lang="scss">
.fund-list-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

// ── Glass Card ──
.glass-card {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 14px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
}

// ── Page Header ──
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  margin-bottom: 16px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 14px;

    .header-icon {
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 10px;
      background: linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(245, 158, 11, 0.05));
      color: #f59e0b;
    }

    h2 {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
      color: #1a1a2e;
    }

    .header-subtitle {
      margin: 2px 0 0;
      font-size: 12px;
      color: rgba(0, 0, 0, 0.4);
    }
  }

  .search-box {
    position: relative;
    width: 260px;

    .search-icon {
      position: absolute;
      left: 12px;
      top: 50%;
      transform: translateY(-50%);
      color: rgba(0, 0, 0, 0.3);
      pointer-events: none;
    }

    input {
      width: 100%;
      padding: 8px 12px 8px 36px;
      background: rgba(0, 0, 0, 0.04);
      border: 1px solid rgba(0, 0, 0, 0.08);
      border-radius: 8px;
      color: #1a1a2e;
      font-size: 13px;
      outline: none;
      transition: all 0.2s;

      &::placeholder { color: rgba(0, 0, 0, 0.25); }
      &:focus { border-color: rgba(41, 151, 255, 0.4); background: rgba(41, 151, 255, 0.04); }
    }
  }
}

// ── Stats Bar ──
.stats-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
  overflow-x: auto;
  scrollbar-width: none;
  &::-webkit-scrollbar { display: none; }
}

.stat-item {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 12px 20px;
  min-width: 80px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;

  &:hover { background: rgba(41, 151, 255, 0.06); }

  .stat-value {
    font-size: 22px;
    font-weight: 700;
    font-family: 'SF Mono', 'Fira Code', monospace;
    color: #1a1a2e;
    position: relative;
  }

  .stat-label {
    font-size: 11px;
    color: rgba(0, 0, 0, 0.4);
    position: relative;
  }

  .stat-indicator {
    position: absolute;
    bottom: -1px;
    left: 50%;
    transform: translateX(-50%);
    width: 20px;
    height: 2px;
    background: #2997ff;
    border-radius: 1px;
  }
}

// ── Filter Row ──
.filter-row {
  display: flex;
  gap: 6px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 20px;
  background: transparent;
  color: rgba(0, 0, 0, 0.5);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;

  .chip-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  &:hover {
    color: #1a1a2e;
    border-color: rgba(0, 0, 0, 0.2);
    background: rgba(0, 0, 0, 0.03);
  }

  &.active {
    color: #1a1a2e;
    border-color: transparent;
    font-weight: 500;
  }
}

// ── Fund Grid ──
.fund-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.fund-card {
  padding: 18px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94);

  &:hover {
    transform: translateY(-2px);
    border-color: rgba(41, 151, 255, 0.2);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);

    .fund-name { color: #1a1a2e; }
  }

  &.skeleton { pointer-events: none; }

  .card-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .type-badge {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 500;
    line-height: 1.4;

    &.混合型 { background: rgba(139,92,246,0.12); color: #a78bfa; }
    &.股票型 { background: rgba(245,158,11,0.12); color: #fbbf24; }
    &.债券型 { background: rgba(16,185,129,0.12); color: #34d399; }
    &.指数型 { background: rgba(6,182,212,0.12); color: #22d3ee; }
    &.货币型 { background: rgba(236,72,153,0.12); color: #f472b6; }
    &.other   { background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.4); }
  }

  .fund-code {
    font-size: 11px;
    color: rgba(0, 0, 0, 0.3);
    font-family: 'SF Mono', 'Fira Code', monospace;
  }

  .fund-name {
    font-size: 14px;
    font-weight: 600;
    color: #1a1a2e;
    margin: 0 0 14px;
    line-height: 1.3;
    transition: color 0.2s;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .card-metrics {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 14px;
  }

  .metric {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .metric-label {
    font-size: 10px;
    color: rgba(0, 0, 0, 0.35);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .metric-value {
    font-size: 16px;
    font-weight: 600;
    color: #1a1a2e;
    display: flex;
    align-items: center;
    gap: 2px;

    &.mono { font-family: 'SF Mono', 'Fira Code', monospace; }
    &.muted { color: rgba(0, 0, 0, 0.25); }
  }

  .trend-icon { flex-shrink: 0; }

  .metric-divider {
    width: 1px;
    height: 32px;
    background: rgba(0, 0, 0, 0.08);
    flex-shrink: 0;
  }

  .card-footer {
    display: flex;
    gap: 12px;

    .footer-item {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 11px;
      color: rgba(0, 0, 0, 0.35);

      svg { opacity: 0.35; }
    }
  }
}

// ── Skeleton ──
.skeleton-line {
  height: 12px;
  background: rgba(0, 0, 0, 0.06);
  border-radius: 4px;
  animation: shimmer 1.5s infinite ease-in-out;

  &.w-20 { width: 60px; }
  &.w-24 { width: 72px; }
  &.w-32 { width: 96px; }
  &.w-40 { width: 120px; }
  &.w-60 { width: 180px; }

  &.mt-12 { margin-top: 12px; }
}

.skeleton-row {
  display: flex;
  gap: 12px;
  margin-top: 14px;
}

@keyframes shimmer {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

// ── Pagination ──
.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 8px;
}

// ── Empty State ──
.empty-state {
  text-align: center;
  padding: 80px 0;
  color: rgba(0, 0, 0, 0.25);
  font-size: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

// ── Color Helpers ──
.text-rise { color: #f59e0b; }
.text-fall { color: #10b981; }
</style>
