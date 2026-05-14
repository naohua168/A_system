<template>
  <div class="chat-view">
    <!-- 顶部标题 -->
    <div class="chat-header">
      <div class="header-left">
        <el-icon :size="28" color="var(--primary)"><ChatLineSquare /></el-icon>
        <div>
          <h3>AI 智能分析</h3>
          <span class="subtitle">基于 {{ modeLabel }}，支持股票基金智能问答</span>
        </div>
      </div>
      <div class="header-right">
        <el-popover placement="bottom-end" :width="320" trigger="click">
          <template #reference>
            <el-button :icon="InfoFilled" circle size="small" />
          </template>
          <div class="tips-content">
            <h4>提问示例</h4>
            <ul>
              <li @click="quickAsk('000001 这只股票怎么样？')">000001 这只股票怎么样？</li>
              <li @click="quickAsk('分析平安银行的缠论买卖点')">分析平安银行的缠论买卖点</li>
              <li @click="quickAsk('大盘今天走势如何？')">大盘今天走势如何？</li>
              <li @click="quickAsk('110011 基金值得定投吗？')">110011 基金值得定投吗？</li>
              <li @click="quickAsk('MACD金叉了，可以买入吗？')">MACD金叉了，可以买入吗？</li>
              <li @click="quickAsk('当前市场有什么投资建议？')">当前市场有什么投资建议？</li>
            </ul>
          </div>
        </el-popover>
        <el-button :icon="Delete" circle size="small" @click="clearChat" />
      </div>
    </div>

    <!-- 对话区域 -->
    <div class="chat-messages" ref="messagesRef">
      <div v-if="messages.length === 0" class="empty-state">
        <el-icon :size="48" color="var(--primary)" style="opacity: 0.4"><ChatLineSquare /></el-icon>
        <p>输入股票/基金代码或问题，AI 为您分析</p>
        <div class="quick-actions">
          <el-tag v-for="q in quickQuestions" :key="q" @click="quickAsk(q)" effect="plain">
            {{ q }}
          </el-tag>
        </div>
      </div>

      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        class="message-row"
        :class="msg.role"
      >
        <el-avatar
          v-if="msg.role === 'assistant'"
          :size="36"
          icon="ChatLineSquare"
          style="background: var(--primary); flex-shrink: 0"
        />
        <div class="bubble" v-html="renderedContent(msg.content)" />
        <el-avatar
          v-if="msg.role === 'user'"
          :size="36"
          style="background: #909399; flex-shrink: 0"
        >U</el-avatar>
      </div>

      <div v-if="loading" class="message-row assistant">
        <el-avatar :size="36" icon="ChatLineSquare" style="background: var(--primary); flex-shrink: 0" />
        <div class="bubble typing">
          <span class="dot">.</span><span class="dot">.</span><span class="dot">.</span>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="chat-input">
      <el-input
        v-model="inputMessage"
        type="textarea"
        :rows="2"
        placeholder="输入问题，例如：分析 000001 的技术面..."
        :disabled="loading"
        @keydown="handleKeydown"
      />
      <el-button
        type="primary"
        :icon="Promotion"
        :loading="loading"
        :disabled="!inputMessage.trim()"
        @click="sendMessage"
      >
        发送
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, computed } from 'vue'
import { ChatLineSquare, InfoFilled, Delete, Promotion } from '@element-plus/icons-vue'
import { chatAI, getAIStatus } from '@/api/ai'
import type { ChatMessage } from '@/types'

// ── 状态 ──
const messages = ref<ChatMessage[]>([])
const inputMessage = ref('')
const loading = ref(false)
const modeLabel = ref('加载中...')
const messagesRef = ref<HTMLElement | null>(null)

// 快速提问
const quickQuestions = [
  '分析 000001 的技术面',
  '缠论分析：平安银行',
  '大盘今日走势如何？',
  '当前市场投资建议',
]

// ── 初始化 ──
getAIStatus().then((res: any) => {
  modeLabel.value = res?.aiServiceUrl ? '实时模式' : '模拟模式'
}).catch(() => {
  modeLabel.value = '模拟模式'
})

