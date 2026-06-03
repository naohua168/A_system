<template>
  <div class="lk-page">
    <header class="lk-top">
      <h1>限售解禁</h1>
      <div class="lk-toolbar">
        <span class="today-label">今日 · {{ todayStr }}</span>
        <el-radio-group v-model="mode" size="small">
          <el-radio-button value="upcoming">即将解禁</el-radio-button>
          <el-radio-button value="search">个股查询</el-radio-button>
        </el-radio-group>
      </div>
    </header>

    <!-- 个股查询模式 -->
    <template v-if="mode === 'search'">
      <div class="lk-search">
        <el-input v-model="searchCode" placeholder="输入股票代码" size="small" style="width:160px;margin-right:8px"
          @keyup.enter="searchStock" clearable />
        <el-button type="primary" size="small" @click="searchStock" :loading="searchLoading">查询</el-button>
      </div>
      <div v-if="searchResult.length" class="lk-section">
        <h3 class="lk-section-title">{{ searchRecord.stockName || searchRecord.stockCode }} · 历史解禁</h3>
        <el-table :data="searchResult" stripe size="small" style="width:100%"
          :header-cell-style="{ background: '#f5f6fa', color: '#666', fontWeight: 500, fontSize: '12px', padding: '10px 8px' }"
          :cell-style="{ padding: '8px' }">
          <el-table-column label="解禁日期" width="110" prop="lockupDate" sortable />
          <el-table-column label="类型" min-width="140" prop="lockupType" />
          <el-table-column label="占流通股%" width="100" align="right">
            <template #default="{ row }">{{ (row.floatRatio || 0) > 0 ? (row.floatRatio * 100).toFixed(2) + '%' : '-' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="70" align="center">
            <template #default="{ row }">
              <span :class="(row.lockupDate || '') >= today ? 'lk-badge lk-badge-pending' : 'lk-badge lk-badge-done'">
                {{ (row.lockupDate || '') >= today ? '待解禁' : '已解禁' }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div v-else-if="searchDone && !searchLoading" class="lk-empty">未找到该股票的解禁数据</div>
    </template>

    <!-- 即将解禁模式 -->
    <template v-else>
      <template v-if="loading">
        <div class="lk-sk" v-for="i in 5" :key="i"></div>
      </template>
      <div v-else-if="!records.length" class="lk-empty">
        <p>暂无即将解禁数据</p>
      </div>
      <template v-else>
        <!-- ① 概览统计 -->
        <section class="lk-summary">
          <div class="lk-sum-item">
            <span class="lk-sum-l">未来待解禁</span>
            <span class="lk-sum-v">{{ records.length }}</span>
          </div>
          <div class="lk-sum-div" />
          <div class="lk-sum-item">
            <span class="lk-sum-l">最早解禁</span>
            <span class="lk-sum-v">{{ earliestDate }}</span>
            <span class="lk-sum-r">{{ earliestDays > 0 ? earliestDays + '天后' : '今日' }}</span>
          </div>
          <div class="lk-sum-div" />
          <div class="lk-sum-item">
            <span class="lk-sum-l">最晚</span>
            <span class="lk-sum-v">{{ latestDate }}</span>
          </div>
          <div class="lk-sum-div" />
          <div class="lk-sum-item">
            <span class="lk-sum-l">解禁高峰月</span>
            <span class="lk-sum-v">{{ peakMonth }}</span>
            <span class="lk-sum-r">{{ peakMonthCount }} 只股票</span>
          </div>
        </section>

        <!-- ② 月度分布柱状图 -->
        <section class="lk-chart-section">
          <h3 class="lk-section-title">{{ activeMonth ? activeMonth + ' 解禁明细' : '月度解禁分布' }}</h3>
          <div class="lk-month-bar">
            <div v-for="m in monthlyStats" :key="m.month"
              class="lk-month-item" :class="{ active: activeMonth === m.month }"
              @click="activeMonth = activeMonth === m.month ? '' : m.month">
              <div class="lk-month-label">{{ m.label }}</div>
              <div class="lk-month-track">
                <div class="lk-month-fill" :style="{ height: (m.count / maxMonthlyCount) * 100 + '%',
                  background: m.rising ? '#D93026' : '#34A853' }" />
              </div>
              <div class="lk-month-count">{{ m.count }}</div>
            </div>
          </div>
        </section>

        <!-- ③ 表格 -->
        <section class="lk-section">
          <div class="lk-tbl-header">
            <h3 class="lk-section-title" style="margin-bottom:0">
              解禁明细 ({{ filteredRecords.length }})
              <span class="lk-section-sub" v-if="activeMonth">· {{ activeMonth }}</span>
            </h3>
            <el-input v-model="filterText" placeholder="搜索股票" size="small" clearable style="width:160px" prefix-icon="Search" />
          </div>
          <el-table :data="filteredRecords" stripe size="small" style="width:100%"
            :header-cell-style="{ background: '#f5f6fa', color: '#666', fontWeight: 500, fontSize: '12px', padding: '10px 8px' }"
            :cell-style="{ padding: '8px' }"
            @row-click="goToStock">
            <el-table-column label="日期" width="85" prop="lockupDate" sortable>
              <template #default="{ row }">{{ (row.lockupDate || '').slice(5) }}</template>
            </el-table-column>
            <el-table-column label="代码" width="80">
              <template #default="{ row }"><span class="lk-code">{{ row.stockCode }}</span></template>
            </el-table-column>
            <el-table-column label="名称" width="90" prop="stockName" />
            <el-table-column label="类型" min-width="140" prop="lockupType" show-overflow-tooltip />
            <el-table-column label="占流通股" width="90" align="right">
              <template #default="{ row }">{{ (row.floatRatio || 0) > 0 ? (row.floatRatio * 100).toFixed(2) + '%' : '-' }}</template>
            </el-table-column>
            <el-table-column label="距今日" width="80" align="center">
              <template #default="{ row }">
                <span :class="daysUntil(row.lockupDate) <= 7 ? 'lk-urgent' : ''">
                  {{ daysUntil(row.lockupDate) <= 0 ? '今日' : daysUntil(row.lockupDate) + '天' }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </section>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getUpcomingLockup, getLockupByStock } from '@/api/signal'
