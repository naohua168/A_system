<template>
  <div class="watchlist-view">
    <div class="page-header">
      <h2>自选</h2>
    </div>

    <!-- 股票自选 -->
    <div class="watchlist-content">
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
            <el-button text type="primary" size="small" @click.stop="removeWatchlistItem(s.code)">
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

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Star, Delete } from '@element-plus/icons-vue'
import { getStockList } from '@/api/market'
import { getWatchlist, removeWatchlist as apiRemoveWatchlist } from '@/api/watchlist'
import { useUserStore } from '@/stores/user'
import { formatPrice, getChangeClass, formatVolume } from '@/utils/format'

const userStore = useUserStore()

interface WatchStock {
  code: string; name: string; price: number
  changePercent: number; high: number; low: number; volume: number
}

const stockWatchlist = ref<WatchStock[]>([])

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

async function removeWatchlistItem(code: string) {
  if (!userStore.isLoggedIn) return
  try {
    await apiRemoveWatchlist(userStore.userInfo!.id, code, 0)
    stockWatchlist.value = stockWatchlist.value.filter(s => s.code !== code)
  } catch (_e) { console.warn('[Watchlist] 移除自选失败:', _e) }
}

onMounted(() => {
  if (userStore.isLoggedIn) {
    loadStocks()
  }
})
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

.empty-state {
  text-align: center;
  padding: $spacing-xxl;
  color: $ink-muted-48;
  p { margin: $spacing-sm 0 $spacing-md; font-size: 15px; }
}
</style>
