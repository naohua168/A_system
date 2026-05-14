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

    <!-- 基金持仓 -->
    <section class="section">
      <div class="section-header">
        <h4>基金持仓</h4>
      </div>
      <div class="fund-grid" v-if="fundHoldings.length > 0">
        <div v-for="f in fundHoldings" :key="f.code"
          class="fund-card"
          @click="$router.push(`/fund/${f.code}`)"
        >
          <div class="fund-header">
            <h4>{{ f.name }}</h4>
            <span class="caption">{{ f.code }}</span>
          </div>
          <div class="fund-body">
            <div class="fund-stat">
              <span class="label">持有份额</span>
              <span class="val">{{ f.shares.toFixed(2) }}</span>
            </div>
            <div class="fund-stat">
              <span class="label">最新净值</span>
              <span class="val">{{ f.nav.toFixed(4) }}</span>
            </div>
          </div>
          <div class="fund-footer">
            <span class="fund-pnl" :class="f.pnl >= 0 ? 'text-rise' : 'text-fall'">
              收益: {{ f.pnl >= 0 ? '+' : '' }}{{ formatMoney(f.pnl) }}
            </span>
            <span class="fund-return" :class="f.returnRate >= 0 ? 'text-rise' : 'text-fall'">
              {{ f.returnRate >= 0 ? '+' : '' }}{{ f.returnRate.toFixed(2) }}%
            </span>
          </div>
        </div>
      </div>
      <div v-else class="empty-state">
        <el-icon :size="48" color="#ccc"><Coin /></el-icon>
        <p>暂无基金持仓</p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Wallet, Coin } from '@element-plus/icons-vue'
import { getStockList } from '@/api/stock'
import { getFundList } from '@/api/fund'
import { formatMoney, formatPrice } from '@/utils/format'

const totalAssets = ref(0)
const dailyPnL = ref(0)
const totalReturn = ref(0)

interface Holding {
  code: string; name: string; shares: number
  price: number; cost: number; pnl: number; returnRate: number
}

const stockHoldings = ref<Holding[]>([])
const fundHoldings = ref<{ code: string; name: string; shares: number; nav: number; pnl: number; returnRate: number }[]>([])

async function loadData() {
  try {
    const res: any = await getStockList({ page: 1, size: 5 })
    if (res?.records?.length) {
      const defaultShares: Record<string, number> = { '600519': 100, '300750': 500, '000858': 300 }
      const defaultCost: Record<string, number> = { '600519': 1550, '300750': 185, '000858': 162.5 }
      stockHoldings.value = res.records.slice(0, 3).map((r: any) => {
        const code = r.stockCode; const price = Number(r.price) || 0
        const shares = defaultShares[code] || 100; const cost = defaultCost[code] || price * 0.95
        return { code, name: r.stockName, shares, price, cost, pnl: (price - cost) * shares, returnRate: cost ? ((price - cost) / cost) * 100 : 0 }
      })
      // 计算汇总
      const total = stockHoldings.value.reduce((s, h) => s + h.price * h.shares, 0)
      totalAssets.value = total
      totalReturn.value = stockHoldings.value.reduce((s, h) => s + h.returnRate, 0) / stockHoldings.value.length
      dailyPnL.value = stockHoldings.value.reduce((s, h) => s + h.pnl, 0)
    }
  } catch (_e) {
    console.warn('[Portfolio] 加载股票失败:', _e)
    stockHoldings.value = []
  }
  try {
    const res: any = await getFundList({ page: 1, size: 5 })
    if (res?.records?.length) {
      fundHoldings.value = res.records.slice(0, 2).map((r: any) => {
        const nav = Number(r.nav) || 1; const shares = 5000; const cost = nav * 0.95
        return { code: r.fundCode || r.code, name: r.fundName || r.name || '', shares, nav, pnl: (nav - cost) * shares, returnRate: ((nav - cost) / cost) * 100 }
      })
    }
  } catch (_e) { console.warn('[Portfolio] 加载基金失败:', _e) }
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

.fund-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $spacing-md;

  .fund-card {
    background: $canvas;
    border: 1px solid $divider-soft;
    border-radius: $rounded-lg;
    padding: $spacing-lg;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      transform: translateY(-2px);
      box-shadow: $shadow-elevated;
    }

    .fund-header {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: $spacing-md;

      h4 { font-size: 16px; margin: 0; }
      .caption { color: $ink-muted-48; }
    }

    .fund-body {
      display: flex;
      gap: $spacing-xl;
      margin-bottom: $spacing-md;

      .fund-stat {
        display: flex;
        flex-direction: column;
        gap: 2px;
        .label { font-size: 12px; color: $ink-muted-48; }
        .val { font-family: $font-display; font-size: 16px; font-weight: 600; }
      }
    }

    .fund-footer {
      display: flex;
      gap: $spacing-lg;
      font-size: 14px;
      font-weight: 500;
    }
  }
}

.empty-state {
  text-align: center;
  padding: $spacing-xxl;
  color: $ink-muted-48;
  p { margin-top: $spacing-sm; font-size: 15px; }
}
</style>
