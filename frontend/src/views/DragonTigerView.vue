<template>
  <div class="dragon-tiger-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">龙虎榜</h2>
        <span class="page-subtitle">每日龙虎榜席位数据 · 东方财富数据源</span>
      </div>
      <div class="header-right">
        <el-date-picker v-model="selectedDate" type="date" placeholder="选择日期"
          value-format="YYYY-MM-DD" :disabled-date="(d: Date) => d > today"
          @change="fetchData" size="small" />
      </div>
    </div>

    <el-table v-loading="loading" :data="records" stripe style="width:100%" @row-click="showDetail">
      <el-table-column prop="stockCode" label="代码" width="100">
        <template #default="{ row }">
          <span class="stock-code">{{ row.stockCode }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="stockName" label="名称" width="100" />
      <el-table-column prop="reason" label="上榜原因" min-width="200" show-overflow-tooltip />
      <el-table-column prop="netBuyWan" label="净买入(万)" width="130" align="right" sortable>
        <template #default="{ row }">
          <span :class="row.netBuyWan >= 0 ? 'text-rise' : 'text-fall'">
            {{ row.netBuyWan >= 0 ? '+' : '' }}{{ Number(row.netBuyWan).toFixed(2) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="buyWan" label="总买入(万)" width="120" align="right" />
      <el-table-column prop="sellWan" label="总卖出(万)" width="120" align="right" />
      <el-table-column prop="changePct" label="涨幅%" width="100" align="right" sortable>
        <template #default="{ row }">
          <span :class="row.changePct >= 0 ? 'text-rise' : 'text-fall'">
            {{ row.changePct >= 0 ? '+' : '' }}{{ row.changePct }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="turnoverPct" label="换手率%" width="100" align="right" />
    </el-table>

    <div class="stats-bar">
      <span>共 <strong>{{ records.length }}</strong> 只个股上榜 · 点击可查看个股详情</span>
    </div>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" :title="detailStock?.stockName || ''" width="500px">
      <div class="detail-info">
        <div class="info-row"><span class="label">代码</span><span>{{ detailStock?.stockCode }}</span></div>
        <div class="info-row"><span class="label">上榜原因</span><span>{{ detailStock?.reason }}</span></div>
        <div class="info-row"><span class="label">净买入</span>
          <span :class="(detailStock?.netBuyWan || 0) >= 0 ? 'text-rise' : 'text-fall'">{{ detailStock?.netBuyWan }}万</span>
        </div>
        <div class="info-row"><span class="label">涨幅</span>
          <span :class="(detailStock?.changePct || 0) >= 0 ? 'text-rise' : 'text-fall'">{{ detailStock?.changePct }}%</span>
        </div>
        <div class="info-row"><span class="label">换手率</span><span>{{ detailStock?.turnoverPct }}%</span></div>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="primary" @click="goToStock">查看个股详情</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getDragonTigerDaily } from '@/api/signal'

const router = useRouter()
const today = new Date()
const loading = ref(false)
const selectedDate = ref(today.toISOString().slice(0, 10))
const records = ref<any[]>([])
const detailVisible = ref(false)
const detailStock = ref<any>(null)

async function fetchData() {
  loading.value = true
  try {
    const res = await getDragonTigerDaily(selectedDate.value)
// @ts-ignore - response data wrapper
    records.value = res.data.records || []
  } catch { records.value = [] }
  finally { loading.value = false }
}

function showDetail(row: any) {
  detailStock.value = row
  detailVisible.value = true
}

function goToStock() {
  detailVisible.value = false
  if (detailStock.value) router.push(`/stock/${detailStock.value.stockCode}`)
}

onMounted(fetchData)
</script>

<style scoped lang="scss">
.dragon-tiger-page { padding: 24px; max-width: 1200px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-title { font-size: 22px; font-weight: 700; color: #fff; margin: 0; }
.page-subtitle { display: block; font-size: 13px; color: rgba(255,255,255,0.4); margin-top: 4px; }
.stock-code { font-family: 'SF Mono', monospace; font-weight: 600; cursor: pointer;
  &:hover { color: #2997ff; } }
.stats-bar { margin-top: 16px; font-size: 13px; color: rgba(255,255,255,0.4);
  strong { color: rgba(255,255,255,0.7); } }
.detail-info { padding: 8px 0; }
.info-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.06);
  .label { color: rgba(255,255,255,0.5); }
  &:last-child { border: none; } }
</style>
