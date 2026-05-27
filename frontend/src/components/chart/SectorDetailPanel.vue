<template>
  <div class="sector-detail-panel" :class="{ visible: modelValue }">
    <!-- 头部 -->
    <div class="panel-header">
      <div class="sector-info">
        <h3 class="sector-name">{{ sectorName }}</h3>
        <div class="sector-change" :class="changeClass">
          {{ changeSign }}{{ sectorChange?.toFixed(2) }}%
        </div>
      </div>
      <div class="header-actions">
        <el-button class="detail-btn" text size="small" @click="$emit('goDetail', sectorName)">
          <el-icon><ArrowRight /></el-icon> 详情
        </el-button>
        <el-button class="close-btn" text @click="$emit('update:modelValue', false)">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- K线图区域 -->
    <div class="kline-section">
      <div ref="klineRef" class="kline-chart"></div>
      <div v-if="!klineData.length" class="kline-empty">
        <el-empty description="暂无K线数据" :image-size="80" />
      </div>
    </div>

    <!-- 成分股列表 -->
    <div class="stock-list-section">
      <div class="section-title">
        <span>成分股</span>
        <span class="stock-count">{{ stocks.length }}只</span>
      </div>
      <div class="stock-list" v-if="stocks.length">
        <div
          v-for="stock in displayedStocks"
          :key="stock.stockCode"
          class="stock-item"
          @click="$emit('stockClick', stock.stockCode)"
        >
          <div class="stock-name">{{ stock.stockName }}</div>
          <div class="stock-code">{{ stock.stockCode }}</div>
          <div class="stock-change" :class="getChangeClass(stock.changePercent)">
            {{ formatChange(stock.changePercent) }}
          </div>
        </div>
        <div v-if="stocks.length > DEFAULT_LIMIT" class="show-all-bar">
          <el-button text size="small" class="show-all-btn" @click="showAll = !showAll">
            {{ showAll ? '收起' : `展示全部 ${stocks.length} 只` }}
            <el-icon><ArrowDown v-if="!showAll" /><ArrowUp v-else /></el-icon>
          </el-button>
        </div>
      </div>
      <div v-else class="stock-empty">
        <el-empty description="暂无成分股数据" :image-size="60" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onBeforeUnmount, computed } from 'vue'
import { Close, ArrowRight, ArrowUp, ArrowDown } from '@element-plus/icons-vue'
import echarts from '@/utils/echarts'

interface StockItem {
  stockCode: string
  stockName: string
  changePercent: number
}

