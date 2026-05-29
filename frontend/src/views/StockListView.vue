<template>
  <div class="stock-list-view">
    <!-- 市场分类标签（二级下拉） -->
    <div class="market-tabs">
      <template v-for="tab in marketTree" :key="tab.key">
        <!-- 有子分类的 tab：点击出下拉菜单 -->
        <div
          v-if="tab.children"
          :class="['market-tab', 'tab-with-dropdown', { active: isTabActive(tab) }]"
        >
          <span class="tab-text" @click="openDropdown(tab.key)">
            {{ tab.label }}
            <svg class="arrow" viewBox="0 0 12 12" width="10" height="10"
              :class="{ rotate: activeDropdown === tab.key }"
            ><path d="M2 4l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </span>
          <!-- 下拉菜单 -->
          <div v-show="activeDropdown === tab.key" class="dropdown-menu">
            <div
              v-for="child in tab.children"
              :key="child.key"
              :class="['dropdown-item', { active: store.selectedMarket === child.key }]"
              @click="selectMarket(child.key, child.label, tab)"
            >{{ child.label }}</div>
          </div>
        </div>
        <!-- 无子分类的 tab -->
        <div
          v-else
          :class="['market-tab', { active: store.selectedMarket === tab.key }]"
          @click="selectMarket(tab.key, tab.label, tab)"
        >{{ tab.label }}</div>
      </template>
    </div>

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

interface MarketNode {
  key: string
  label: string
  children?: MarketNode[]
}

const router = useRouter()
const store = useStockStore()
const searchKeyword = ref('')
const sortField = ref('')
const industries = ref<string[]>([])
const activeDropdown = ref<string | null>(null)

/** 市场分类（参考东方财富：一级横向，二级下拉） */
const marketTree: MarketNode[] = [
  { key: '', label: '全部' },
  { key: 'hs', label: '沪深A股', children: [
    { key: 'hs', label: '全部沪深A股' },
    { key: 'sh', label: '沪市A股' },
    { key: 'sz', label: '深市A股' },
  ]},
  { key: 'sh-kcb', label: '科创板' },
  { key: 'sz-cyb', label: '创业板' },
  { key: 'bj', label: '北交所' },
  { key: 'etf', label: 'ETF' },
]

/** 打开下拉菜单（关闭其他） */
function openDropdown(key: string) {
  activeDropdown.value = activeDropdown.value === key ? null : key
}

/** 点击页面空白关闭下拉 */
function closeDropdown(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.closest('.market-tab')) {
    activeDropdown.value = null
  }
}

/** 判断 tab（或它的子项）是否被选中 */
function isTabActive(tab: MarketNode): boolean {
  if (tab.children) {
    return tab.children.some(c => c.key === store.selectedMarket)
  }
  return tab.key === store.selectedMarket
}

/** 选择市场 */
function selectMarket(key: string, label: string, _parent: MarketNode) {
  activeDropdown.value = null
  store.setMarket(key)
}

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
  document.addEventListener('click', closeDropdown)
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

.market-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  flex-wrap: wrap;

  .market-tab {
    position: relative;
    flex-shrink: 0;
    padding: 6px 16px;
    border: 1px solid $divider-soft;
    background: $canvas;
    font-size: 13px;
    color: $ink-muted-48;
    cursor: pointer;
    border-radius: $rounded-pill;
    transition: all 0.15s;
    font-weight: 500;
    user-select: none;

    &:hover {
      border-color: $primary;
      color: $primary;
    }

    &.active {
      background: $primary;
      border-color: $primary;
      color: #fff;
      font-weight: 600;
    }

    &.tab-with-dropdown {
      .tab-text {
        display: inline-flex;
        align-items: center;
        gap: 2px;
      }
      .arrow {
        opacity: 0.5;
        transition: transform 0.2s;
        &.rotate { transform: rotate(180deg); }
      }
      &:hover .arrow { opacity: 0.8; }
    }
  }
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 4px;
  background: $canvas;
  border: 1px solid $divider-soft;
  border-radius: $rounded-sm;
  box-shadow: $shadow-elevated;
  min-width: 130px;
  padding: 4px;
  z-index: 100;

  .dropdown-item {
    padding: 7px 14px;
    font-size: 13px;
    cursor: pointer;
    border-radius: $rounded-xs;
    color: $ink;
    transition: all 0.1s;

    &:hover {
      background: rgba($primary, 0.06);
      color: $primary;
    }

    &.active {
      color: $primary;
      font-weight: 600;
      background: rgba($primary, 0.08);
    }
  }
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
