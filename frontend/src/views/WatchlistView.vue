<template>
  <div class="watchlist-view">
    <div class="page-header">
      <h2>自选</h2>
      <div class="tabs">
        <button
          :class="['tab-btn', { active: activeTab === 'stock' }]"
          @click="activeTab = 'stock'"
        >股票自选</button>
        <button
          :class="['tab-btn', { active: activeTab === 'fund' }]"
          @click="activeTab = 'fund'"
        >基金自选</button>
      </div>
    </div>

    <!-- 股票自选 -->
    <div v-show="activeTab === 'stock'" class="watchlist-content">
      <div class="watchlist-table" v-if="stockWatchlist.length > 0">
        <div class="table-header">
          <span class="col-name">名称</span>
          <span class="col-code">代码</span>
          <span class="col-price">现价</span>
          <span class="col-chg">涨跌幅</span>
          <span class="col-high">最高</span>
          <span class="col-low">最低</span>
          <span class="col-vol">成交量</span>
          <span class="col-action">操作</span>
        </div>
        <div
          v-for="s in stockWatchlist"
          :key="s.code"
          class="table-row"
          :class="getChangeClass(s.changePercent)"
        >
          <span class="col-name" @click="$router.push(`/stock/${s.code}`)"><strong>{{ s.name }}</strong></span>
          <span class="col-code caption">{{ s.code }}</span>
          <span class="col-price">{{ formatPrice(s.price) }}</span>
          <span class="col-chg">
            <span class="change-badge">{{ s.changePercent >= 0 ? '+' : '' }}{{ s.changePercent.toFixed(2) }}%</span>
          </span>
          <span class="col-high">{{ formatPrice(s.high) }}</span>
          <span class="col-low">{{ formatPrice(s.low) }}</span>
          <span class="col-vol caption">{{ formatVolume(s.volume) }}</span>
          <span class="col-action">
            <el-button text type="primary" size="small" @click.stop="removeWatchlistItem(s.code, 'stock')">
              <el-icon><Delete /></el-icon>
            </el-button>
          </span>
        </div>
      </div>
      <div v-else class="empty-state">
        <el-icon :size="48" color="#ccc"><Star /></el-icon>
        <p>还没有添加自选股票</p>
        <el-button type="primary" @click="$router.push('/stocks')">去添加</el-button>
      </div>
    </div>

    <!-- 基金自选 -->
    <div v-show="activeTab === 'fund'" class="watchlist-content">
      <div class="fund-grid" v-if="fundWatchlist.length > 0">
        <div v-for="f in fundWatchlist" :key="f.code" class="fund-card"
          @click="$router.push(`/fund/${f.code}`)"
        >
          <div class="fund-header">
            <h4>{{ f.name }}</h4>
            <el-button text type="primary" size="small" @click.stop="removeWatchlistItem(f.code, 'fund')">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
          <div class="fund-meta">
            <span class="caption">{{ f.code }} · {{ f.type }}</span>
          </div>
          <div class="fund-body">
            <div class="fund-stat">
              <span class="label">最新净值</span>
              <span class="val">{{ f.nav.toFixed(4) }}</span>
            </div>
            <div class="fund-stat">
              <span class="label">累计净值</span>
              <span class="val">{{ f.accNav.toFixed(4) }}</span>
            </div>
            <div class="fund-stat">
              <span class="label">日涨跌</span>
              <span class="val" :class="f.dailyReturn >= 0 ? 'text-rise' : 'text-fall'">
                {{ f.dailyReturn >= 0 ? '+' : '' }}{{ (f.dailyReturn * 100).toFixed(2) }}%
              </span>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="empty-state">
        <el-icon :size="48" color="#ccc"><Coin /></el-icon>
        <p>还没有添加自选基金</p>
        <el-button type="primary" @click="$router.push('/stocks')">去添加</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Star, Coin, Delete } from '@element-plus/icons-vue'
import { getStockList } from '@/api/stock'
import { getFundList, getFundNav } from '@/api/fund'
import { getWatchlist, removeWatchlist as apiRemoveWatchlist } from '@/api/watchlist'
import { useUserStore } from '@/stores/user'
import { formatPrice, getChangeClass } from '@/utils/format'

const userStore = useUserStore()
const activeTab = ref('stock')

interface WatchStock {
  code: string; name: string; price: number
  changePercent: number; high: number; low: number; volume: number
}

const stockWatchlist = ref<WatchStock[]>([])
const fundWatchlist = ref<{ code: string; name: string; type: string; nav: number; accNav: number; dailyReturn: number }[]>([])

async function loadStocks() {
  if (!userStore.isLoggedIn) return
  try {
    // 1. 获取用户的自选列表
    const watchlistItems: any = await getWatchlist(userStore.userInfo!.id, 0)
    if (!Array.isArray(watchlistItems) || watchlistItems.length === 0) {
      stockWatchlist.value = []
      return
    }
    // 2. 批量查询股票行情（通过搜索接口批量获取）
    const stockCodes = watchlistItems.map((w: any) => w.assetCode)
    const res: any = await getStockList({ page: 1, size: 50 })
    if (res?.records?.length) {
      stockWatchlist.value = res.records
        .filter((r: any) => stockCodes.includes(r.stockCode))
        .map((r: any) => ({
          code: r.stockCode,
          name: r.stockName,
          price: r.price || 0,
          changePercent: r.changePct || 0,
          high: r.highPrice || r.price || 0,
          low: r.lowPrice || r.price || 0,
          volume: r.volume || 0,
        }))
    }
  } catch (_e) {
    console.warn('[Watchlist] 加载自选股票失败:', _e)
  }
}

