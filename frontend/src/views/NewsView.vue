<template>
  <div class="news-view">
    <div class="page-header">
      <h2>市场资讯</h2>
    </div>

    <!-- ── 日期导航 ── -->
    <div class="date-nav">
      <button class="nav-btn" @click="prevDay" title="前一天">
        <el-icon><ArrowLeft /></el-icon>
      </button>

      <el-popover
        :visible="showDatePicker"
        trigger="manual"
        placement="bottom"
        :width="300"
        popper-class="news-popper"
      >
        <template #reference>
          <div class="date-display" @click="showDatePicker = !showDatePicker">
            <span class="date-text">{{ dateDisplayText }}</span>
            <span
              v-if="dateBadgeText"
              class="date-badge"
              :class="dateBadgeText === '今天' ? 'badge-today' : 'badge-yesterday'"
            >{{ dateBadgeText }}</span>
            <el-icon class="cal-icon"><Calendar /></el-icon>
          </div>
        </template>
        <div class="calendar-wrap">
          <el-date-picker
            v-model="activeDate"
            type="date"
            value-format="YYYY-MM-DD"
            inline
            @change="onDatePick"
          />
        </div>
      </el-popover>

      <button class="nav-btn" @click="nextDay" :disabled="!canGoNext">
        <el-icon><ArrowRight /></el-icon>
      </button>
    </div>

    <!-- ── 快捷日期条 ── -->
    <div class="date-strip" v-if="availableDates.length > 0">
      <button
        v-for="d in availableDates" :key="d"
        :class="['date-chip', { active: d === activeDate }]"
        @click="activeDate = d"
      >{{ formatDateShort(d) }}</button>
    </div>

    <!-- ── 加载态 ── -->
    <div v-if="loading" class="state-box">
      <div class="sk-list">
        <div v-for="n in 5" :key="n" class="sk-item">
          <div class="sk-dot"></div>
          <div class="sk-body">
            <div class="sk-line w-30"></div>
            <div class="sk-line w-80"></div>
            <div class="sk-line w-60"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── 错误态 ── -->
    <div v-else-if="error" class="state-box">
      <div class="error-state">
        <el-icon :size="40" color="#e74c3c"><WarningFilled /></el-icon>
        <p class="error-text">{{ error }}</p>
        <el-button type="primary" size="small" @click="loadData">重新加载</el-button>
      </div>
    </div>

    <!-- ── 新闻列表 ── -->
    <div v-else class="news-list">
      <div v-if="currentItems.length === 0" class="state-box">
        <div class="empty-state">
          <el-icon :size="40" color="#ccc"><Document /></el-icon>
          <p class="empty-text">该日期暂无资讯</p>
        </div>
      </div>

      <template v-else>
        <div
          v-for="(item, idx) in currentItems" :key="item.id"
          class="nl-item"
          @click="openLink(item)"
        >
          <div class="nl-left">
            <span class="nl-time" :class="{ 'nl-time-hidden': idx > 0 && item.time.slice(0,5) === currentItems[idx-1].time.slice(0,5) }">{{ item.time }}</span>
            <span class="nl-dot"></span>
          </div>
          <div class="nl-card">
            <div class="nl-meta">
              <el-tag
                size="small"
                :type="item.type === 'cls' ? '' : 'success'"
                class="nl-tag"
              >{{ item.type === 'cls' ? '快讯' : '资讯' }}</el-tag>
              <span class="nl-source">{{ item.source }}</span>
            </div>
            <h4 class="nl-title">{{ item.title }}</h4>
            <p class="nl-summary">{{ item.content }}</p>
          </div>
        </div>

        <div class="load-more" v-if="hasMore">
          <el-button :loading="loadingMore" text type="primary" @click="loadMore">
            {{ loadingMore ? '加载中...' : '加载更多' }}
          </el-button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ArrowLeft, ArrowRight, Calendar, WarningFilled, Document } from '@element-plus/icons-vue'
import { getClsNews, getGlobalNews } from '@/api/info'
import type { ClsNewsItem, GlobalNewsItem } from '@/types'

// ══════════════════════════════════════════
// 工具函数（放在最前面，避免 computed 引用未定义）
// ══════════════════════════════════════════

const $W = ['日', '一', '二', '三', '四', '五', '六']

function pad2(n: number): string {
  return String(n).padStart(2, '0')
}

function fmtDate(d: Date): string {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
}

/** 安全解析 YYYY-MM-DD 字符串 */
function dateFromStr(s: string): Date | null {
  if (!s || typeof s !== 'string') return null
  const p = s.split('-')
  if (p.length < 3) return null
  const [y, m, d] = [parseInt(p[0]), parseInt(p[1]) - 1, parseInt(p[2])]
  if (isNaN(y) || isNaN(m) || isNaN(d)) return null
  return new Date(y, m, d)
}

