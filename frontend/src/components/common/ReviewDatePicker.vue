<template>
  <div class="review-date-picker">
    <el-date-picker
      v-model="selectedDate"
      type="date"
      :disabled-date="disableFuture"
      placeholder="选择复盘日期"
      format="YYYY-MM-DD"
      value-format="YYYY-MM-DD"
      :clearable="true"
      @change="onDateChange"
    />
    <el-button
      v-if="selectedDate"
      size="small"
      type="warning"
      plain
      @click="clearDate"
    >
      返回今日
    </el-button>
    <el-tag v-if="selectedDate" type="info" size="small" effect="plain" class="review-tag">
      复盘模式 {{ selectedDate }}
    </el-tag>
    <el-tag v-if="!selectedDate && isTradingSession" type="warning" size="small" effect="dark" class="downgrade-tag">
      ⏳ 交易时段 · 展示上一个交易日数据
    </el-tag>
    <el-tag v-else-if="!selectedDate && !isTradingDay" type="info" size="small" effect="plain" class="downgrade-tag">
      📅 非交易日 · 展示最近交易日数据
    </el-tag>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: string
}>(), {
  modelValue: '',
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: string): void
  (e: 'change', val: string): void
}>()

const selectedDate = ref(props.modelValue || '')

/** 纯复盘系统：交易时段展示昨日数据，收盘后展示今日数据 */
const isTradingDay = computed(() => {
  const d = new Date()
  const day = d.getDay()
  return day > 0 && day < 6  // 周一到周五
})
const isTradingSession = computed(() => {
  if (!isTradingDay.value) return false
  const h = new Date().getHours()
  return h >= 9 && h < 15  // 09:00~15:00
})

watch(() => props.modelValue, (val) => {
  selectedDate.value = val || ''
})

function disableFuture(time: Date) {
  // 开发阶段：仅昨天（有完整数据的日期）可选
  const yesterday = new Date()
  yesterday.setDate(yesterday.getDate() - 1)
  // 比较年月日
  return (
    time.getFullYear() !== yesterday.getFullYear() ||
    time.getMonth() !== yesterday.getMonth() ||
    time.getDate() !== yesterday.getDate()
  )
}

function onDateChange(val: string | null) {
  const v = val || ''
  selectedDate.value = v
  emit('update:modelValue', v)
  emit('change', v)
}

function clearDate() {
  selectedDate.value = ''
  emit('update:modelValue', '')
  emit('change', '')
}
</script>

<style scoped>
.review-date-picker {
  display: flex;
  align-items: center;
  gap: 8px;
}
.review-tag {
  font-size: 12px;
}
.downgrade-tag {
  font-size: 12px;
  white-space: nowrap;
}
</style>
