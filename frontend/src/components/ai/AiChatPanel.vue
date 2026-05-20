<template>
  <div class="ai-chat-panel" :class="{ collapsed }">
    <div class="header" @click="collapsed = !collapsed">
      <el-icon :size="18"><ChatLineSquare /></el-icon>
      <span>AI 分析</span>
      <el-button size="small" :icon="collapsed ? 'ArrowUp' : 'ArrowDown'" circle />
    </div>
    <div v-show="!collapsed" class="body">
      <div class="messages" ref="msgRef">
        <div v-for="(msg, i) in messages" :key="i" :class="['msg', msg.role]">
          <div class="bubble" v-html="renderContent(msg.content)" />
        </div>
        <div v-if="loading" class="msg assistant">
          <div class="bubble typing">分析中...</div>
        </div>
      </div>
      <div class="input-area">
        <el-input v-model="input" type="textarea" :rows="2" placeholder="输入问题..." @keydown.enter.prevent="send" />
        <el-button type="primary" @click="send" :loading="loading">发送</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { ChatLineSquare } from '@element-plus/icons-vue'
import { chatAI } from '@/api/ai'

const props = defineProps<{ stockCode?: string }>()
const collapsed = ref(true)
const input = ref('')
const loading = ref(false)
const messages = ref<{ role: string; content: string }[]>([])
const msgRef = ref<HTMLElement>()

async function send() {
  if (!input.value.trim() || loading.value) return
  const question = input.value
  messages.value.push({ role: 'user', content: question })
  input.value = ''
  loading.value = true
  try {
    const res = await chatAI({
      message: question,
      stockCode: props.stockCode || '',
      history: messages.value.slice(0, -1),
    })
    messages.value.push({ role: 'assistant', content: res.reply })
  } catch {
    messages.value.push({ role: 'assistant', content: '抱歉，AI服务暂时不可用，请稍后重试。' })
  } finally {
    loading.value = false
    nextTick(() => msgRef.value?.scrollTo({ top: msgRef.value.scrollHeight, behavior: 'smooth' }))
  }
}

function renderContent(text: string) {
  return text.replace(/\n/g, '<br>').replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
}
</script>

<style scoped lang="scss">
.ai-chat-panel { position: fixed; bottom: 20px; right: 20px; width: 380px; z-index: 1000; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); background: #fff; overflow: hidden; }
.ai-chat-panel.collapsed .body { display: none; }
.header { display: flex; align-items: center; gap: 8px; padding: 12px 16px; background: $primary; color: #fff; cursor: pointer; font-weight: 600; }
.body { display: flex; flex-direction: column; height: 500px; }
.messages { flex: 1; overflow-y: auto; padding: 16px; }
.msg { margin-bottom: 12px; }
.msg.user { text-align: right; }
.msg .bubble { display: inline-block; max-width: 85%; padding: 10px 14px; border-radius: 12px; font-size: 14px; line-height: 1.6; text-align: left; }
.msg.user .bubble { background: $primary; color: #fff; border-bottom-right-radius: 4px; }
.msg.assistant .bubble { background: $canvas-parchment; color: $ink; border-bottom-left-radius: 4px; }
.input-area { display: flex; gap: 8px; padding: 12px; border-top: 1px solid $divider-soft; }
.input-area .el-textarea { flex: 1; }
.typing { color: $ink-muted-48 !important; }
</style>
