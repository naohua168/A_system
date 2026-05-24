<template>
  <div class="skeleton-wrap" :style="wrapStyle">
    <!-- 表格骨架 -->
    <template v-if="type === 'table'">
      <div v-for="r in rows" :key="r" class="skeleton-row" :style="{ animationDelay: `${(r - 1) * 0.08}s` }">
        <div class="skeleton-cell" v-for="(w, c) in colWidths" :key="c"
          :style="{ width: isPct(w) ? w : w + 'px', animationDelay: `${(r - 1) * 0.08 + c * 0.05}s` }" />
      </div>
    </template>

    <!-- 卡片骨架 -->
    <template v-else-if="type === 'card'">
      <div class="skeleton-card-grid" :style="{ gridTemplateColumns: `repeat(${cols || 4}, 1fr)` }">
        <div v-for="i in (rows * (cols || 4))" :key="i" class="skeleton-card"
          :style="{ animationDelay: `${(i - 1) * 0.06}s` }">
          <div class="skeleton-card-title" />
          <div class="skeleton-card-value" />
          <div class="skeleton-card-sub" />
        </div>
      </div>
    </template>

    <!-- 列表骨架 -->
    <template v-else-if="type === 'list'">
      <div v-for="r in rows" :key="r" class="skeleton-list-item"
        :style="{ animationDelay: `${(r - 1) * 0.08}s` }">
        <div class="skeleton-list-line skeleton-list-line--short" />
        <div class="skeleton-list-line skeleton-list-line--long" />
        <div class="skeleton-list-line skeleton-list-line--medium" />
      </div>
    </template>

    <!-- 图表骨架 -->
    <template v-else-if="type === 'chart'">
      <div class="skeleton-chart" :style="{ height: height || '300px' }">
        <div class="skeleton-chart-bars">
          <div v-for="i in 12" :key="i" class="skeleton-chart-bar"
            :style="{ height: `${30 + Math.random() * 50}%`, animationDelay: `${i * 0.08}s` }" />
        </div>
        <div class="skeleton-chart-x">
          <div v-for="i in 6" :key="i" class="skeleton-chart-xtick" />
        </div>
      </div>
    </template>

    <!-- 自定义自定义骨架插槽 -->
    <slot v-else />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  type?: 'table' | 'card' | 'list' | 'chart' | 'custom'
  rows?: number
  cols?: number
  colWidths?: string[]
  height?: string
  padding?: string
  borderRadius?: string
}>(), {
  type: 'table',
  rows: 5,
  cols: 4,
  colWidths: () => ['35%', '20%', '15%', '12%', '12%'],
  height: '300px',
  padding: '0',
  borderRadius: '12px',
})

function isPct(v: string) { return v.endsWith('%') }

const wrapStyle = computed(() => ({
  padding: props.padding || '0',
  borderRadius: props.borderRadius,
}))
</script>

<style scoped>
.skeleton-wrap { width: 100%; overflow: hidden; }

/* ===== 表格骨架 ===== */
.skeleton-row { display: flex; gap: 16px; padding: 14px 16px; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.04); }
.skeleton-cell { height: 14px; border-radius: 4px; background: linear-gradient(90deg, rgba(255,255,255,0.06) 25%, rgba(255,255,255,0.10) 50%, rgba(255,255,255,0.06) 75%); background-size: 200% 100%; animation: shimmer 1.8s ease-in-out infinite; }

/* ===== 卡片骨架 ===== */
.skeleton-card-grid { display: grid; gap: 12px; }
.skeleton-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; display: flex; flex-direction: column; gap: 10px; }
.skeleton-card-title { height: 12px; width: 50%; border-radius: 4px; background: linear-gradient(90deg, rgba(255,255,255,0.05) 25%, rgba(255,255,255,0.09) 50%, rgba(255,255,255,0.05) 75%); background-size: 200% 100%; animation: shimmer 1.8s ease-in-out infinite; }
.skeleton-card-value { height: 22px; width: 35%; border-radius: 4px; background: linear-gradient(90deg, rgba(255,255,255,0.05) 25%, rgba(255,255,255,0.09) 50%, rgba(255,255,255,0.05) 75%); background-size: 200% 100%; animation: shimmer 1.8s ease-in-out infinite; }
.skeleton-card-sub { height: 10px; width: 60%; border-radius: 4px; background: linear-gradient(90deg, rgba(255,255,255,0.03) 25%, rgba(255,255,255,0.07) 50%, rgba(255,255,255,0.03) 75%); background-size: 200% 100%; animation: shimmer 1.8s ease-in-out infinite; }

/* ===== 列表骨架 ===== */
.skeleton-list-item { padding: 12px 16px; display: flex; flex-direction: column; gap: 8px; border-bottom: 1px solid rgba(255,255,255,0.04); }
.skeleton-list-line { height: 12px; border-radius: 4px; background: linear-gradient(90deg, rgba(255,255,255,0.05) 25%, rgba(255,255,255,0.09) 50%, rgba(255,255,255,0.05) 75%); background-size: 200% 100%; animation: shimmer 1.8s ease-in-out infinite; }
.skeleton-list-line--short { width: 30%; }
.skeleton-list-line--long { width: 80%; }
.skeleton-list-line--medium { width: 55%; }

/* ===== 图表骨架 ===== */
.skeleton-chart { display: flex; flex-direction: column; justify-content: flex-end; gap: 8px; padding: 20px; }
.skeleton-chart-bars { display: flex; align-items: flex-end; gap: 8px; height: 100%; }
.skeleton-chart-bar { flex: 1; border-radius: 4px 4px 0 0; background: linear-gradient(90deg, rgba(255,255,255,0.05) 25%, rgba(255,255,255,0.09) 50%, rgba(255,255,255,0.05) 75%); background-size: 200% 100%; animation: shimmer 1.8s ease-in-out infinite; }
.skeleton-chart-x { display: flex; gap: 8px; }
.skeleton-chart-xtick { flex: 1; height: 8px; border-radius: 2px; background: rgba(255,255,255,0.04); }

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
</style>