// ── 发送消息 ──
async function sendMessage() {
  const text = inputMessage.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text, timestamp: Date.now() })
  inputMessage.value = ''
  loading.value = true
  scrollToBottom()

  try {
    // 提取股票代码
    const codeMatch = text.match(/(\d{6})/)
    const stockCode = codeMatch ? codeMatch[1] : ''

    const history = messages.value
      .filter(m => m.role !== 'system')
      .slice(-10)
      .map(m => ({ role: m.role, content: m.content }))

    const res = await chatAI({
      message: text,
      stockCode,
      history,
    })
    messages.value.push({ role: 'assistant', content: res.reply, timestamp: Date.now() })
  } catch {
    messages.value.push({
      role: 'assistant',
      content: '服务暂时不可用，请稍后重试。如果问题持续，请检查后端和 AI 服务是否已启动。',
      timestamp: Date.now(),
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

// ── 渲染 markdown 样式的文本 ──
function renderedContent(content: string): string {
  return content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // 标题
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/__(.+?)__/g, '<strong>$1</strong>')
    // 换行
    .replace(/\n/g, '<br>')
    // 列表
    .replace(/•/g, '&bull;')
    // 数字列表
    .replace(/(\d+)\. /g, '<br>$1. ')
}

// ── 清空 ──
function clearChat() {
  messages.value = []
}

// ── 快速提问 ──
function quickAsk(text: string) {
  inputMessage.value = text
}

// ── 回车发送 ──
function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

// ── 滚动到底部 ──
function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}
</script>

<style scoped lang="scss">
.chat-view {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 180px);
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;

    h3 {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
    }

    .subtitle {
      font-size: 12px;
      color: #909399;
    }
  }

  .header-right {
    display: flex;
    gap: 8px;
  }
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    flex: 1;
    gap: 16px;
    color: #909399;

    .quick-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: center;
      max-width: 400px;

      .el-tag {
        cursor: pointer;
        transition: all 0.2s;
        &:hover {
          transform: scale(1.05);
          border-color: var(--primary);
          color: var(--primary);
        }
      }
    }
  }

  .message-row {
    display: flex;
    gap: 12px;
    align-items: flex-start;

    &.user {
      flex-direction: row-reverse;
    }

    .bubble {
      max-width: 70%;
      padding: 12px 16px;
      border-radius: 12px;
      font-size: 14px;
      line-height: 1.6;
      word-break: break-word;

      :deep(strong) {
        color: var(--primary);
      }

      :deep(br + br) {
        display: block;
        content: '';
        margin-top: 4px;
      }
    }

    &.assistant .bubble {
      background: #f5f7fa;
      color: #303133;
      border-top-left-radius: 4px;
    }

    &.user .bubble {
      background: linear-gradient(135deg, var(--primary), #409eff);
      color: #fff;
      border-top-right-radius: 4px;
    }

    .typing {
      display: flex;
      gap: 4px;
      padding: 16px 20px;

      .dot {
        animation: blink 1.4s infinite;
        font-size: 24px;
        line-height: 0;
        color: #909399;

        &:nth-child(2) { animation-delay: 0.2s; }
        &:nth-child(3) { animation-delay: 0.4s; }
      }
    }
  }
}

.chat-input {
  display: flex;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #f0f0f0;
  background: #fafafa;
  flex-shrink: 0;

  .el-textarea {
    flex: 1;
  }

  .el-button {
    align-self: flex-end;
    height: 56px;
    width: 90px;
  }
}

.tips-content {
  h4 { margin: 0 0 8px; font-size: 14px; }
  ul {
    margin: 0;
    padding: 0;
    list-style: none;

    li {
      padding: 6px 8px;
      cursor: pointer;
      border-radius: 6px;
      font-size: 13px;
      color: #606266;
      transition: all 0.2s;

      &:hover {
        background: #f0f5ff;
        color: var(--primary);
      }
    }
  }
}

@keyframes blink {
  0%, 80%, 100% { opacity: 0; }
  40% { opacity: 1; }
}
</style>
