/**
 * ECharts 按需引入 — 仅注册项目实际使用到的组件
 * 大幅减小打包体积（从全量 ~1MB 降至 ~300KB）
 *
 * 使用方式：其他文件中 import echarts from '@/utils/echarts' 替代 import * as echarts from 'echarts'
 */
import { use } from 'echarts/core'
import * as echartsCore from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import {
  LineChart,
  BarChart,
  PieChart,
  CandlestickChart,
  TreemapChart,
  ScatterChart,
  HeatmapChart,
} from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  ToolboxComponent,
  MarkLineComponent,
  VisualMapComponent,
  CalendarComponent,
} from 'echarts/components'

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  PieChart,
  CandlestickChart,
  TreemapChart,
  ScatterChart,
  HeatmapChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  ToolboxComponent,
  MarkLineComponent,
  VisualMapComponent,
  CalendarComponent,
])

// 默认导出 echarts 核心对象（包含 init / dispose / registerMap 等 API），
// 同时保留核心的命名导出以便需要时灵活导入
export default echartsCore
export * from 'echarts/core'
