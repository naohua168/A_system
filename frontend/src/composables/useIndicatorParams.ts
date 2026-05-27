/**
 * K线图指标参数管理组合函数
 *
 * 提取 StockDetailView 与 SectorDetailView 共享的工具栏逻辑：
 * - 周期切换、叠加指标(MA/BOLL)、底部指标(MACD/KDJ/RSI)的状态管理
 * - 指标参数设置弹窗（MACD周期、KDJ周期、RSI周期、MA周期、BOLL标准差）
 * - 指标开关切换与选择
 *
 * 通过 triggerRender 可被调用方设置为渲染函数引用，
 * 状态变更后自动触发重绘，避免循环依赖。
 */
import { ref, reactive } from 'vue'

/** 周期选项卡定义 */
export const periods = [
  { key: '5min', label: '5分' },
  { key: '15min', label: '15分' },
  { key: '30min', label: '30分' },
  { key: '60min', label: '60分' },
  { key: 'day', label: '日K' },
  { key: 'week', label: '周K' },
  { key: 'month', label: '月K' },
]

export interface IndicatorItem {
  key: string
  label: string
  active?: boolean
}

/**
 * 指标参数管理
 */
export function useIndicatorParams() {
  /** 叠加在K线图上的指标 (MA/BOLL)，可多选 */
  const overlayIndicators = ref<IndicatorItem[]>([
    { key: 'ma', label: 'MA', active: true },
    { key: 'boll', label: 'BOLL', active: false },
  ])

  /** 底部图表指标 (MACD/KDJ/RSI)，互斥，选中替换成交量 */
  const bottomIndicators = ref<IndicatorItem[]>([
    { key: 'macd', label: 'MACD' },
    { key: 'kdj', label: 'KDJ' },
    { key: 'rsi', label: 'RSI' },
  ])

  /** 当前底部指标，null 表示显示成交量 */
  const bottomActive = ref<string | null>(null)

  /**
   * 渲染回调引用 — 由调用方设置为具体的渲染函数。
   * 用于避免 `useIndicatorParams` 与 `useTechnicalChart` 之间的循环依赖。
   */
  let _render: (() => void) | null = null

  function setRenderCallback(cb: () => void) {
    _render = cb
  }

  /** 切换叠加指标开关 */
  function toggleOverlay(ind: IndicatorItem) {
    ind.active = !ind.active
    _render?.()
  }

  /** 选择/切换底部指标（再次点击回到成交量） */
  function selectBottomIndicator(ind: IndicatorItem) {
    bottomActive.value = bottomActive.value === ind.key ? null : ind.key
    _render?.()
  }

  // ── 参数设置弹窗 ──
  const paramsDialogVisible = ref(false)
  const paramsDialogTitle = ref('')
  const paramsTarget = ref('')

  /** 技术指标参数（默认值） */
  const params = reactive({
    macd: { fast: 12, slow: 26, signal: 9 },
    kdj: { period: 9, m1: 3, m2: 3 },
    rsi: { period: 14 },
    ma: { periods: [5, 20, 60, 120] as number[] },
    boll: { period: 20, multiplier: 2 },
  })

  /** 打开参数设置弹窗 */
  function openParams(ind: IndicatorItem) {
    paramsTarget.value = ind.key
    paramsDialogTitle.value = ind.label
    paramsDialogVisible.value = true
  }

  /** 应用参数并关闭弹窗 */
  function applyParams() {
    paramsDialogVisible.value = false
    _render?.()
  }

  return {
    periods,
    overlayIndicators,
    bottomIndicators,
    bottomActive,
    setRenderCallback,
    toggleOverlay,
    selectBottomIndicator,
    paramsDialogVisible,
    paramsDialogTitle,
    paramsTarget,
    params,
    openParams,
    applyParams,
  }
}
