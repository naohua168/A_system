<template>
  <div class="stock-list-view">
    <!-- 搜索栏 + 筛选 -->
    <div class="toolbar">
      <div class="search-area">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索股票代码/名称"
          clearable
          prefix-icon="Search"
          class="search-input"
          @keyup.enter="handleSearch"
        >
          <template #append>
            <el-button @click="handleSearch">搜索</el-button>
          </template>
        </el-input>
      </div>
      <div class="filter-area">
        <el-select v-model="selectedIndustry" placeholder="全部行业" clearable @change="fetchData">
          <el-option v-for="ind in industries" :key="ind" :label="ind" :value="ind" />
        </el-select>
        <el-select v-model="sortField" placeholder="排序" @change="fetchData">
          <el-option label="默认排序" value="" />
          <el-option label="涨幅 ↑" value="change_pct_desc" />
          <el-option label="涨幅 ↓" value="change_pct_asc" />
          <el-option label="价格 ↑" value="price_desc" />
          <el-option label="价格 ↓" value="price_asc" />
          <el-option label="成交量 ↑" value="volume_desc" />
        </el-select>
      </div>
    </div>

    <!-- 股票表格 -->
    <el-table
      :data="stockList"
      v-loading="loading"
      stripe
      highlight-current-row
      @row-click="goToDetail"
      class="stock-table"
    >
      <el-table-column prop="code" label="代码" width="100" />
      <el-table-column prop="name" label="名称" min-width="140">
        <template #default="{ row }">
          <span class="stock-name">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="price" label="最新价" width="120" align="right">
        <template #default="{ row }">
          <span class="mono">{{ row.price?.toFixed(2) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="change_pct" label="涨跌幅" width="110" align="right">
        <template #default="{ row }">
          <span :class="['change-tag', row.change_pct >= 0 ? 'rise' : 'fall']">
            {{ row.change_pct >= 0 ? '+' : '' }}{{ row.change_pct?.toFixed(2) }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="change" label="涨跌额" width="100" align="right">
        <template #default="{ row }">
          <span :class="['mono', row.change >= 0 ? 'text-rise' : 'text-fall']">
            {{ row.change >= 0 ? '+' : '' }}{{ row.change?.toFixed(2) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="volume" label="成交量" width="110" align="right">
        <template #default="{ row }">
          <span class="mono">{{ formatVol(row.volume) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="industry" label="行业" width="100" />
      <el-table-column prop="pe" label="市盈率" width="90" align="right">
        <template #default="{ row }">
          <span class="mono">{{ typeof row.pe === 'number' ? row.pe.toFixed(1) : '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click.stop="$router.push(`/stock/${row.code}`)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @change="fetchData"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getStockList, searchStocks, getIndustries } from '@/api/stock'
import { formatVol } from '@/utils/format'

const router = useRouter()
const loading = ref(false)
const stockList = ref<any[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchKeyword = ref('')
const selectedIndustry = ref('')
const sortField = ref('')
const industries = ref<string[]>([])

async function fetchData() {
  loading.value = true
  try {
    const params: any = {
      page: currentPage.value,
      size: pageSize.value,
    }
    if (searchKeyword.value) params.keyword = searchKeyword.value
    if (selectedIndustry.value) params.industry = selectedIndustry.value
    if (sortField.value) {
      const [field, dir] = sortField.value.split('_')
      params.sortField = field
      params.sortOrder = dir === 'asc' ? 'asc' : 'desc'
    }
    const res: any = await getStockList(params)
    if (res?.records) {
      // 映射后端字段：stockCode -> code, stockName -> name
      stockList.value = res.records.map((r: any) => ({
        code: r.stockCode,
        name: r.stockName,
        industry: r.industry,
        market: r.market,
        // stock_daily 数据暂缺时填充占位
        price: r.price || 0,
        change_pct: r.changePct !== undefined ? r.changePct : 0,
        change: r.change || 0,
        volume: r.volume || 0,
        pe: r.pe != null ? Number(r.pe) : undefined,
      }))
      total.value = res.total || 0
    } else if (Array.isArray(res)) {
      stockList.value = res
      total.value = res.length
    }
  } catch (_e) {
    console.warn('[StockList] 加载股票列表失败:', _e)
    stockList.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  fetchData()
}

function goToDetail(row: any) {
  router.push(`/stock/${row.code}`)
}

onMounted(() => {
  fetchData()
  // 获取行业列表
  getIndustries().then((res: any) => {
    if (Array.isArray(res)) industries.value = res
  }).catch(() => {
    console.warn('[StockList] 加载行业列表失败')
  })
})
</script>

<style scoped lang="scss">
.stock-list-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: $spacing-lg;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-lg;
  flex-wrap: wrap;
  gap: $spacing-md;

  .search-area {
    flex: 1;
    max-width: 420px;
  }

  .filter-area {
    display: flex;
    gap: $spacing-sm;
  }
}

.stock-table {
  border-radius: $rounded-lg;
  overflow: hidden;
  cursor: pointer;

  .stock-name { font-weight: 500; }

  .mono { font-family: $font-display; }

  .change-tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: $rounded-xs;
    font-weight: 600;
    font-family: $font-display;

    &.rise { color: white; background: $rise; }
    &.fall { color: white; background: $fall; }
  }
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: $spacing-lg;
}
</style>
