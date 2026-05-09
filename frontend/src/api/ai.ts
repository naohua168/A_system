import request from './request'
import type { AIRequest, AIResponse, AIStatus } from '@/types'

/** AI 对话 */
export function chatAI(data: AIRequest): Promise<AIResponse> {
  return request.post('/ai/chat', data)
}

/** AI 服务状态 */
export function getAIStatus(): Promise<AIStatus> {
  return request.get('/ai/status')
}
