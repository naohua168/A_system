<template>
  <div class="dt-page">
    <!-- 顶栏 -->
    <header class="dt-top">
      <h1>龙虎榜</h1>
      <div class="dt-toolbar">
        <ReviewDatePicker @change="(d:string) => { reviewDate.value = d; fetchData() }" />
        <span class="today-label">{{ reviewDate ? reviewDate : '今日 · ' + todayStr }}</span>
        <el-button v-if="error" type="warning" size="small" @click="fetchData" :loading="loading">重试</el-button>
        <el-button size="small" text @click="fetchData" :loading="loading" v-else>刷新</el-button>
      </div>
    </header>

    <!-- 骨架 -->
    <template v-if="loading">
      <div class="dt-sk" v-for="i in 6" :key="i"></div>
    </template>

    <!-- 错误 -->
    <div v-else-if="error" class="dt-empty">
      <p>加载失败</p>
      <el-button size="small" @click="fetchData">重试</el-button>
    </div>

    <!-- 空 -->
    <div v-else-if="!records.length" class="dt-empty">
      <p>今日暂无龙虎榜数据，收盘后更新</p>
      <el-button size="small" @click="fetchData">刷新</el-button>
    </div>

    <!-- 正常数据 -->
    <template v-else>
      <!-- ① 概览统计 -->
      <section class="dt-summary">
        <div class="dt-sum-item">
          <span class="dt-sum-v">{{ records.length }}</span>
          <span class="dt-sum-l">上榜个股</span>
        </div>
        <div class="dt-sum-div" />
        <div class="dt-sum-item">
          <span class="dt-sum-v" :class="totalNet >= 0 ? 'text-rise' : 'text-fall'">{{ totalNet >= 0 ? '+' : '' }}{{ toYi(totalNet) }}</span>
          <span class="dt-sum-l">净买入总额</span>
        </div>
        <div class="dt-sum-div" />
        <div class="dt-sum-item">
          <span class="dt-sum-v text-rise">{{ zhangTingCount }}</span>
          <span class="dt-sum-l">涨停</span>
        </div>
        <div class="dt-sum-div" />
        <div class="dt-sum-item">
          <span class="dt-sum-v" :class="bullRatio >= 50 ? 'text-rise' : 'text-fall'">{{ bullRatio }}%</span>
          <span class="dt-sum-l">多头占比</span>
        </div>
        <div class="dt-sum-div" />
        <div class="dt-sum-item highlight">
          <span class="dt-sum-v text-primary">{{ maxBuyName }}</span>
          <span class="dt-sum-l">净买入最多 · {{ maxBuyYi }}亿</span>
        </div>
      </section>

      <!-- ② TOP4 资金卡片 -->
      <section class="dt-cards">
        <div v-for="c in topCards" :key="c.stockCode" class="dt-card"
          :class="c.net >= 0 ? 'card-buy' : 'card-sell'"
          @click="goToStock(c.stockCode)">
          <div class="card-badge">{{ c.net >= 0 ? '买入' : '卖出' }}</div>
          <div class="card-name">{{ c.stockName }}</div>
          <div class="card-code">{{ c.stockCode }}</div>
          <div class="card-net" :class="c.net >= 0 ? 'text-rise' : 'text-fall'">{{ c.net >= 0 ? '+' : '' }}{{ c.yi }}亿</div>
          <div class="card-sub">
            <span :class="c.chg >= 0 ? 'text-rise' : 'text-fall'">{{ c.chg >= 0 ? '+' : '' }}{{ c.chg.toFixed(2) }}%</span>
            <span>换手 {{ c.turnover.toFixed(2) }}%</span>
          </div>
          <div class="card-bar">
            <div class="card-bar-fill" :style="{ width: c.ratio + '%', background: c.net >= 0 ? '#D93026' : '#34A853' }" />
          </div>
        </div>
      </section>

      <!-- ③ 明细表格 -->
      <section class="dt-table-wrap">
        <div class="dt-tbl-header">
          <h3>龙虎榜明细</h3>
          <el-input v-model="searchQuery" placeholder="搜索股票" size="small" clearable style="width:180px" prefix-icon="Search" />
        </div>
        <el-table :data="filteredRows" stripe size="small" style="width:100%"
          :header-cell-style="{ background: '#f5f6fa', color: '#666', fontWeight: 500, fontSize: '12px', padding: '10px 8px' }"
          :cell-style="{ padding: '8px 6px' }"
          @row-click="goToStock">
          <el-table-column label="#" type="index" width="40" align="center" />
          <el-table-column label="代码" width="80">
            <template #default="{ row }">
              <span class="dt-code">{{ row.stockCode }}</span>
            </template>
          </el-table-column>
          <el-table-column label="名称" width="80" prop="stockName" />
          <el-table-column label="涨幅%" width="75" align="right">
            <template #default="{ row }">
              <span :class="(row.changePct || 0) >= 0 ? 'text-rise' : 'text-fall'"
                :style="(row.changePct || 0) >= 9.9 ? 'font-weight:700' : ''">
                {{ (row.changePct || 0) >= 0 ? '+' : '' }}{{ safeNum(row.changePct, 2) }}%
              </span>
            </template>
          </el-table-column>
          <el-table-column label="净买入(亿)" width="110" align="right" sortable prop="netBuyWan">
            <template #default="{ row }">
              <span :class="(row.netBuyWan || 0) >= 0 ? 'text-rise' : 'text-fall'" style="font-weight:600">
                {{ (row.netBuyWan || 0) >= 0 ? '+' : '' }}{{ toYi(row.netBuyWan) }}
              </span>
              <!-- 买卖比进度条 -->
              <div class="dt-bar-mini">
                <div class="dt-bar-mini-track">
                  <div class="dt-bar-mini-fill" :style="{ width: buyRatio(row) + '%', background: row.netBuyWan >= 0 ? '#D93026' : '#34A853' }" />
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="总买入(亿)" width="95" align="right">
            <template #default="{ row }">
              <span class="text-rise">{{ safeNum(row.buyWan / 1e8, 2) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="总卖出(亿)" width="95" align="right">
            <template #default="{ row }">
              <span class="text-fall">{{ safeNum(row.sellWan / 1e8, 2) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="买卖比" width="75" align="right">
            <template #default="{ row }">
              {{ buyRatio(row) }}%
            </template>
          </el-table-column>
          <el-table-column label="换手率%" width="80" align="right">
            <template #default="{ row }">
              {{ safeNum(row.turnoverPct, 2) }}%
            </template>
          </el-table-column>
        </el-table>
        <div class="dt-stats">共 <strong>{{ filteredRows.length }}</strong> 只个股上榜 · 点击行可查看个股详情</div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getDragonTigerDaily, getHistoryDragonTiger } from '@/api/signal'
import { useApiRetry, safeRecords, safeNum, safeStr } from '@/composables/useApiRetry'
import { useAutoRefresh } from '@/composables/useAutoRefresh'
import ReviewDatePicker from '@/components/common/ReviewDatePicker.vue'

const router = useRouter()
const todayStr = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
const reviewDate = ref('')
const searchQuery = ref('')

const { data: rawData, loading, error, fetch: fetchData } = useApiRetry(
  () => reviewDate.value ? getHistoryDragonTiger(reviewDate.value) : getDragonTigerDaily(),
  { maxRetries: 1, showError: false, errorMessage: '龙虎榜数据加载失败' }
)

const records = ref<any[]>([])

/** 蛇形→驼峰映射 */
function mapSnakeToCamel(items: any[]): any[] {
  const keyMap: Record<string, string> = {
    stock_code: 'stockCode', stock_name: 'stockName',
    net_buy_wan: 'netBuyWan', change_pct: 'changePct',
    turnover_pct: 'turnoverPct', trade_date: 'tradeDate',
    buy_wan: 'buyWan', sell_wan: 'sellWan',
  }
  return items.map(item => {
    const mapped: any = {}
    for (const [k, v] of Object.entries(item)) {
      mapped[keyMap[k] || k] = v
    }
    return mapped
  })
}

watch(() => safeRecords(rawData.value, 'records'), (raw) => {
  const items = Array.isArray(raw) ? mapSnakeToCamel(raw) : []
  records.value = items
}, { immediate: true })

/** 元 → 亿，保留2位小数 */
function toYi(val: number | undefined | null): string {
  const n = Number(val) || 0
  return (n / 1e8).toFixed(2)
}

/** 买入占比 */
function buyRatio(row: any): number {
  const b = Number(row.buyWan) || 0
  const s = Number(row.sellWan) || 0
  const total = b + s
  return total > 0 ? Math.round(b / total * 100) : 50
}

/** 搜索过滤 */
const filteredRows = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return records.value
  return records.value.filter((r: any) =>
    (r.stockCode || '').includes(q) || (r.stockName || '').includes(q)
  )
})

/** 统计 */
const totalNet = computed(() => records.value.reduce((s: number, r: any) => s + (Number(r.netBuyWan) || 0), 0))
const zhangTingCount = computed(() => records.value.filter((r: any) => (r.changePct || 0) >= 9.9).length)
const bullRatio = computed(() => {
  const n = records.value.filter((r: any) => (r.netBuyWan || 0) >= 0).length
  return records.value.length ? Math.round(n / records.value.length * 100) : 50
})

/** 净买入最多的股票名 */
const maxBuyName = computed(() => {
  const sorted = [...records.value].sort((a, b) => (b.netBuyWan || 0) - (a.netBuyWan || 0))
  return sorted[0]?.stockName || '-'
})
const maxBuyYi = computed(() => {
  const sorted = [...records.value].sort((a, b) => (b.netBuyWan || 0) - (a.netBuyWan || 0))
  return sorted[0] ? toYi(sorted[0].netBuyWan) : '-'
})

/** TOP4 资金卡片 */
const topCards = computed(() => {
  const sorted = [...records.value].sort((a, b) => Math.abs(b.netBuyWan || 0) - Math.abs(a.netBuyWan || 0))
  return sorted.slice(0, 4).map((r: any) => ({
    stockCode: r.stockCode,
    stockName: r.stockName,
    net: Number(r.netBuyWan) || 0,
    yi: toYi(r.netBuyWan),
    chg: Number(r.changePct) || 0,
    turnover: Number(r.turnoverPct) || 0,
    ratio: Math.min(Math.abs(Number(r.netBuyWan) || 0) / Math.abs(sorted[0]?.netBuyWan || 1) * 100, 100),
  }))
})

function goToStock(codeOrRow: any) {
  const code = typeof codeOrRow === 'string' ? codeOrRow : codeOrRow?.stockCode
  if (code) router.push(`/stock/${code}`)
}

onMounted(fetchData)
useAutoRefresh(() => { if (!reviewDate.value) fetchData() }, 120_000)
</script>

<style scoped lang="scss">
.dt-page { padding: 20px 24px; max-width: 1300px; margin: 0 auto; }
.text-rise { color: #D93026; }
.text-fall { color: #34A853; }
.text-primary { color: #1890FF; }

/* 顶栏 */
.dt-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px;
  h1 { font-size: 22px; font-weight: 700; color: #333; margin: 0; } }
.dt-toolbar { display: flex; gap: 8px; align-items: center; }
.dt-sk { height: 52px; background: #f5f6fa; border-radius: 6px; margin-bottom: 8px; }
.dt-empty { text-align: center; padding: 80px 0; color: #999; font-size: 14px; }

/* 概览统计 */
.dt-summary {
  display: flex; align-items: center; gap: 0; padding: 14px 20px;
  background: #fff; border: 1px solid #e8e8e8; border-radius: 6px; margin-bottom: 16px;
}
.dt-sum-item { display: flex; flex-direction: column; align-items: center; padding: 0 14px; min-width: 80px; }
.dt-sum-item.highlight { flex: 1; }
.dt-sum-v { font-size: 20px; font-weight: 700; color: #333; line-height: 1.3; }
.dt-sum-l { font-size: 12px; color: #999; margin-top: 2px; }
.dt-sum-div { width: 1px; height: 32px; background: #eee; flex-shrink: 0; }

/* TOP4 资金卡片 */
.dt-cards { display: flex; gap: 12px; margin-bottom: 16px; }
.dt-card {
  flex: 1; min-width: 0; padding: 14px; border-radius: 6px; cursor: pointer; position: relative;
  border: 1px solid #e8e8e8; transition: all .15s;
  &:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
}
.card-badge {
  position: absolute; top: 8px; right: 8px; font-size: 11px; padding: 1px 6px; border-radius: 3px;
  color: #fff; background: #D93026;
}
.card-sell .card-badge { background: #34A853; }
.card-name { font-size: 14px; font-weight: 600; color: #333; margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card-code { font-size: 11px; color: #999; font-family: 'Consolas', monospace; margin-bottom: 4px; }
.card-net { font-size: 18px; font-weight: 700; margin-bottom: 4px; }
.card-sub { display: flex; gap: 10px; font-size: 12px; color: #666; margin-bottom: 6px; }
.card-bar { height: 3px; background: #eee; border-radius: 2px; overflow: hidden; }
.card-bar-fill { height: 100%; border-radius: 2px; transition: width .3s; }

/* 表格 */
.dt-table-wrap { background: #fff; border: 1px solid #e8e8e8; border-radius: 6px; padding: 16px; }
.dt-tbl-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;
  h3 { font-size: 15px; font-weight: 600; color: #333; margin: 0; } }
.dt-code { font-family: 'Consolas', monospace; font-weight: 600; cursor: pointer; color: #1890FF; }
.dt-bar-mini { margin-top: 3px; height: 3px; }
.dt-bar-mini-track { width: 60px; height: 3px; background: #eee; border-radius: 2px; overflow: hidden; }
.dt-bar-mini-fill { height: 100%; border-radius: 2px; }
.dt-stats { margin-top: 12px; font-size: 13px; color: #999; text-align: right;
  strong { color: #333; } }

@media (max-width: 900px) {
  .dt-cards { flex-wrap: wrap; }
  .dt-card { flex: 0 0 calc(50% - 6px); }
}
@media (max-width: 600px) {
  .dt-card { flex: 0 0 100%; }
  .dt-summary { flex-wrap: wrap; gap: 6px; }
  .dt-sum-div { display: none; }
}
</style>
