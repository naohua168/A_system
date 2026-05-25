<template>
  <div class="fund-list-page">
    <!-- 页头 -->
    <div class="page-header">
      <h2>{{ t('nav.funds') }}</h2>
      <div class="search-bar">
        <el-input
          v-model="searchQuery"
          :placeholder="t('common.search')"
          clearable
          prefix-icon="Search"
          @input="handleSearch"
        />
      </div>
    </div>

    <!-- 筛选标签 -->
    <div class="filter-tabs">
      <el-radio-group v-model="activeFilter" size="small">
        <el-radio-button value="all">{{ t('market.all') }}</el-radio-button>
        <el-radio-button value="stock">股票型</el-radio-button>
        <el-radio-button value="mixed">混合型</el-radio-button>
        <el-radio-button value="bond">债券型</el-radio-button>
        <el-radio-button value="index">指数型</el-radio-button>
        <el-radio-button value="money">货币型</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 基金列表 -->
    <el-table
      :data="filteredFunds"
      stripe
      highlight-current-row
      @row-click="goToDetail"
      v-loading="loading"
    >
      <el-table-column prop="code" :label="t('stock.code')" width="120" sortable />
      <el-table-column prop="name" :label="t('stock.name')" min-width="200" />
      <el-table-column prop="type" :label="t('fund.type')" width="100" />
      <el-table-column prop="nav" :label="t('fund.nav')" width="120" sortable>
        <template #default="{ row }">
          <span class="nav-value">{{ row.nav?.toFixed(4) || '--' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="navDate" :label="t('signal.date')" width="120" />
      <el-table-column prop="manager" :label="t('fund.manager')" width="120" />
      <el-table-column prop="establishDate" label="成立日期" width="120" />
      <el-table-column label="近1年收益" width="110" align="right">
        <template #default="{ row }">
          <span :class="getChangeClass(row.yearReturn)">{{ row.yearReturn ?? '--' }}%</span>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrap" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        :pager-count="5"
        layout="prev, pager, next"
        @current-change="handlePageChange"
      />
    </div>

    <!-- 空状态 -->
    <el-empty v-if="!loading && filteredFunds.length === 0" :description="t('common.empty')" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { t } from '@/i18n'
import { getFundList } from '@/api/fund'

interface FundItem {
  code: string
  name: string
  type: string
  nav: number | null
  navDate: string
  manager: string
  establishDate: string
  yearReturn: number | null
}

const router = useRouter()
const searchQuery = ref('')
const activeFilter = ref('all')
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const allFunds = ref<FundItem[]>([])

const filteredFunds = computed(() => {
  let list = allFunds.value
  // 类型筛选
  if (activeFilter.value !== 'all') {
    list = list.filter((f) => f.type?.includes(activeFilter.value))
  }
  // 搜索筛选
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter((f) => f.code?.toLowerCase().includes(q) || f.name?.toLowerCase().includes(q))
  }
  return list
})

function getChangeClass(value: number | null): string {
  if (value == null) return ''
  return value >= 0 ? 'text-rise' : 'text-fall'
}

function goToDetail(row: FundItem) {
  router.push(`/fund/${row.code}`)
}

function handleSearch() {
  currentPage.value = 1
}

function handlePageChange(page: number) {
  currentPage.value = page
}

onMounted(async () => {
  loading.value = true
  try {
    const res = await getFundList()
    // 后端返回 {size, total, records, totalPages, page}
    const pageData = (res as any)?.data || res || {}
    allFunds.value = pageData?.records || pageData || []
    total.value = pageData?.total || allFunds.value.length
  } catch {
    // 降级：使用示例数据
    allFunds.value = [
      { code: '000001', name: '示例基金A', type: '混合型', nav: 1.2345, navDate: '2026-05-19', manager: '张三', establishDate: '2020-01-01', yearReturn: 12.5 },
      { code: '000002', name: '示例基金B', type: '股票型', nav: 2.3456, navDate: '2026-05-19', manager: '李四', establishDate: '2019-06-15', yearReturn: -3.2 },
      { code: '000003', name: '示例基金C', type: '债券型', nav: 1.0100, navDate: '2026-05-19', manager: '王五', establishDate: '2021-03-20', yearReturn: 4.8 },
    ]
    total.value = allFunds.value.length
  } finally {
    loading.value = false
  }
})
</script>

<style scoped lang="scss">
.fund-list-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
  }

  .search-bar {
    width: 300px;
  }
}

.filter-tabs {
  margin-bottom: 16px;
}

.nav-value {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-weight: 500;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.text-rise {
  color: var(--el-color-success);
}

.text-fall {
  color: var(--el-color-danger);
}
</style>