import { ElMessage } from 'element-plus'
import { useAutoRefresh } from '@/composables/useAutoRefresh'

const router = useRouter()
const today = new Date().toISOString().slice(0, 10)
const todayStr = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
const mode = ref('upcoming')
const loading = ref(false)
const records = ref<any[]>([])
const filterText = ref('')
const searchCode = ref('')
const searchLoading = ref(false)
const searchDone = ref(false)
const searchResult = ref<any[]>([])
const searchRecord = ref<any>({})
const activeMonth = ref('')

// 统计
const earliestDate = computed(() => records.value.length ? records.value[0]?.lockupDate?.slice(0, 10) : '-')
const latestDate = computed(() => records.value.length ? records.value[records.value.length - 1]?.lockupDate?.slice(0, 10) : '-')
const earliestDays = computed(() => earliestDate.value !== '-' ? daysUntil(earliestDate.value) : 0)

const monthlyStats = computed(() => {
  const map = new Map<string, number>()
  records.value.forEach((r: any) => {
    const m = (r.lockupDate || '').slice(0, 7)
    if (m) map.set(m, (map.get(m) || 0) + 1)
  })
  return Array.from(map.entries())
    .map(([month, count]) => ({
      month,
      label: month.slice(5) + '月',
      count,
      rising: count > 50,
    }))
    .sort((a, b) => a.month.localeCompare(b.month))
})

const maxMonthlyCount = computed(() => Math.max(...monthlyStats.value.map(m => m.count), 1))
const peakMonth = computed(() => {
  if (!monthlyStats.value.length) return '-'
  return monthlyStats.value.reduce((a, b) => a.count > b.count ? a : b).month
})
const peakMonthCount = computed(() => monthlyStats.value.reduce((a, b) => a.count > b.count ? a : b).count || 0)

// 过滤
const filteredRecords = computed(() => {
  let list = records.value
  if (activeMonth.value) {
    list = list.filter((r: any) => (r.lockupDate || '').startsWith(activeMonth.value))
  }
  const q = filterText.value.toLowerCase().trim()
  if (q) {
    list = list.filter((r: any) =>
      (r.stockName || '').toLowerCase().includes(q) ||
      (r.stockCode || '').toLowerCase().includes(q)
    )
  }
  return list
})

function daysUntil(d: string): number {
  if (!d) return 999
  return Math.ceil((new Date(d).getTime() - new Date().getTime()) / 86400000)
}

