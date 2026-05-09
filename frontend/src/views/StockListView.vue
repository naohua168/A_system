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

function formatVol(v: number) {
  if (!v) return '-'
  if (v >= 100000000) return (v / 100000000).toFixed(2) + '亿'
  if (v >= 10000) return (v / 10000).toFixed(2) + '万'
  return v.toLocaleString()
}

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
    // 使用 mock 数据回退
    stockList.value = generateMockStocks()
    total.value = stockList.value.length
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

// Mock 数据（后端不可用时的回退）
function generateMockStocks() {
  const names = ['贵州茅台', '宁德时代', '中国平安', '招商银行', '五粮液',
    '美的集团', '恒瑞医药', '隆基绿能', '比亚迪', '中信证券',
    '紫金矿业', '药明康德', '迈瑞医疗', '海康威视', '长江电力']
  const industries_list = ['白酒', '新能源', '金融', '银行', '白酒',
    '家电', '医药', '光伏', '汽车', '证券',
    '有色', '医药', '医疗器械', '安防', '电力']

  return names.map((name, i) => {
    const change_pct = (Math.random() - 0.5) * 6
    const price = 20 + Math.random() * 200
    return {
      code: ['600519', '300750', '601318', '600036', '000858',
             '000333', '600276', '601012', '002594', '600030',
             '601899', '603259', '300760', '002415', '600900'][i],
      name,
      price: +price.toFixed(2),
      change_pct: +change_pct.toFixed(2),
      change: +(price * change_pct / 100).toFixed(2),
      volume: Math.floor(Math.random() * 50000000),
      industry: industries_list[i],
      pe: +(15 + Math.random() * 40).toFixed(1),
    }
  }).sort((a, b) => Math.abs(b.change_pct) - Math.abs(a.change_pct))
}

onMounted(() => {
  fetchData()
  // 尝试获取行业列表
  getIndustries().then((res: any) => {
    if (Array.isArray(res)) industries.value = res
  }).catch(() => {
    industries.value = ['白酒', '新能源', '金融', '医药', '科技', '消费', '制造', '有色']
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
