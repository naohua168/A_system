<template>
  <div class="hot-reason-page">
    <!-- 顶栏 -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">题材热点</h2>
        <span class="page-subtitle">今日强势股题材归因 · 概念聚类分析</span>
      </div>
      <div class="header-right">
        <ReviewDatePicker @change="(d:string) => { reviewDate.value = d; fetchAll() }" />
        <span class="live-indicator" v-if="lastUpdated && !reviewDate">
          <span class="live-dot" /> {{ lastUpdated }}
        </span>
        <span class="today-label">{{ reviewDate || '今日 · ' + todayStr }}</span>
        <el-button v-if="error" type="warning" size="small" @click="fetchAll" :loading="loading">重试</el-button>
      </div>
    </div>

    <!-- 加载骨架 -->
    <template v-if="loading">
      <div class="skeleton-placeholder" />
    </template>

    <!-- 错误状态 -->
    <template v-else-if="error">
      <div class="empty-state">
        <div class="empty-icon">⚠</div>
        <div class="empty-text">{{ error }}</div>
        <el-button size="small" type="primary" @click="fetchAll">重新加载</el-button>
      </div>
    </template>

    <!-- 空数据 -->
    <template v-else-if="!enrichedRecords.length">
      <div class="empty-state">
        <div class="empty-icon">📭</div>
        <div class="empty-text">暂无题材热点数据</div>
          <el-button size="small" @click="fetchAll">刷新重试</el-button>
      </div>
    </template>

    <!-- 正常数据 -->
    <template v-else>
      <!-- 概览统计 -->
      <div class="stats-row">
        <div class="stat-item">
          <span class="stat-value">{{ enrichedRecords.length }}</span>
          <span class="stat-label">强势题材股</span>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <span class="stat-value">{{ concepts.length }}</span>
          <span class="stat-label">活跃概念</span>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <span class="stat-value" :class="zhangTingCount > 0 ? 'text-rise' : ''">{{ zhangTingCount }}</span>
          <span class="stat-label">涨停</span>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <span class="stat-value" :class="avgChangePct >= 0 ? 'text-rise' : 'text-fall'">{{ avgChangePct >= 0 ? '+' : '' }}{{ avgChangePct.toFixed(2) }}%</span>
          <span class="stat-label">平均涨幅</span>
        </div>
        <div class="stat-divider" />
        <div class="stat-item highlight">
          <span class="stat-value text-primary">{{ topConcept?.name || '-' }}</span>
          <span class="stat-label">{{ topConcept ? `最强概念 · ${topConcept.stockCount}只股票` : '' }}</span>
        </div>
      </div>

      <!-- 概念活跃度卡片区 -->
      <div class="concept-section">
        <div class="section-header">
          <h3>概念活跃度</h3>
          <div class="concept-search-wrap">
            <el-input v-model="conceptFilter" placeholder="搜索概念..." size="small" clearable
              style="width:180px" prefix-icon="Search" />
          </div>
        </div>
        <div class="concept-grid" v-if="visibleConcepts.length">
          <div v-for="c in visibleConcepts" :key="c.name"
            class="concept-card" :class="{ active: selectedConcept === c.name }"
            @click="toggleConcept(c.name)">
            <div class="concept-name">{{ c.name }}</div>
            <div class="concept-stats">
              <span class="concept-count">{{ c.stockCount }}只</span>
              <span :class="['concept-change', (c.avgChange || 0) >= 0 ? 'text-rise' : 'text-fall']">
                {{ (c.avgChange || 0) >= 0 ? '+' : '' }}{{ (c.avgChange || 0).toFixed(2) }}%
              </span>
            </div>
            <div class="concept-bar-row">
              <div class="concept-bar-track">
                <div class="concept-bar-fill" :style="{ width: c.stockCount / maxConceptCount * 100 + '%',
                  background: (c.avgChange || 0) >= 0 ? '#D93026' : '#34A853' }" />
              </div>
              <span class="concept-zt">涨停{{ c.ztCount }}</span>
            </div>
          </div>
        </div>
        <div v-else class="concept-empty">未匹配到概念，换个关键词试试</div>
      </div>

      <!-- 强势股明细 -->
      <div class="detail-section">
        <div class="section-header">
          <h3>
            强势股明细
            <span class="section-subtitle" v-if="selectedConcept">· 概念：{{ selectedConcept }}</span>
          </h3>
          <el-button v-if="selectedConcept" size="small" text @click="selectedConcept = ''">清除筛选</el-button>
        </div>
        <el-table :data="filteredRecords" stripe style="width:100%" @row-click="goToStock"
          :header-cell-style="{ background: '#f5f6fa', color: '#666', fontWeight: 500, fontSize: '12px', padding: '10px 8px' }"
          :cell-style="{ padding: '8px' }" size="small">
          <el-table-column label="#" width="44" type="index" align="center" />
          <el-table-column prop="stockCode" label="代码" width="90">
            <template #default="{ row }">
              <span class="stock-code">{{ row.stockCode }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="stockName" label="名称" width="90" />
          <el-table-column label="价格" width="80" align="right" prop="price">
            <template #default="{ row }">
              {{ row.price ? row.price.toFixed(2) : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="涨幅%" width="80" align="right" prop="changePct">
            <template #default="{ row }">
              <span v-if="row.changePct !== undefined && row.changePct !== null"
                :class="row.changePct >= 0 ? 'text-rise' : 'text-fall'"
                :style="row.changePct >= 9.9 ? 'font-weight:700' : ''">
                {{ row.changePct >= 0 ? '+' : '' }}{{ row.changePct.toFixed(2) }}%
              </span>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column label="换手%" width="70" align="right" prop="turnoverPct">
            <template #default="{ row }">
              {{ row.turnoverPct ? row.turnoverPct.toFixed(2) + '%' : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="流通市值" width="100" align="right" prop="mcapYi">
            <template #default="{ row }">
              {{ row.mcapYi ? row.mcapYi.toFixed(1) + '亿' : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="题材归因" min-width="260">
            <template #default="{ row }">
              <div class="reason-tags">
                <el-tag v-for="tag in parseTags(row.reason)" :key="tag" size="small"
                  :class="['reason-tag', { 'tag-active': selectedConcept === tag }]"
                  @click.stop="toggleConcept(tag)">
                  {{ tag }}
                </el-tag>
              </div>
            </template>
          </el-table-column>
        </el-table>
        <div class="stats-bar">
          共 <strong>{{ filteredRecords.length }}</strong> 只强势股出现题材信号
          <span class="text-muted" v-if="selectedConcept">（已筛选概念：{{ selectedConcept }}）</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { getHotReason, getHistoryHotReason } from '@/api/signal'
import ReviewDatePicker from '@/components/common/ReviewDatePicker.vue'
import { getStockList } from '@/api/market'
import { useApiRetry, safeRecords, safeNum, safeStr } from '@/composables/useApiRetry'

const router = useRouter()
const today = new Date()
const todayStr = today.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })

const loading = ref(false)
const error = ref<string | null>(null)
const rawHotData = ref<any[]>([])
const stockMap = ref<Record<string, any>>({})
const conceptFilter = ref('')
const selectedConcept = ref('')
const lastUpdated = ref('')
const reviewDate = ref('')
const pollingTimer = ref<ReturnType<typeof setInterval> | null>(null)
const stockRefreshTick = ref(0)  // 每4次poll刷新一次stock_basic

/** 仅获取题材热点（轻量快速） */
async function fetchHotOnly() {
  try {
    const hotRes = reviewDate.value ? await getHistoryHotReason(reviewDate.value) : await getHotReason()
    let arr: any[] = []
    const raw = hotRes as any
    if (Array.isArray(raw)) arr = raw
    else if (raw?.records && Array.isArray(raw.records)) arr = raw.records
    else if (raw?.data && Array.isArray(raw.data)) arr = raw.data
    rawHotData.value = arr
  } catch { /* stockMap有旧数据时静默失败 */ }
}

/** 获取题材数据 + stock_basic 全量 */
async function fetchAll() {
  loading.value = true
  error.value = null
  try {
    const [hotRes, listRes] = await Promise.all([
      reviewDate.value ? getHistoryHotReason(reviewDate.value) : getHotReason(),
      getStockList({ page: 1, size: 5000 })
    ])
    // 解析 hot_reason
    let arr: any[] = []
    const raw = hotRes as any
    if (Array.isArray(raw)) arr = raw
    else if (raw?.records && Array.isArray(raw.records)) arr = raw.records
    else if (raw?.data && Array.isArray(raw.data)) arr = raw.data
    rawHotData.value = arr

    // 解析 stock_basic
    const listRaw = listRes as any
    let stocks: any[] = []
    if (Array.isArray(listRaw)) stocks = listRaw
    else if (listRaw?.data?.records) stocks = listRaw.data.records
    else if (listRaw?.records) stocks = listRaw.records
    const sm: Record<string, any> = {}
    stocks.forEach((s: any) => {
      if (s.stockCode) sm[s.stockCode] = s
    })
    stockMap.value = sm
  } catch (e: any) {
    error.value = e?.message || '数据加载失败'
  } finally {
    loading.value = false
  }
}

/** 定时轮询：hot_reason每30秒刷新，stock_basic每2分钟刷新 */
function startPolling() {
  stopPolling()
  let tick = 0
  pollingTimer.value = setInterval(async () => {
    if (reviewDate.value) return
    tick++
    if (tick % 4 === 0) {
      await fetchAll()
    } else {
      await fetchHotOnly()
    }
    lastUpdated.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }, 30000)
}
function stopPolling() {
  if (pollingTimer.value) { clearInterval(pollingTimer.value); pollingTimer.value = null }
}

/** 数据合并：题材 + 实时价格/涨幅 */
const enrichedRecords = computed(() => {
  return rawHotData.value.map((r: any) => {
    const s = stockMap.value[r.stockCode] || {}
    return {
      ...r,
      price: s.price,
      changePct: s.changePct,
      turnoverPct: s.turnoverPct,
      mcapYi: s.mcapYi,
      pe: s.pe,
      amountWan: s.amountWan,
    }
  })
})

/** 解析概念标签 */
function parseTags(reason: string): string[] {
  if (!reason) return []
  return reason.split(/[+＋,，、]/).map(t => t.trim()).filter(Boolean)
}

/** 合并相似概念名：长标签包含短关键词时合并到关键词下 */
function mergeConceptName(tag: string): string {
  // 去除后缀干扰词
  let t = tag.replace(/概念$/, '').replace(/产业链$/, '').replace(/配套$/, '').trim()
  // 映射表：关键词 → 合并后名称
  const map: Record<string, string> = {
    '机器人': '机器人',
    '人形机器人': '机器人',
    '机器人轴承': '机器人',
    '机器人腱绳': '机器人',
    '机器狗': '机器人',
    '宇树科技': '机器人',
    'AI': 'AI人工智能',
    'AI算力': 'AI人工智能',
    'AI赋能': 'AI人工智能',
    'AI应用': 'AI人工智能',
    'AI视觉': 'AI人工智能',
    'AI眼镜': 'AI人工智能',
    'AI PCB': 'AI人工智能',
    '芯片': '半导体芯片',
    '芯片概念': '半导体芯片',
    '存储芯片': '半导体芯片',
    '存储芯片封测': '半导体芯片',
    '先进封装': '半导体芯片',
    '半导体清洗': '半导体芯片',
    '半导体设备': '半导体芯片',
    '半导体产业链': '半导体芯片',
    '光模块': '光通信',
    'CPO': '光通信',
    'CPO封装': '光通信',
    '光纤': '光通信',
    '光纤概念': '光通信',
    '光纤上游': '光通信',
    '光纤材料': '光通信',
    '多芯光纤': '光通信',
    '800G光模块': '光通信',
    '新能源': '新能源',
    '新能源汽配': '新能源',
    '新能源车检测': '新能源',
    '光伏概念': '新能源',
    '固态电池': '新能源',
    '储能': '新能源',
    '风光火储一体化': '新能源',
    '核电石墨': '新能源',
    '锂电': '新能源',
    '抽水蓄能': '新能源',
    '绿电': '电力',
    '绿色电力': '电力',
    '火力发电': '电力',
    '热电联产': '电力',
    '火电': '电力',
    '飞行汽车': '低空经济',
    '低空经济': '低空经济',
    '算力中心': '算力',
    '算力租赁': '算力',
    '定增': '定增/并购',
    '定增通过': '定增/并购',
    '定增AI服务器': '定增/并购',
    '并购重组': '定增/并购',
    '重大资产重组': '定增/并购',
    '外延并购': '定增/并购',
    '拟收购奇芯光电': '定增/并购',
    '股权转让': '股权变更',
    '股份转让': '股权变更',
    '控制权变更': '股权变更',
    '控制权拟变更': '股权变更',
    '实控人拟变更': '股权变更',
    '协议转让': '股权变更',
    '申请摘帽': 'ST摘帽',
    'ST摘帽预期': 'ST摘帽',
    '撤销退市风险警示': 'ST摘帽',
    '摘帽': 'ST摘帽',
    '一季报增长': '业绩增长',
    '业绩增长': '业绩增长',
    '营收增长': '业绩增长',
    '业绩改善': '业绩增长',
    '一季度扭亏': '业绩改善',
    '一季报扭亏': '业绩改善',
    '扭亏为盈': '业绩改善',
    '扭亏': '业绩改善',
    '业绩减亏': '业绩改善',
    '亏损收窄': '业绩改善',
    '碳化硅': '第三代半导体',
    '金刚石散热': '第三代半导体',
    '硅基材料': '第三代半导体',
    '高纯石英砂': '新材料',
    '硅光电倍增器': '新材料',
    '催化新材料': '新材料',
    '石墨电极龙头': '新材料',
    '有机硅': '新材料',
    'PI膜': '新材料',
    '碳纤维': '新材料',
    '磷化工': '化工',
    '碳酸锂': '化工',
    '碳酸锶涨价': '化工',
    '电池材料': '化工',
    '锰酸锂': '化工',
    '电解二氧化锰': '化工',
    '电子特气': '化工',
    '高速树脂': '化工',
    '石油化工': '化工',
    '光稳定剂': '化工',
    '消费电子': '消费电子',
    '小家电': '消费电子',
    '智能硬件': '消费电子',
    'LED照明': '消费电子',
    '跨境电商': '跨境电商',
    '家电零售': '跨境电商',
    '央企': '央企/国企',
    '国企': '央企/国企',
    '国企改革': '央企/国企',
    '国资': '央企/国企',
    '地方国资': '央企/国企',
    '北京国资': '央企/国企',
    '广西国资': '央企/国企',
    '河南国资': '央企/国企',
    '深圳国资': '央企/国企',
    '青岛国资': '央企/国企',
    '郑州国资': '央企/国企',
    '福建国资': '央企/国企',
    '湘潭国资': '央企/国企',
    '枣庄国资': '央企/国企',
    '佛山国资': '央企/国企',
    '汽车零部件': '汽车产业链',
    '汽车铝型材': '汽车产业链',
    '新能源汽配': '汽车产业链',
    '服务器': '服务器/算力',
    '液冷服务器': '服务器/算力',
    '温控设备': '服务器/算力',
    '高速铜连接': '服务器/算力',
    '回购': '回购/分红',
    '分红': '回购/分红',
    '分红计划': '回购/分红',
    '拟分红': '回购/分红',
    '增持': '回购/分红',
    '股东增持举牌': '回购/分红',
    '高管增持': '回购/分红',
    '股份回购': '回购/分红',
    '大飞机': '军工/航空',
    '商业航天': '军工/航空',
    '卫星通信': '军工/航空',
    'eVTOL模拟器': '军工/航空',
    '核医疗': '军工/航空',
    '生物医药': '生物医药',
    '大健康': '生物医药',
    '培育钻石': '生物医药',
  }
  const lower = t.toLowerCase()
  for (const [key, val] of Object.entries(map)) {
    if (t === key || t.includes(key) || lower === key.toLowerCase()) return val
  }
  // 剩余未映射的长尾标签按关键词就近合并
  return tag
}

/** 概念聚类（含合并） */
interface ConceptInfo {
  name: string
  stockCount: number
  ztCount: number
  avgChange: number
}

const concepts = computed<ConceptInfo[]>(() => {
  const map = new Map<string, { count: number; zt: number; totalChange: number }>()
  enrichedRecords.value.forEach((r: any) => {
    const tags = parseTags(r.reason)
    const chg = r.changePct ?? 0
    // 去重复合并名（一只股票只往同一概念算一次）
    const seen = new Set<string>()
    tags.forEach((tag: string) => {
      const merged = mergeConceptName(tag)
      if (seen.has(merged)) return
      seen.add(merged)
      const entry = map.get(merged) || { count: 0, zt: 0, totalChange: 0 }
      entry.count++
      entry.totalChange += chg
      if (chg >= 9.9) entry.zt++
      map.set(merged, entry)
    })
  })
  return Array.from(map.entries())
    .map(([name, v]) => ({
      name,
      stockCount: v.count,
      ztCount: v.zt,
      avgChange: v.totalChange / v.count,
    }))
    .sort((a, b) => b.stockCount - a.stockCount)
})

/** 最大概念股数（用于进度条比例） */
const maxConceptCount = computed(() => Math.max(...concepts.value.map(c => c.stockCount), 1))

/** 筛选后的概念 */
const visibleConcepts = computed(() => {
  if (!conceptFilter.value) return concepts.value.slice(0, 20)
  const kw = conceptFilter.value.toLowerCase()
  return concepts.value.filter(c => c.name.includes(kw)).slice(0, 30)
})

/** 根据选中概念过滤的股票 */
const filteredRecords = computed(() => {
  if (!selectedConcept.value) return enrichedRecords.value
  return enrichedRecords.value.filter((r: any) => {
    const tags = parseTags(r.reason)
    return tags.some(t => mergeConceptName(t) === selectedConcept.value)
  })
})

/** 切换概念筛选（支持合并概念和原始标签） */
function toggleConcept(name: string) {
  const merged = mergeConceptName(name)
  selectedConcept.value = selectedConcept.value === merged ? '' : merged
}

/** 统计 */
const zhangTingCount = computed(() =>
  enrichedRecords.value.filter((r: any) => (r.changePct ?? 0) >= 9.9).length
)
const avgChangePct = computed(() => {
  const vals = enrichedRecords.value.map((r: any) => r.changePct ?? 0)
  return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0
})
const topConcept = computed(() => concepts.value[0] || null)

function onDateChange() { fetchAll(); startPolling() }  // 预留，后续如有日期选择可用
function goToStock(row: any) {
  if (row.stockCode) router.push(`/stock/${row.stockCode}`)
}

onMounted(() => { fetchAll(); startPolling() })
onUnmounted(stopPolling)
</script>

<style scoped lang="scss">
.hot-reason-page { padding: 20px 24px; max-width: 1300px; margin: 0 auto; }
.text-rise { color: #D93026; }
.text-fall { color: #34A853; }
.text-muted { color: #999; }
.text-primary { color: #1890FF; }

/* 顶栏 */
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 18px; }
.page-title { font-size: 22px; font-weight: 700; color: #333; margin: 0; }
.page-subtitle { display: block; font-size: 13px; color: #999; margin-top: 4px; }
.header-right { display: flex; gap: 8px; align-items: center; }

/* 骨架/空态 */
.skeleton-placeholder { height: 300px; background: #f5f6fa; border-radius: 6px; }
.live-indicator { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; color: #999; margin-right: 8px; }
.live-dot { width: 6px; height: 6px; border-radius: 50%; background: #34A853; animation: pulse-dot 1.5s infinite; }
@keyframes pulse-dot { 0%,100%{opacity:1} 50%{opacity:0.4} }
.today-label { font-size: 13px; color: #666; background: #f5f6fa; padding: 3px 10px; border-radius: 4px; }
.empty-state { text-align: center; padding: 80px 0; color: #999; }
.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-text { font-size: 14px; margin-bottom: 16px; }

/* 概览统计 */
.stats-row {
  display: flex; align-items: center; gap: 0; padding: 16px 20px;
  background: #fff; border: 1px solid #e8e8e8; border-radius: 6px; margin-bottom: 16px;
}
.stat-item { display: flex; flex-direction: column; align-items: center; padding: 0 16px; min-width: 90px; }
.stat-item.highlight { flex: 1; }
.stat-value { font-size: 20px; font-weight: 700; color: #333; line-height: 1.3; }
.stat-label { font-size: 12px; color: #999; margin-top: 2px; white-space: nowrap; }
.stat-divider { width: 1px; height: 36px; background: #eee; flex-shrink: 0; }

/* 概念区 */
.concept-section { margin-bottom: 16px; }
.section-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;
  h3 { font-size: 15px; font-weight: 600; color: #333; margin: 0; display: flex; align-items: center; gap: 8px; }
}
.section-subtitle { font-size: 13px; font-weight: 400; color: #999; }

.concept-grid { display: flex; flex-wrap: wrap; gap: 10px; }
.concept-card {
  flex: 0 0 calc(20% - 8px); min-width: 150px; max-width: 240px;
  padding: 12px 14px; background: #fff; border: 1px solid #e8e8e8;
  border-radius: 6px; cursor: pointer; transition: all .15s;
  &:hover { border-color: #1890FF; box-shadow: 0 1px 4px rgba(24,144,255,0.08); }
  &.active { border-color: #1890FF; background: #f0f7ff; }
}
.concept-name { font-size: 13px; font-weight: 600; color: #333; margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.concept-stats { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.concept-count { font-size: 22px; font-weight: 700; color: #333; }
.concept-change { font-size: 12px; font-weight: 600; }
.concept-bar-row { display: flex; align-items: center; gap: 6px; }
.concept-bar-track { flex: 1; height: 4px; background: #eee; border-radius: 2px; overflow: hidden; }
.concept-bar-fill { height: 100%; border-radius: 2px; transition: width .3s; }
.concept-zt { font-size: 11px; color: #999; white-space: nowrap; }
.concept-empty { padding: 20px; text-align: center; color: #999; font-size: 13px; background: #fff; border: 1px dashed #ddd; border-radius: 6px; }

/* 明细 */
.detail-section { background: #fff; border: 1px solid #e8e8e8; border-radius: 6px; padding: 16px; }
.stock-code { font-family: 'SF Mono', 'Consolas', monospace; font-weight: 600; cursor: pointer;
  &:hover { color: #1890FF; } }
.reason-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.reason-tag { cursor: pointer; background: #f0f5ff; color: #1890FF; border: 1px solid transparent;
  &:hover { background: #e6f0ff; }
  &.tag-active { background: #1890FF; color: #fff; border-color: #1890FF; } }
.stats-bar { margin-top: 12px; font-size: 13px; color: #999; text-align: right;
  strong { color: #333; } }

@media (max-width: 900px) {
  .concept-card { flex: 0 0 calc(33.33% - 8px); }
}
@media (max-width: 600px) {
  .concept-card { flex: 0 0 calc(50% - 6px); }
  .stats-row { flex-wrap: wrap; gap: 8px; }
  .stat-divider { display: none; }
}
</style>