/** 解析 publishTime 字段，兼容只存了时间的情况 */
function parsePubTime(s: string): { date: string; time: string } {
  if (!s) return { date: '', time: '' }

  // "2026-05-27 22:47:10" → 完整日期时间
  if (s.includes(' ')) {
    const p = s.split(' ')
    return { date: p[0], time: (p[1] || '00:00').substring(0, 5) }
  }

  // "22:47:10" → 只有时间（cls_news 数据只存了时间无日期）
  // 用当前时间对比：如果存储时间小时 > 当前小时，说明是前一天的
  if (s.includes(':')) {
    const now = new Date()
    const storedHour = parseInt(s.substring(0, 2), 10)
    const curHour = now.getHours()
    if (!isNaN(storedHour) && storedHour > curHour + 1) {
      now.setDate(now.getDate() - 1)
    }
    return { date: fmtDate(now), time: s.substring(0, 5) }
  }

  // "2026-05-27" → 只有日期
  return { date: s, time: '00:00' }
}

function formatDateShort(s: string): string {
  const d = dateFromStr(s)
  if (!d) return s || '?'
  return `${d.getMonth() + 1}/${d.getDate()}`
}

// ══════════════════════════════════════════
// 类型
// ══════════════════════════════════════════

interface FeedItem {
  id: string
  type: 'cls' | 'global'
  title: string
  date: string
  time: string
  content: string
  source: string
  url?: string
}

// ══════════════════════════════════════════
// 状态
// ══════════════════════════════════════════

const today = new Date()
const tomorrowStr = (() => {
  const d = new Date(today)
  d.setDate(d.getDate() + 1)
  return fmtDate(d)
})()

const activeDate = ref(fmtDate(today))
const availableDates = ref<string[]>([])
const showDatePicker = ref(false)

const loading = ref(true)
const error = ref('')
const loadingMore = ref(false)
const allItems = ref<FeedItem[]>([])
const clsDone = ref(false)
const globalDone = ref(false)

// ══════════════════════════════════════════
// computed
// ══════════════════════════════════════════

const currentItems = computed(() =>
  allItems.value
    .filter(i => i.date === activeDate.value)
    .sort((a, b) => a.time.localeCompare(b.time))
)

const hasMore = computed(() => !clsDone.value || !globalDone.value)

const dateDisplayText = computed(() => {
  const d = dateFromStr(activeDate.value)
  if (!d || isNaN(d.getTime())) return activeDate.value
  return `${d.getMonth() + 1}月${d.getDate()}日 周${$W[d.getDay()]}`
})

const dateBadgeText = computed(() => {
  const t = fmtDate(today)
  if (activeDate.value === t) return '今天'
  const y = new Date(today)
  y.setDate(y.getDate() - 1)
  if (activeDate.value === fmtDate(y)) return '昨天'
  return ''
})

const canGoNext = computed(() => activeDate.value < tomorrowStr)

// ══════════════════════════════════════════
// 数据转换
// ══════════════════════════════════════════

function cls2feed(item: ClsNewsItem): FeedItem {
  const { date, time } = parsePubTime(item.publishTime)
  return { id: `cls-${item.id}`, type: 'cls', title: item.title, date, time, content: item.content || '', source: '财联社' }
}

function global2feed(item: GlobalNewsItem): FeedItem {
  const { date, time } = parsePubTime(item.publishTime)
  return { id: `global-${item.id}`, type: 'global', title: item.title, date, time, content: item.summary || '', source: item.source || '全球资讯', url: item.url }
}

// ══════════════════════════════════════════
// 数据加载
// ══════════════════════════════════════════