interface KlineData {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

const props = defineProps<{
  modelValue: boolean
  sectorName: string
  sectorChange?: number
  stocks: StockItem[]
  klineData: KlineData[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  stockClick: [code: string]
  goDetail: [name: string]
}>()

const klineRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

const DEFAULT_LIMIT = 20
const showAll = ref(false)

const displayedStocks = computed(() => {
  if (showAll.value) return props.stocks
  return props.stocks.slice(0, DEFAULT_LIMIT)
})

watch(() => props.modelValue, (visible) => {
  if (visible) {
    showAll.value = false
    nextTick(() => {
      renderKline()
    })
  }
})

const changeClass = computed(() => {
  if (!props.sectorChange) return ''
  return props.sectorChange >= 0 ? 'rise' : 'fall'
})

const changeSign = computed(() => {
  if (!props.sectorChange) return ''
  return props.sectorChange >= 0 ? '+' : ''
})

function getChangeClass(pct: number) {
  if (pct > 0) return 'rise'
  if (pct < 0) return 'fall'
  return ''
}

function formatChange(pct: number) {
  if (!pct) return '0.00%'
  const sign = pct > 0 ? '+' : ''
  return `${sign}${pct.toFixed(2)}%`
}

function renderKline() {
  if (!klineRef.value || !props.klineData.length) return
  
  if (!chart) {
    chart = echarts.init(klineRef.value, undefined, { renderer: 'canvas' })
  }

  const dates = props.klineData.map(d => d.date)
  const values = props.klineData.map(d => [d.open, d.close, d.low, d.high])
  const volumes = props.klineData.map(d => d.volume)

  const option: echarts.EChartsOption = {
    grid: {
      left: '10%',
      right: '10%',
      bottom: '15%',
      top: '10%',
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#333' } },
      axisLabel: { color: '#999', fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      scale: true,
      splitLine: { lineStyle: { color: '#2a2a2a' } },
      axisLabel: { color: '#999', fontSize: 10 },
    },
    dataZoom: [
      { type: 'inside', start: 50, end: 100 },
      { type: 'slider', start: 50, end: 100, height: 20, bottom: 10 },
    ],
    series: [
      {
        type: 'candlestick',
        data: values,
        itemStyle: {
          color: '#ef5350',
          color0: '#66bb6a',
          borderColor: '#ef5350',
          borderColor0: '#66bb6a',
        },
      },
    ],
  }

  chart.setOption(option, true)
}

function handleResize() {
  chart?.resize()
}

watch(() => props.klineData, () => {
  if (props.modelValue) {
    nextTick(renderKline)
  }
}, { deep: true })

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped lang="scss">
.sector-detail-panel {
  position: fixed;
  right: 0;
  top: 0;
  width: 420px;
  height: 100vh;
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  border-left: 1px solid rgba(255, 255, 255, 0.08);
  z-index: 1000;
  transform: translateX(100%);
  transition: transform 0.3s ease;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  &.visible {
    transform: translateX(0);
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);

    .sector-info {
      display: flex;
      align-items: center;
      gap: 12px;

      .sector-name {
        margin: 0;
        font-size: 18px;
        font-weight: 600;
        color: #fff;
      }

      .sector-change {
        font-size: 14px;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 4px;

        &.rise {
          color: #ef5350;
          background: rgba(239, 83, 80, 0.1);
        }

        &.fall {
          color: #66bb6a;
          background: rgba(102, 187, 106, 0.1);
        }
      }
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .detail-btn {
      color: rgba(255, 255, 255, 0.6);
      font-size: 12px;

      &:hover {
        color: $primary-on-dark;
      }
    }

    .close-btn {
      color: rgba(255, 255, 255, 0.5);

      &:hover {
        color: #fff;
      }
    }
  }

  .kline-section {
    height: 280px;
    padding: 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    position: relative;

    .kline-chart {
      width: 100%;
      height: 100%;
    }

    .kline-empty {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
    }
  }

  .stock-list-section {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;

    .section-title {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 20px;
      font-size: 14px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.7);
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);

      .stock-count {
        font-size: 12px;
        font-weight: normal;
        color: rgba(255, 255, 255, 0.4);
      }
    }

    .stock-list {
      flex: 1;
      overflow-y: auto;
      padding: 8px 16px;

      .stock-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 16px;
        margin-bottom: 8px;
        background: rgba(255, 255, 255, 0.02);
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s;

        &:hover {
          background: rgba(255, 255, 255, 0.06);
        }

        .stock-name {
          font-size: 14px;
          font-weight: 500;
          color: #fff;
          flex: 1;
        }

        .stock-code {
          font-size: 12px;
          color: rgba(255, 255, 255, 0.4);
          margin: 0 16px;
        }

        .stock-change {
          font-size: 14px;
          font-weight: 600;
          min-width: 70px;
          text-align: right;

          &.rise {
            color: #ef5350;
          }

          &.fall {
            color: #66bb6a;
          }
        }
      }
    }

    .stock-empty {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .show-all-bar {
      display: flex;
      justify-content: center;
      padding: 16px 0;

      .show-all-btn {
        font-size: 13px;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 8px 24px;
        border-radius: 20px;
        color: rgba(255, 255, 255, 0.55);
        background: transparent;
        border: 1px solid rgba(255, 255, 255, 0.08);
        transition: all 0.25s ease;
        cursor: pointer;

        &:hover {
          color: #F59E0B;
          background: rgba(245, 158, 11, 0.08);
          border-color: rgba(245, 158, 11, 0.25);
        }

        &:active {
          transform: scale(0.97);
        }

        :deep(.el-icon) {
          font-size: 15px;
        }
      }
    }
  }
}

:deep(.el-empty__description) {
  color: rgba(255, 255, 255, 0.4);
}
</style>