async function loadFunds() {
  if (!userStore.isLoggedIn) return
  try {
    const watchlistItems: any = await getWatchlist(userStore.userInfo!.id, 1)
    if (!Array.isArray(watchlistItems) || watchlistItems.length === 0) {
      fundWatchlist.value = []
      return
    }
    const items: any[] = []
    for (const w of watchlistItems.slice(0, 6)) {
      const code = w.assetCode
      try {
        const info: any = await getFundList({ page: 1, size: 10 })
        const fundInfo = Array.isArray(info?.records) ? info.records.find((r: any) => (r.fundCode || r.code) === code) : null
        let nav = fundInfo ? Number(fundInfo.nav) : 1
        let accNav = fundInfo ? Number(fundInfo.accumulatedNav) : nav
        let dailyReturn = 0
        try {
          const navData: any = await getFundNav(code, { days: 2 })
          if (Array.isArray(navData) && navData.length >= 2) {
            const last = navData[navData.length - 1]
            const prev = navData[navData.length - 2]
            nav = Number(last.nav) || nav
            accNav = Number(last.accumulatedNav) || accNav
            dailyReturn = (Number(last.nav) - Number(prev.nav)) / Number(prev.nav)
          }
        } catch (_) { console.warn('[Watchlist] 加载基金净值失败:', _) }
        items.push({
          code,
          name: fundInfo?.fundName || fundInfo?.name || code,
          type: fundInfo?.fundType || '',
          nav, accNav, dailyReturn,
        })
      } catch (_) { console.warn('[Watchlist] 跳过基金:', _) }
    }
    fundWatchlist.value = items
  } catch (_e) { console.warn('[Watchlist] 加载基金自选失败:', _e) }
}

async function removeWatchlistItem(code: string, type: 'stock' | 'fund') {
  if (!userStore.isLoggedIn) return
  try {
    await apiRemoveWatchlist(userStore.userInfo!.id, code, type === 'stock' ? 0 : 1)
    if (type === 'stock') {
      stockWatchlist.value = stockWatchlist.value.filter(s => s.code !== code)
    } else {
      fundWatchlist.value = fundWatchlist.value.filter(f => f.code !== code)
    }
  } catch (_e) { console.warn('[Watchlist] 移除自选失败:', _e) }
}

onMounted(() => {
  if (userStore.isLoggedIn) {
    loadStocks()
    loadFunds()
  }
})



function removeWatchlist(code: string, type: string) {
  if (type === 'stock') {
    const idx = stockWatchlist.value.findIndex(s => s.code === code)
    if (idx >= 0) stockWatchlist.value.splice(idx, 1)
  } else {
    const idx = fundWatchlist.value.findIndex(f => f.code === code)
    if (idx >= 0) fundWatchlist.value.splice(idx, 1)
  }
}
</script>

<style scoped lang="scss">
.watchlist-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: $spacing-lg;
}

.page-header {
  margin-bottom: $spacing-lg;
  h2 { margin-bottom: $spacing-md; }
}

.tabs {
  display: flex;
  gap: $spacing-xs;

  .tab-btn {
    padding: 8px 20px;
    border: 1px solid $hairline;
    background: $canvas;
    border-radius: $rounded-pill;
    font-size: 14px;
    color: $ink-muted-48;
    cursor: pointer;
    transition: all 0.2s;

    &:hover { border-color: $primary; color: $primary; }
    &.active {
      background: $primary;
      border-color: $primary;
      color: white;
    }
  }
}

.watchlist-table {
  background: $canvas;
  border: 1px solid $divider-soft;
  border-radius: $rounded-lg;
  overflow: hidden;

  .table-header {
    display: grid;
    grid-template-columns: 1fr 80px 100px 100px 100px 100px 120px 60px;
    gap: $spacing-sm;
    padding: $spacing-sm $spacing-lg;
    background: $canvas-parchment;
    font-size: 13px;
    color: $ink-muted-48;
  }

  .table-row {
    display: grid;
    grid-template-columns: 1fr 80px 100px 100px 100px 100px 120px 60px;
    gap: $spacing-sm;
    padding: $spacing-md $spacing-lg;
    border-top: 1px solid $divider-soft;
    font-size: 14px;
    align-items: center;
    transition: background 0.15s;

    &:hover { background: $surface-pearl; }

    .col-name {
      cursor: pointer;
      &:hover { color: $primary; }
    }

    .col-code { color: $ink-muted-48; }

    &.rise .col-price, &.rise .col-chg { color: $rise; }
    &.fall .col-price, &.fall .col-chg { color: $fall; }

    .change-badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: $rounded-xs;
      font-size: 13px;
      font-weight: 500;
    }

    &.rise .change-badge { background: $rise-bg; color: $rise; }
    &.fall .change-badge { background: $fall-bg; color: $fall; }
  }
}

.fund-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: $spacing-md;

  .fund-card {
    background: $canvas;
    border: 1px solid $divider-soft;
    border-radius: $rounded-lg;
    padding: $spacing-lg;
    cursor: pointer;
    transition: all 0.2s;

    &:hover { transform: translateY(-2px); box-shadow: $shadow-elevated; }

    .fund-header { display: flex; justify-content: space-between; align-items: center; h4 { font-size: 16px; margin: 0; } }
    .fund-meta { margin: 6px 0 $spacing-md; }
    .fund-body { display: flex; gap: $spacing-lg; }
    .fund-stat { display: flex; flex-direction: column; gap: 2px;
      .label { font-size: 12px; color: $ink-muted-48; }
      .val { font-size: 16px; font-weight: 600; }
    }
  }
}

.empty-state {
  text-align: center;
  padding: $spacing-xxl;
  color: $ink-muted-48;
  p { margin: $spacing-sm 0 $spacing-md; font-size: 15px; }
}
</style>
