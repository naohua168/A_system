/**
 * 层架构详情 — API 接口
 * 优先从后端获取数据，不可用时降级到静态 Mock
 */
import type { LayerInfo, LayerFlow } from '@/types'
import request from './request'

/** 后端基础路径 */
const BASE = '/layers'

/**
 * 获取全部层列表
 */
export async function getLayerList(signal?: AbortSignal): Promise<LayerInfo[]> {
  try {
    const resp = await request.get(BASE, { signal })
    return resp.data as LayerInfo[]
  } catch {
    return getFallbackLayers()
  }
}

/**
 * 获取指定层的详细信息
 */
export async function getLayerDetail(
  layerId: string,
  signal?: AbortSignal,
): Promise<LayerInfo | null> {
  try {
    const resp = await request.get(`${BASE}/${layerId}`, { signal })
    return resp.data as LayerInfo
  } catch {
    const layers = getFallbackLayers()
    return layers.find((l) => l.id === layerId) ?? null
  }
}

/**
 * 获取层间数据流
 */
export async function getLayerFlows(signal?: AbortSignal): Promise<LayerFlow[]> {
  try {
    const resp = await request.get(`${BASE}/flows`, { signal })
    return resp.data as LayerFlow[]
  } catch {
    return getFallbackFlows()
  }
}

/**
 * 按关键字搜索层
 */
export async function searchLayers(
  keyword: string,
  signal?: AbortSignal,
): Promise<LayerInfo[]> {
  const kw = keyword.toLowerCase()
  const layers = await getLayerList(signal)
  return layers.filter(
    (l) =>
      l.name.includes(kw) ||
      l.id.toLowerCase().includes(kw) ||
      l.directory.toLowerCase().includes(kw) ||
      l.techStack.toLowerCase().includes(kw) ||
      l.modules.some((m) => m.name.includes(kw)),
  )
}

// ==================== 降级数据（后端不可用时使用） ====================

function getFallbackLayers(): LayerInfo[] {
  return [
    {
      id: 'L1', name: '数据采集层', directory: 'data-collector/',
      description: '系统的数据入口。从 7 个外部数据源采集实时行情、K 线、资金流向等数据。',
      techStack: 'Python 3.11, HTTP/TCP, ThreadPoolExecutor, Kafka, MySQL, HDFS',
      status: 'completed', completion: 90, fileCount: 46, moduleCount: 6, testCount: 90,
      modules: [
        { name: '多源采集器', status: 'completed', description: '10 个采集器覆盖 7 数据源' },
        { name: '管道与编排', status: 'completed', description: '并行采集编排 + 数据目录' },
      ],
      issues: ['原始采集部分未覆盖'], lastUpdated: '2026-05-20',
    },
    {
      id: 'L2', name: '大数据处理层', directory: 'bigdata-processing/',
      description: 'Hive SQL 分析 → Spark 批处理 → MLlib 预测。',
      techStack: 'Hadoop 3.2.1, Hive 2.3.2, Spark 3.5.0, ORC, Parquet',
      status: 'completed', completion: 85, fileCount: 47, moduleCount: 8, testCount: 30,
      modules: [
        { name: 'Spark 批处理', status: 'completed', description: '8 个 Job' },
        { name: 'MLlib 预测', status: 'in_progress', description: '预测原型' },
      ],
      issues: ['ORC 迁移需手动执行'], lastUpdated: '2026-05-20',
    },
    {
      id: 'L3', name: '算法分析层', directory: 'analysis-algorithms/',
      description: '9 个技术指标 + 缠论六步 + 4 量化策略 + 回测引擎。',
      techStack: 'Python 3.11, NumPy, Redis, MySQL',
      status: 'completed', completion: 95, fileCount: 46, moduleCount: 5, testCount: 144,
      modules: [
        { name: '技术指标', status: 'completed', description: '9 个指标' },
        { name: '缠论分析', status: 'completed', description: '六步递归' },
      ],
      issues: [], lastUpdated: '2026-05-20',
    },
    {
      id: 'L4', name: '后端 API 服务层', directory: 'backend/',
      description: 'Spring Boot RESTful API，12 大业务模块。',
      techStack: 'Java 17, Spring Boot 3.x, MyBatis-Plus, Redis, JWT',
      status: 'completed', completion: 90, fileCount: 130, moduleCount: 13, testCount: 16,
      modules: [
        { name: '行情 API', status: 'completed', description: '10 个端点' },
        { name: '安全认证', status: 'completed', description: 'JWT + RBAC' },
      ],
      issues: ['StockController 已废弃'], lastUpdated: '2026-05-20',
    },
    {
      id: 'L5', name: 'AI 智能服务层', directory: 'ai-service/',
      description: '7 个专业化 Agent + 融合引擎 + 记忆服务。',
      techStack: 'Python FastAPI, SiliconFlow/DeepSeek, 多智能体',
      status: 'completed', completion: 85, fileCount: 33, moduleCount: 7, testCount: 166,
      modules: [
        { name: '技术分析', status: 'completed', description: 'K线/指标分析' },
        { name: '辩论小组', status: 'completed', description: '3 轮辩论' },
      ],
      issues: ['需配置 SiliconFlow API Key'], lastUpdated: '2026-05-20',
    },
    {
      id: 'L6', name: '前端展示层', directory: 'frontend/',
      description: 'Vue 3 SPA，19 功能页面，ECharts 可视化。',
      techStack: 'Vue 3.4, TypeScript, Pinia, ECharts, Element Plus, Vite',
      status: 'completed', completion: 95, fileCount: 65, moduleCount: 7, testCount: 56,
      modules: [
        { name: '行情模块', status: 'completed', description: '大盘/列表/详情' },
        { name: 'AI 模块', status: 'completed', description: '智能对话' },
      ],
      issues: [], lastUpdated: '2026-05-20',
    },
  ]
}

function getFallbackFlows(): LayerFlow[] {
  return [
    { from: 'L1 数据采集', to: 'L2 大数据处理', via: 'HDFS + Kafka', description: '采集→加工' },
    { from: 'L2 大数据处理', to: 'L3 算法分析', via: 'MySQL', description: '预计算→分析' },
    { from: 'L3 算法分析', to: 'L4 后端 API', via: 'MySQL + Redis', description: '结果→API' },
    { from: 'L4 后端 API', to: 'L6 前端展示', via: 'REST API', description: 'JSON→Vue' },
    { from: 'L4 后端 API', to: 'L5 AI 服务', via: 'HTTP', description: '数据→AI' },
    { from: 'L5 AI 服务', to: 'L4 后端 API', via: 'HTTP', description: 'AI→对话' },
  ]
}
