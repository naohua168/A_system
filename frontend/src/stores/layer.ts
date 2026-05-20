import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { LayerInfo, LayerFlow } from '@/types'
import {
  getLayerList,
  getLayerDetail,
  getLayerFlows,
  searchLayers,
} from '@/api/layer'

/**
 * L1~L6 层架构详情 Store
 * 遵循 Pinia 组合式 API 风格，支持 AbortController 竞态控制
 */
export const useLayerStore = defineStore('layer', () => {
  // ============================================================
  // State
  // ============================================================
  const layers = ref<LayerInfo[]>([])
  const currentLayer = ref<LayerInfo | null>(null)
  const flows = ref<LayerFlow[]>([])
  const loading = ref(false)
  const detailLoading = ref(false)
  const error = ref<string | null>(null)
  const searchKeyword = ref('')
  const searchResults = ref<LayerInfo[]>([])
  const activeTab = ref('overview')

  // ============================================================
  // AbortController — 竞态控制
  // ============================================================
  let listController: AbortController | null = null
  let detailController: AbortController | null = null
  let searchController: AbortController | null = null

  // ============================================================
  // Computed
  // ============================================================
  /** 按层编号排序的已加载层列表 */
  const sortedLayers = computed(() =>
    [...layers.value].sort((a, b) => a.id.localeCompare(b.id)),
  )

  /** 总体完成度（各层完成度的平均值） */
  const overallCompletion = computed(() => {
    if (!layers.value.length) return 0
    const total = layers.value.reduce((s, l) => s + l.completion, 0)
    return Math.round(total / layers.value.length)
  })

  /** 总计文件数 */
  const totalFiles = computed(() =>
    layers.value.reduce((s, l) => s + l.fileCount, 0),
  )

  /** 总计模块数 */
  const totalModules = computed(() =>
    layers.value.reduce((s, l) => s + l.moduleCount, 0),
  )

  /** 总计测试用例 */
  const totalTests = computed(() =>
    layers.value.reduce((s, l) => s + l.testCount, 0),
  )

  /** 各状态层的数量 */
  const statusCounts = computed(() => {
    const counts = { completed: 0, in_progress: 0, blocked: 0, pending: 0 }
    layers.value.forEach((l) => {
      counts[l.status] = (counts[l.status] || 0) + 1
    })
    return counts
  })

  /** 搜索筛选后的列表 */
  const filteredLayers = computed(() => {
    const kw = searchKeyword.value.toLowerCase().trim()
    if (!kw) return sortedLayers.value
    return sortedLayers.value.filter(
      (l) =>
        l.id.toLowerCase().includes(kw) ||
        l.name.includes(kw) ||
        l.directory.toLowerCase().includes(kw),
    )
  })

  // ============================================================
  // Actions
  // ============================================================

  /** 获取/刷新全部层列表 */
  async function fetchLayers() {
    listController?.abort()
    listController = new AbortController()
    loading.value = true
    error.value = null
    try {
      layers.value = await getLayerList(listController.signal)
    } catch (e: any) {
      if (e.name === 'CanceledError' || e.name === 'AbortError') return
      error.value = e.message || '加载层列表失败'
    } finally {
      loading.value = false
    }
  }

  /** 获取/刷新层间数据流 */
  async function fetchFlows() {
    try {
      flows.value = await getLayerFlows()
    } catch {
      // 静默，数据流为非关键信息
    }
  }

  /** 获取指定层详情 */
  async function fetchLayerDetail(layerId: string) {
    detailController?.abort()
    detailController = new AbortController()
    detailLoading.value = true
    error.value = null
    try {
      const result = await getLayerDetail(layerId, detailController.signal)
      currentLayer.value = result
      if (!result) error.value = `层 ${layerId} 不存在`
    } catch (e: any) {
      if (e.name === 'CanceledError' || e.name === 'AbortError') return
      error.value = e.message || '加载层详情失败'
    } finally {
      detailLoading.value = false
    }
  }

  /** 搜索层 */
  async function doSearch(keyword: string) {
    searchKeyword.value = keyword
    if (!keyword.trim()) {
      searchResults.value = []
      return
    }
    searchController?.abort()
    searchController = new AbortController()
    try {
      searchResults.value = await searchLayers(keyword, searchController.signal)
    } catch (e: any) {
      if (e.name === 'CanceledError' || e.name === 'AbortError') return
      searchResults.value = []
    }
  }

  /** 设置当前标签 */
  function setActiveTab(tab: string) {
    activeTab.value = tab
  }

  /** 初始化 — 首次加载层列表和数据流 */
  async function init() {
    await Promise.all([fetchLayers(), fetchFlows()])
  }

  return {
    // State
    layers,
    currentLayer,
    flows,
    loading,
    detailLoading,
    error,
    searchKeyword,
    searchResults,
    activeTab,
    // Computed
    sortedLayers,
    overallCompletion,
    totalFiles,
    totalModules,
    totalTests,
    statusCounts,
    filteredLayers,
    // Actions
    fetchLayers,
    fetchFlows,
    fetchLayerDetail,
    doSearch,
    setActiveTab,
    init,
  }
})
