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
    </div>

    <el-table
      :data="store.records"
      v-loading="store.loading"
      stripe
      highlight-current-row
      @row-click="goToDetail"
      size="small"
      class="stock-table"
      :header-cell-style="{ background: '#f5f6fa', color: '#666', fontWeight: 500, fontSize: '12px', padding: '10px 8px' }"
      :cell-style="{ padding: '8px 6px', fontSize: '12px' }"
    >
      <el-table-column label="代码" width="80">
        <template #default="{ row }">
          <span class="stock-code">{{ row.stockCode }}</span>
        </template>
      </el-table-column>
      <el-table-column label="名称" min-width="110" prop="stockName">
        <template #default="{ row }">
          <span class="stock-name">{{ row.stockName }}</span>
        </template>
      </el-table-column>
      <el-table-column label="最新价" width="80" align="right">
        <template #default="{ row }">
          <span class="mono">{{ formatPrice(row.price) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="涨跌幅" width="80" align="right">
        <template #default="{ row }">
          <span :class="['change-tag', Number(row.changePct ?? 0) >= 0 ? 'rise' : 'fall']">
            {{ formatPercent(row.changePct) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="成交额" width="90" align="right">
        <template #default="{ row }">
          <span class="mono">{{ fmtAmount(row.amountWan) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="换手率" width="75" align="right">
        <template #default="{ row }">
          <span class="mono">{{ row.turnoverPct ? row.turnoverPct.toFixed(2) + '%' : '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="流通市值" width="95" align="right">
        <template #default="{ row }">
          <span class="mono">{{ row.mcapYi ? row.mcapYi.toFixed(1) + '亿' : '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="市盈率" width="75" align="right">
        <template #default="{ row }">
          <span class="mono">{{ row.pe && row.pe > 0 ? row.pe.toFixed(1) : '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="市净率" width="75" align="right">
        <template #default="{ row }">
          <span class="mono">{{ row.pb && row.pb > 0 ? row.pb.toFixed(2) : '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="昨收" width="75" align="right">
        <template #default="{ row }">
          <span class="mono">{{ row.lastClose ? row.lastClose.toFixed(2) : '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="70" fixed="right" align="center">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click.stop="goToDetail(row)">详情</el-button>
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
import { formatPrice, formatPercent } from '@/utils/format'

interface MarketNode {
  key: string
  label: string
  children?: MarketNode[]
}

const router = useRouter()
const store = useStockStore()
const searchKeyword = ref('')
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

function goToDetail(row: any) {
  router.push(`/stock/${row.stockCode}`)
}

function fmtAmount(wan: number | undefined | null): string {
  if (!wan || wan <= 0) return '-'
  const yi = wan / 10000
  if (yi >= 1) return yi.toFixed(1) + '亿'
  return wan.toFixed(0) + '万'
}

onMounted(() => {
  store.fetchList()
  document.addEventListener('click', closeDropdown)
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
}

.stock-table {
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  .stock-code { color: #1890FF; font-weight: 600; font-family: 'Consolas', monospace; }
  .stock-name { font-weight: 500; color: #333; }
  .mono { font-family: 'Consolas', monospace; color: #333; }
  .change-tag {
    font-weight: 600; font-family: 'Consolas', monospace;
    &.rise { color: #D93026; }
    &.fall { color: #34A853; }
  }
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>
