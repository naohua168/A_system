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
          @change="onDateChange" size="small" />
        <el-button v-if="error" type="warning" size="small" @click="fetchData" :loading="loading">
          重试
        </el-button>
      </div>
    </div>

    <!-- 加载骨架 -->
    <template v-if="loading">
      <SkeletonLoader type="table" :rows="8" :col-widths="['10%','10%','25%','12%','10%','10%','10%','10%']" />
    </template>

    <!-- 错误状态 -->
    <template v-else-if="error">
      <EmptyState type="error" :title="error" description="点击重试或切换日期" size="lg">
        <template #actions>
          <el-button type="primary" size="small" @click="fetchData">重新加载</el-button>
        </template>
      </EmptyState>
    </template>

    <!-- 空数据 -->
    <template v-else-if="!records.length">
      <EmptyState type="empty" title="暂无龙虎榜数据" :sub="selectedDate">
        <template #actions>
          <el-button size="small" @click="selectedDate = yesterday; onDateChange()">查看最近交易日</el-button>
        </template>
      </EmptyState>
    </template>

    <!-- 正常数据 -->
    <template v-else>
      <el-table :data="records" stripe style="width:100%" @row-click="showDetail">
        <el-table-column prop="stockCode" label="代码" width="100">
          <template #default="{ row }">
            <span class="stock-code">{{ safeStr(row.stockCode) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="stockName" label="名称" width="100" />
        <el-table-column prop="reason" label="上榜原因" min-width="200" show-overflow-tooltip />
        <el-table-column prop="netBuyWan" label="净买入(万)" width="130" align="right" sortable>
          <template #default="{ row }">
            <span :class="(row.netBuyWan || 0) >= 0 ? 'text-rise' : 'text-fall'">
              {{ (row.netBuyWan || 0) >= 0 ? '+' : '' }}{{ safeNum(row.netBuyWan, 2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="buyWan" label="总买入(万)" width="120" align="right" />
        <el-table-column prop="sellWan" label="总卖出(万)" width="120" align="right" />
        <el-table-column prop="changePct" label="涨幅%" width="100" align="right" sortable>
          <template #default="{ row }">
            <span :class="(row.changePct || 0) >= 0 ? 'text-rise' : 'text-fall'">
              {{ (row.changePct || 0) >= 0 ? '+' : '' }}{{ safeNum(row.changePct, 2) }}%
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
            <span :class="safeNum(detailStock?.netBuyWan) >= 0 ? 'text-rise' : 'text-fall'">{{ safeStr(detailStock?.netBuyWan) }}万</span>
          </div>
          <div class="info-row"><span class="label">涨幅</span>
            <span :class="safeNum(detailStock?.changePct) >= 0 ? 'text-rise' : 'text-fall'">{{ safeStr(detailStock?.changePct) }}%</span>
          </div>
          <div class="info-row"><span class="label">换手率</span><span>{{ safeStr(detailStock?.turnoverPct) }}%</span></div>
        </div>
        <template #footer>
          <el-button @click="detailVisible = false">关闭</el-button>
          <el-button type="primary" @click="goToStock">查看个股详情</el-button>
        </template>
      </el-dialog>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getDragonTigerDaily } from '@/api/signal'
import { useApiRetry, safeRecords, safeNum, safeStr } from '@/composables/useApiRetry'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const router = useRouter()
const today = new Date()
const yesterday = new Date(today.getTime() - 86400000).toISOString().slice(0, 10)
const selectedDate = ref(yesterday)
const detailVisible = ref(false)
const detailStock = ref<any>(null)

const { data: rawData, loading, error, fetch: fetchData } = useApiRetry(
  () => getDragonTigerDaily(selectedDate.value),
  { maxRetries: 1, showError: false, errorMessage: '龙虎榜数据加载失败' }
)

const records = ref<any[]>([])

const computedRecords = computed(() => safeRecords(rawData.value, 'records'))
watch(computedRecords, (v) => { records.value = v }, { immediate: true })

function onDateChange() { fetchData() }

function showDetail(row: any) {
  detailStock.value = row
  detailVisible.value = true
}

function goToStock() {
  detailVisible.value = false
  if (detailStock.value?.stockCode) router.push(`/stock/${detailStock.value.stockCode}`)
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
