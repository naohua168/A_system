<template>
  <div class="portfolio-view">
    <div class="page-header">
      <h2>持有</h2>
      <div class="portfolio-summary">
        <div class="summary-item">
          <span class="label">总资产</span>
          <span class="value">¥{{ formatMoney(totalAssets) }}</span>
        </div>
        <div class="summary-item">
          <span class="label">今日收益</span>
          <span class="value" :class="dailyPnL >= 0 ? 'text-rise' : 'text-fall'">
            {{ dailyPnL >= 0 ? '+' : '' }}{{ formatMoney(dailyPnL) }}
          </span>
        </div>
        <div class="summary-item">
          <span class="label">总收益率</span>
          <span class="value" :class="totalReturn >= 0 ? 'text-rise' : 'text-fall'">
            {{ totalReturn >= 0 ? '+' : '' }}{{ totalReturn.toFixed(2) }}%
          </span>
        </div>
      </div>
    </div>

    <!-- 股票持仓 -->
    <section class="section">
      <div class="section-header">
        <h4>股票持仓</h4>
      </div>
      <div class="holding-table" v-if="stockHoldings.length > 0">
        <div class="table-header">
          <span class="col-name">名称</span>
          <span class="col-code">代码</span>
          <span class="col-amount">持有数量</span>
          <span class="col-price">现价</span>
          <span class="col-cost">成本价</span>
          <span class="col-pnl">浮动盈亏</span>
          <span class="col-return">收益率</span>
        </div>
        <div
          v-for="h in stockHoldings"
          :key="h.code"
          class="table-row"
          @click="$router.push(`/stock/${h.code}`)"
        >
          <span class="col-name"><strong>{{ h.name }}</strong></span>
          <span class="col-code caption">{{ h.code }}</span>
          <span class="col-amount">{{ h.shares }}</span>
          <span class="col-price">{{ formatPrice(h.price) }}</span>
          <span class="col-cost caption">{{ formatPrice(h.cost) }}</span>
          <span class="col-pnl" :class="h.pnl >= 0 ? 'text-rise' : 'text-fall'">
            {{ h.pnl >= 0 ? '+' : '' }}{{ formatMoney(h.pnl) }}
          </span>
          <span class="col-return" :class="h.returnRate >= 0 ? 'text-rise' : 'text-fall'">
            {{ h.returnRate >= 0 ? '+' : '' }}{{ h.returnRate.toFixed(2) }}%
          </span>
        </div>
      </div>
      <div v-else class="empty-state">
        <el-icon :size="48" color="#ccc"><Wallet /></el-icon>
        <p>暂无持仓数据</p>
      </div>
    </section>

  </div>
</template>

<script setup lang="ts">
/** 持仓管理 — 基于 localStorage 的本地持仓模拟，用于演示。
 *  实际生产中应对接后端用户持仓表。
 */
import { ref, onMounted } from 'vue'
import { Wallet } from '@element-plus/icons-vue'
import { getStockList } from '@/api/market'
import { formatMoney, formatPrice } from '@/utils/format'

interface Holding {
  code: string; name: string; shares: number
  price: number; cost: number; pnl: number; returnRate: number
  preClose?: number; dailyPnl?: number
}

const STORAGE_KEY = 'portfolio_holdings'

const totalAssets = ref(0)
const dailyPnL = ref(0)
const totalReturn = ref(0)
const stockHoldings = ref<Holding[]>([])

/** 从 localStorage 读取本地持仓配置 */
function loadLocalHoldings(): { stocks: Record<string, { shares: number; cost: number }> } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      return { stocks: parsed.stocks || {} }
    }
  } catch { /* ignore */ }
  return { stocks: { '600519': { shares: 100, cost: 1550 }, '300750': { shares: 500, cost: 185 }, '000858': { shares: 300, cost: 162.5 } } }
}

/** 保存当前持仓配置到 localStorage */
function saveLocalHoldings(stocks: Record<string, { shares: number; cost: number }>) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ stocks }))
}

async function loadData() {
  const local = loadLocalHoldings()

  try {
    const stockRes = await getStockList({ page: 1, size: 50 }) as any
    const codeMap = new Map((stockRes?.records || []).map((r: any) => [r.stockCode, r]))
    let total = 0; const returns: number[] = []
    const holdings: Holding[] = []

    for (const [code, cfg] of Object.entries(local.stocks)) {
      const rec: any = codeMap.get(code)
      if (!rec) continue
      const price = Number(rec.price) || 0
      const preClose = Number(rec.preClose) || 0
      const { shares, cost } = cfg as { shares: number; cost: number }
      const pnl = (price - cost) * shares
      const returnRate = cost > 0 ? ((price - cost) / cost) * 100 : 0
      const dailyPnl = preClose > 0 ? (price - preClose) * shares : pnl
      holdings.push({ code, name: rec.stockName || code, shares, price, cost, pnl, returnRate, dailyPnl, preClose })
      total += price * shares
      returns.push(returnRate)
    }
    stockHoldings.value = holdings
    totalAssets.value = total
    totalReturn.value = returns.length > 0 ? returns.reduce((a, b) => a + b, 0) / returns.length : 0
    dailyPnL.value = holdings.reduce((s, h) => s + (h as any).dailyPnl, 0)
  } catch (_e) {
    console.warn('[Portfolio] 加载股票失败:', _e)
    stockHoldings.value = []
  }
}

onMounted(loadData)
</script>

<style scoped lang="scss">
.portfolio-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: $spacing-lg;
}

.page-header {
  margin-bottom: $spacing-xl;

  h2 { margin-bottom: $spacing-md; }
}

.portfolio-summary {
  display: flex;
  gap: $spacing-lg;

  .summary-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
    .label { font-size: 13px; color: $ink-muted-48; }
    .value { font-family: $font-display; font-size: 24px; font-weight: 600; }
  }
}

.section { margin-bottom: $spacing-xl; }
.section-header { margin-bottom: $spacing-md; h4 { margin: 0; } }

.holding-table {
  background: $canvas;
  border: 1px solid $divider-soft;
  border-radius: $rounded-lg;
  overflow: hidden;

  .table-header {
    display: grid;
    grid-template-columns: 1fr 80px 100px 100px 100px 120px 100px;
    gap: $spacing-sm;
    padding: $spacing-sm $spacing-lg;
    background: $canvas-parchment;
    font-size: 13px;
    color: $ink-muted-48;
  }

  .table-row {
    display: grid;
    grid-template-columns: 1fr 80px 100px 100px 100px 120px 100px;
    gap: $spacing-sm;
    padding: $spacing-md $spacing-lg;
    border-top: 1px solid $divider-soft;
    font-size: 14px;
    cursor: pointer;
    transition: background 0.15s;
    align-items: center;

    &:hover { background: $surface-pearl; }

    .col-code { color: $ink-muted-48; }
  }
}

.empty-state {
  text-align: center;
  padding: $spacing-xxl;
  color: $ink-muted-48;
  p { margin-top: $spacing-sm; font-size: 15px; }
}
</style>
