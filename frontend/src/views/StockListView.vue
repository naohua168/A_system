<template>
  <div class="stock-list-view">
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
        <el-select v-model="store.selectedIndustry" placeholder="全部行业" clearable @change="store.setIndustry($event || '')">
          <el-option v-for="ind in industries" :key="ind" :label="ind" :value="ind" />
        </el-select>
        <el-select v-model="sortField" placeholder="排序" @change="handleSort">
          <el-option label="默认排序" value="" />
          <el-option label="涨幅 ↑" value="change_pct_desc" />
          <el-option label="涨幅 ↓" value="change_pct_asc" />
          <el-option label="价格 ↑" value="price_desc" />
          <el-option label="价格 ↓" value="price_asc" />
          <el-option label="成交量 ↑" value="volume_desc" />
        </el-select>
      </div>
    </div>

    <el-table
      :data="store.records"
      v-loading="store.loading"
      stripe
      highlight-current-row
      @row-click="goToDetail"
      class="stock-table"
    >
      <el-table-column prop="stockCode" label="代码" width="100" />
      <el-table-column prop="stockName" label="名称" min-width="140">
        <template #default="{ row }">
          <span class="stock-name">{{ row.stockName }}</span>
        </template>
      </el-table-column>
      <el-table-column label="最新价" width="120" align="right">
        <template #default="{ row }">
          <span class="mono">{{ row.price?.toFixed(2) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="涨跌幅" width="110" align="right">
        <template #default="{ row }">
          <span :class="['change-tag', (row.changePct ?? 0) >= 0 ? 'rise' : 'fall']">
            {{ (row.changePct ?? 0) >= 0 ? '+' : '' }}{{ (row.changePct ?? 0).toFixed(2) }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column label="涨跌额" width="100" align="right">
        <template #default="{ row }">
          <span :class="['mono', (row.change ?? 0) >= 0 ? 'text-rise' : 'text-fall']">
            {{ (row.change ?? 0) >= 0 ? '+' : '' }}{{ (row.change ?? 0).toFixed(2) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="成交量" width="110" align="right">
        <template #default="{ row }">
          <span class="mono">{{ formatVol(row.volume) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="industry" label="行业" width="100" />
      <el-table-column label="市盈率" width="90" align="right">
        <template #default="{ row }">
          <span class="mono">{{ typeof row.pe === 'number' ? row.pe.toFixed(1) : '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click.stop="$router.push(`/stock/${row.stockCode}`)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="store.currentPage"
        v-model:page-size="store.pageSize"
        :total="store.total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="store.setPage"
        @size-change="(s: number) => { store.pageSize = s; store.fetchList() }"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useStockStore } from '@/stores/stock'
import { getIndustries } from '@/api/market'
import { formatVol } from '@/utils/format'

const router = useRouter()
const store = useStockStore()
const searchKeyword = ref('')
const sortField = ref('')
const industries = ref<string[]>([])

function handleSearch() {
  store.setKeyword(searchKeyword.value)
}

function handleSort() {
  if (!sortField.value) {
    store.fetchList({ page: 1 })
    return
  }
  const [field, dir] = sortField.value.split('_')
  store.fetchList({
    page: 1,
    sortField: field,
    sortOrder: dir === 'asc' ? 'asc' : 'desc',
  })
}

function goToDetail(row: any) {
  router.push(`/stock/${row.stockCode}`)
}

onMounted(() => {
  store.fetchList()
  getIndustries().then((res) => {
    industries.value = res
  }).catch(() => {})
})
</script>

<style scoped lang="scss">
.stock-list-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;

  .search-area { flex: 1; max-width: 420px; }
  .filter-area { display: flex; gap: 8px; }
}

.stock-table {
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  .stock-name { font-weight: 500; }
  .mono { font-family: 'Menlo', 'Consolas', monospace; }
  .change-tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 600;
    font-family: 'Menlo', 'Consolas', monospace;
    &.rise { color: white; background: #f56c6c; }
    &.fall { color: white; background: #67c23a; }
  }
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>
