<template>
  <div class="lockup-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">限售解禁</h2>
        <span class="page-subtitle">限售股解禁日历 · 东方财富数据源</span>
      </div>
      <div class="header-right">
        <el-radio-group v-model="tab" size="small">
          <el-radio-button value="upcoming">未来待解禁</el-radio-button>
          <el-radio-button value="history">历史已解禁</el-radio-button>
          <el-radio-button value="search">个股查询</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <!-- 搜索模式 -->
    <div v-if="tab === 'search'" class="search-bar">
      <el-input v-model="searchCode" placeholder="输入股票代码查询" size="small" style="width:200px;margin-right:8px" />
      <el-button type="primary" size="small" @click="searchStock" :loading="searchLoading">查询</el-button>
    </div>

    <el-table v-loading="loading" :data="records" stripe style="width:100%">
      <el-table-column prop="stockCode" label="代码" width="100">
        <template #default="{ row }">
          <span class="stock-code" @click="$router.push(`/stock/${row.stockCode}`)">{{ row.stockCode }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="lockupDate" label="解禁日期" width="120" sortable />
      <el-table-column prop="lockupType" label="限售股类型" min-width="160" show-overflow-tooltip />
      <el-table-column prop="shares" label="解禁数量" width="140" align="right">
        <template #default="{ row }">{{ formatShares(row.shares) }}</template>
      </el-table-column>
      <el-table-column prop="floatRatio" label="占流通股%" width="120" align="right">
        <template #default="{ row }">{{ row.floatRatio }}%</template>
      </el-table-column>
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.isUpcoming ? 'warning' : 'info'" size="small">
            {{ row.isUpcoming ? '待解禁' : '已解禁' }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>

    <div class="stats-bar">
      <span>共 <strong>{{ records.length }}</strong> 条解禁记录</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getUpcomingLockup, getLockupHistory, getLockupByStock } from '@/api/signal'

const tab = ref('upcoming')
const loading = ref(false)
const searchLoading = ref(false)
const searchCode = ref('')
const records = ref<any[]>([])

function formatShares(shares: number) {
  if (!shares) return '-'
  const s = Number(shares)
  if (s >= 100000000) return (s / 100000000).toFixed(2) + '亿'
  if (s >= 10000) return (s / 10000).toFixed(2) + '万'
  return s.toString()
}

async function fetchData() {
  loading.value = true
  try {
    let res: any
    if (tab.value === 'upcoming') res = await getUpcomingLockup()
    else if (tab.value === 'history') res = await getLockupHistory()
    records.value = res.data || []
  } catch { records.value = [] }
  finally { loading.value = false }
}

async function searchStock() {
  if (!searchCode.value.trim()) return
  searchLoading.value = true
  try {
    const res = await getLockupByStock(searchCode.value.trim())
    records.value = res.data || []
  } catch { records.value = [] }
  finally { searchLoading.value = false }
}

onMounted(fetchData)
</script>

<style scoped lang="scss">
.lockup-page { padding: 24px; max-width: 1200px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; flex-wrap: wrap; gap: 12px; }
.page-title { font-size: 22px; font-weight: 700; color: #fff; margin: 0; }
.page-subtitle { display: block; font-size: 13px; color: rgba(255,255,255,0.4); margin-top: 4px; }
.search-bar { margin-bottom: 16px; }
.stock-code { font-family: 'SF Mono', monospace; font-weight: 600; cursor: pointer; &:hover { color: #2997ff; } }
.stats-bar { margin-top: 16px; font-size: 13px; color: rgba(255,255,255,0.4); strong { color: rgba(255,255,255,0.7); } }
</style>