function goToStock(row: any) {
  if (row.stockCode) router.push(`/stock/${row.stockCode}`)
}

async function fetchData() {
  loading.value = true
  try {
    const res = await getUpcomingLockup() as any
    records.value = Array.isArray(res) ? res : []
  } catch { records.value = [] } finally { loading.value = false }
}

async function searchStock() {
  const code = searchCode.value.trim()
  if (!code) { ElMessage.warning('请输入股票代码'); return }
  searchLoading.value = true; searchDone.value = false
  try {
    const res = await getLockupByStock(code) as any
    searchResult.value = Array.isArray(res) ? res : []
    searchRecord.value = searchResult.value[0] || {}
  } catch { searchResult.value = [] } finally {
    searchLoading.value = false; searchDone.value = true
  }
}

watch(mode, () => { if (mode.value === 'upcoming') { activeMonth.value = ''; fetchData() } })
onMounted(fetchData)
useAutoRefresh(fetchData, 300_000)
</script>

<style scoped lang="scss">
.lk-page { padding: 20px 24px; max-width: 1300px; margin: 0 auto; }
.lk-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;
  h1 { font-size: 22px; font-weight: 700; color: #333; margin: 0; } }
.lk-toolbar { display: flex; gap: 8px; align-items: center; }
.lk-sk { height: 44px; background: #f5f6fa; border-radius: 6px; margin-bottom: 8px; }
.lk-empty { text-align: center; padding: 80px 0; color: #999; font-size: 14px; }
.lk-search { margin-bottom: 14px; }
.lk-code { color: #1890FF; font-weight: 600; cursor: pointer; }
.lk-badge { display: inline-block; padding: 1px 8px; font-size: 11px; border-radius: 3px; }
.lk-badge-pending { background: #fff7e6; color: #d46b08; }
.lk-badge-done { background: #f0f0f0; color: #999; }
.lk-urgent { color: #D93026; font-weight: 600; }
.lk-section { background: #fff; border: 1px solid #e8e8e8; border-radius: 6px; padding: 16px; margin-bottom: 14px; }
.lk-section-title { font-size: 15px; font-weight: 600; color: #333; margin: 0 0 10px 0; display: flex; align-items: center; gap: 8px; }
.lk-section-sub { font-size: 13px; font-weight: 400; color: #999; }
.lk-tbl-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }

/* 概览统计 */
.lk-summary {
  display: flex; align-items: center; gap: 0; padding: 14px 20px;
  background: #fff; border: 1px solid #e8e8e8; border-radius: 6px; margin-bottom: 14px;
}
.lk-sum-item { display: flex; flex-direction: column; align-items: center; padding: 0 14px; min-width: 80px; flex: 1; }
.lk-sum-v { font-size: 20px; font-weight: 700; color: #333; line-height: 1.3; }
.lk-sum-l { font-size: 12px; color: #999; margin-top: 2px; }
.lk-sum-r { font-size: 11px; color: #D93026; margin-top: 1px; }
.lk-sum-div { width: 1px; height: 32px; background: #eee; flex-shrink: 0; }

/* 月度柱状图 */
.lk-chart-section { background: #fff; border: 1px solid #e8e8e8; border-radius: 6px; padding: 16px; margin-bottom: 14px; }
.lk-month-bar { display: flex; align-items: flex-end; gap: 6px; padding-top: 10px; min-height: 130px; overflow-x: auto; }
.lk-month-item {
  flex: 1; min-width: 36px; display: flex; flex-direction: column; align-items: center; gap: 4px; cursor: pointer;
  padding: 4px 2px; border-radius: 4px; transition: all .15s;
  &:hover { background: #f5f6fa; }
  &.active { background: #f0f5ff; }
}
.lk-month-label { font-size: 10px; color: #888; white-space: nowrap; }
.lk-month-track { width: 20px; height: 80px; background: #f0f0f0; border-radius: 3px; overflow: hidden; display: flex; flex-direction: column-reverse; }
.lk-month-fill { width: 100%; border-radius: 3px 3px 0 0; transition: height .3s; min-height: 2px; }
.lk-month-count { font-size: 11px; font-weight: 600; color: #555; }

@media (max-width: 700px) {
  .lk-summary { flex-wrap: wrap; gap: 6px; }
  .lk-sum-div { display: none; }
}
</style>