async function loadData() {
  loading.value = true
  error.value = ''
  allItems.value = []
  clsDone.value = false
  globalDone.value = false

  try {
    const [clsRes, globalRes] = await Promise.all([
      getClsNews(100).catch(() => ({ records: [] as ClsNewsItem[], total: 0 })),
      getGlobalNews(100).catch(() => ({ records: [] as GlobalNewsItem[], total: 0 })),
    ])

    // 转换 + 去重
    const raw: FeedItem[] = [
      ...((clsRes?.records || []).map(cls2feed)),
      ...((globalRes?.records || []).map(global2feed)),
    ]
    const seen = new Set<string>()
    raw.forEach(i => { if (!seen.has(i.id)) { seen.add(i.id); allItems.value.push(i) } })

    // 可用日期（按从早到晚排列）
    const ds = new Set<string>()
    allItems.value.forEach(i => {
      if (i.date && /^\d{4}-\d{2}-\d{2}$/.test(i.date)) ds.add(i.date)
    })
    availableDates.value = Array.from(ds).sort()

    // 默认定位到今天或最近有数据的日期
    const todayStr = fmtDate(today)
    if (availableDates.value.includes(todayStr)) {
      activeDate.value = todayStr
    } else if (availableDates.value.length > 0) {
      activeDate.value = availableDates.value[0]
    }

    clsDone.value = (clsRes?.records || []).length < 100
    globalDone.value = (globalRes?.records || []).length < 100
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  loadingMore.value = true
  try {
    const ps: Promise<any>[] = []
    if (!clsDone.value) {
      ps.push(
        getClsNews(100).then((r: any) => {
          const items = (r?.records || []).map(cls2feed)
          const exist = new Set(allItems.value.map(i => i.id))
          items.forEach(i => { if (!exist.has(i.id)) { allItems.value.push(i) } })
          clsDone.value = items.length < 100
        })
      )
    }
    if (!globalDone.value) {
      ps.push(
        getGlobalNews(100).then((r: any) => {
          const items = (r?.records || []).map(global2feed)
          const exist = new Set(allItems.value.map(i => i.id))
          items.forEach(i => { if (!exist.has(i.id)) { allItems.value.push(i) } })
          globalDone.value = items.length < 100
        })
      )
    }
    await Promise.all(ps)
    const ds = new Set<string>()
    allItems.value.forEach(i => { if (/^\d{4}-\d{2}-\d{2}$/.test(i.date)) ds.add(i.date) })
    availableDates.value = Array.from(ds).sort().reverse()
  } catch { /* silent */ } finally {
    loadingMore.value = false
  }
}

// ══════════════════════════════════════════
// 交互
// ══════════════════════════════════════════

function prevDay() {
  const d = dateFromStr(activeDate.value)
  if (!d) return
  d.setDate(d.getDate() - 1)
  activeDate.value = fmtDate(d)
}

function nextDay() {
  const d = dateFromStr(activeDate.value)
  if (!d) return
  d.setDate(d.getDate() + 1)
  const maxD = new Date(today)
  maxD.setDate(maxD.getDate() + 1)
  if (d > maxD) return
  activeDate.value = fmtDate(d)
}

function onDatePick(val: string) {
  showDatePicker.value = false
  if (val) activeDate.value = val
}

function openLink(item: FeedItem) {
  if (item.url) window.open(item.url, '_blank')
}

onMounted(loadData)
</script>

<style scoped lang="scss">
.news-view {
  max-width: 860px;
  margin: 0 auto;
  padding: $spacing-lg;
}

.page-header {
  margin-bottom: $spacing-xl;
  h2 { margin: 0 0 $spacing-lg; font-weight: 700; font-size: 22px; }
}

// ── 日期导航 ──
.date-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: $spacing-xs;
  margin-bottom: $spacing-md;

  .nav-btn {
    width: 36px; height: 36px;
    border-radius: 50%;
    border: 1px solid $hairline;
    background: $canvas;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s;
    color: $ink-muted-48;
    flex-shrink: 0;

    &:hover:not(:disabled) { border-color: $primary; color: $primary; background: rgba($primary, 0.04); }
    &:disabled { opacity: 0.3; cursor: not-allowed; }
  }

  .date-display {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 16px;
    border-radius: $rounded-md;
    cursor: pointer;
    user-select: none;
    transition: background 0.15s;

    &:hover { background: $canvas-parchment; }

    .date-text { font-size: 17px; font-weight: 600; color: $ink; white-space: nowrap; }
    .cal-icon { font-size: 16px; color: $ink-muted-48; flex-shrink: 0; }
  }

  .date-badge {
    font-size: 11px; font-weight: 600; padding: 2px 10px; border-radius: $rounded-pill;
    flex-shrink: 0; margin-left: -6px;

    &.badge-today { background: $rise; color: white; }
    &.badge-yesterday { background: $ink-muted-48; color: white; }
  }
}

// ── 日历弹出 ──
:deep(.calendar-wrap) {
  padding: 8px;
  .el-date-picker { width: 100%; }
}

// ── 来源标签 ──
.source-tabs {
  display: flex; gap: $spacing-xs; margin-bottom: $spacing-sm; justify-content: center;

  .source-btn {
    padding: 6px 20px;
    border: 1px solid $hairline; background: $canvas; border-radius: $rounded-pill;
    font-size: 13px; font-weight: 500; color: $ink-muted-48; cursor: pointer; transition: all 0.2s;

    &:hover { border-color: $primary; color: $primary; }
    &.active { background: $primary; border-color: $primary; color: white; }
  }
}

