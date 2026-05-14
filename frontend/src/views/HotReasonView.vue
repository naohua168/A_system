<template>
  <div class="hot-reason-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">题材热点</h2>
        <span class="page-subtitle">每日强势股题材归因 · 同花顺数据源</span>
      </div>
      <div class="header-right">
        <el-date-picker v-model="selectedDate" type="date" placeholder="选择日期"
          value-format="YYYY-MM-DD" :disabled-date="d => d > today"
          @change="fetchData" size="small" />
      </div>
    </div>

    <el-table v-loading="loading" :data="records" stripe style="width:100%" @row-click="goToStock">
      <el-table-column prop="stockCode" label="代码" width="100">
        <template #default="{ row }">
          <span class="stock-code">{{ row.stockCode }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="stockName" label="名称" width="100" />
      <el-table-column prop="reason" label="题材归因" min-width="300">
        <template #default="{ row }">
          <div class="reason-tags">
            <el-tag v-for="tag in parseTags(row.reason)" :key="tag" size="small" class="reason-tag">
              {{ tag }}
            </el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="changePct" label="涨幅%" width="100" align="right">
        <template #default="{ row }">
          <span :class="row.changePct >= 0 ? 'text-rise' : 'text-fall'">
            {{ row.changePct >= 0 ? '+' : '' }}{{ row.changePct }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="turnoverPct" label="换手率%" width="100" align="right" />
    </el-table>

    <div class="stats-bar">
      <span>共 <strong>{{ records.length }}</strong> 只个股出现强势题材信号</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getHotReason } from '@/api/signal'

const router = useRouter()
const today = new Date()
const loading = ref(false)
const selectedDate = ref(today.toISOString().slice(0, 10))
const records = ref<any[]>([])

function parseTags(reason: string): string[] {
  if (!reason) return []
  return reason.split(/[+＋,，、]/).filter(Boolean)
}

async function fetchData() {
  loading.value = true
  try {
    const res = await getHotReason(selectedDate.value)
    records.value = res.data.records || []
  } catch { records.value = [] }
  finally { loading.value = false }
}

function goToStock(row: any) {
  router.push(`/stock/${row.stockCode}`)
}

onMounted(fetchData)
</script>

<style scoped lang="scss">
.hot-reason-page { padding: 24px; max-width: 1200px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-title { font-size: 22px; font-weight: 700; color: #fff; margin: 0; }
.page-subtitle { display: block; font-size: 13px; color: rgba(255,255,255,0.4); margin-top: 4px; }
.stock-code { font-family: 'SF Mono', monospace; font-weight: 600; cursor: pointer;
  &:hover { color: #2997ff; } }
.reason-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.reason-tag { background: rgba(41,151,255,0.12); color: #2997ff; border: 1px solid rgba(41,151,255,0.25); }
.stats-bar { margin-top: 16px; font-size: 13px; color: rgba(255,255,255,0.4);
  strong { color: rgba(255,255,255,0.7); } }
</style>