// ── 日期快捷条 ──
.date-strip {
  display: flex; gap: 6px; padding: $spacing-sm 0 $spacing-md; justify-content: center;
  flex-wrap: wrap;

  .date-chip {
    padding: 4px 12px; border-radius: $rounded-pill;
    border: 1px solid $hairline; background: $canvas;
    font-size: 12px; color: $ink-muted-48; cursor: pointer; transition: all 0.2s; white-space: nowrap;

    &:hover { border-color: $primary; color: $primary; }
    &.active { background: $primary; border-color: $primary; color: white; font-weight: 600; }
  }
}

// ── 状态 ──
.state-box {
  min-height: 320px; display: flex; align-items: center; justify-content: center;
}

// skeleton
.sk-list { width: 100%; display: flex; flex-direction: column; gap: $spacing-lg; }

.sk-item {
  display: flex; gap: $spacing-lg; align-items: flex-start;

  .sk-dot {
    width: 10px; height: 10px; border-radius: 50%; background: $hairline;
    flex-shrink: 0; margin-top: 6px; animation: pulse 1.5s infinite;
  }
  .sk-body { flex: 1; }
  .sk-line {
    height: 14px; border-radius: 4px; background: $hairline; margin-bottom: 8px; animation: pulse 1.5s infinite;
    &.w-30 { width: 30%; } &.w-60 { width: 60%; } &.w-80 { width: 80%; }
  }
}

@keyframes pulse { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }

.error-state { text-align: center; display: flex; flex-direction: column; align-items: center; gap: $spacing-md; }
.error-text { color: $ink-muted-48; font-size: 14px; }
.empty-state { text-align: center; display: flex; flex-direction: column; align-items: center; gap: $spacing-sm; }
.empty-text { color: $ink-muted-48; font-size: 14px; margin: 0; }

// ══════════════════════════════════════════
// 新闻列表
// ══════════════════════════════════════════

.news-list { position: relative; padding-left: 56px; }

// 竖线
.news-list::before {
  content: ''; position: absolute; left: 26px; top: 12px; bottom: 12px;
  width: 2px;
  background: linear-gradient(to bottom, transparent 0%, $hairline 6%, $hairline 94%, transparent 100%);
  pointer-events: none;
}

.nl-item {
  position: relative; display: flex; align-items: flex-start; gap: $spacing-md;
  margin-bottom: $spacing-md; cursor: pointer;

  &:last-child { margin-bottom: 0; }
}

// 左侧时间 + 圆点
.nl-left {
  position: absolute; left: -56px; top: 18px;
  display: flex; align-items: center; gap: 6px;
  width: 56px; justify-content: flex-end;

  .nl-time { font-size: 12px; font-weight: 600; color: $ink-muted-48; white-space: nowrap; transition: color 0.2s; }
  .nl-time-hidden { visibility: hidden; }

  .nl-dot {
    width: 10px; height: 10px; border-radius: 50%; background: $primary;
    border: 2px solid $canvas; box-shadow: 0 0 0 2px rgba($primary, 0.2);
    flex-shrink: 0; transition: all 0.25s;
  }
}

.nl-item:hover {
  .nl-dot { transform: scale(1.35); background: $rise; box-shadow: 0 0 0 3px rgba($rise, 0.25); }
  .nl-time { color: $ink; font-weight: 700; }
}

// 卡片
.nl-card {
  flex: 1; background: $canvas; border: 1px solid $divider-soft; border-radius: $rounded-md;
  padding: $spacing-md $spacing-lg; transition: all 0.2s;

  &:hover {
    transform: translateY(-1px); box-shadow: $shadow-elevated; border-color: rgba($primary, 0.15);
  }

  .nl-meta { display: flex; align-items: center; gap: $spacing-xs; margin-bottom: $spacing-xs; }
  .nl-tag { border: none; font-weight: 600; height: 22px; line-height: 22px; padding: 0 8px; }
  .nl-source { font-size: 11px; color: $ink-muted-48; }

  .nl-title {
    font-size: 15px; font-weight: 600; line-height: 1.4; color: $ink; margin: 0 0 $spacing-xs;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
    &:hover { color: $primary; }
  }

  .nl-summary {
    font-size: 13px; line-height: 1.5; color: $ink-muted-48; margin: 0;
    display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
  }
}

.load-more {
  text-align: center; padding: $spacing-lg 0 $spacing-xl; position: relative; left: -28px;
}
</style>
