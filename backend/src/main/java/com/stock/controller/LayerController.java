package com.stock.controller;

import com.stock.dto.ApiResponse;
import org.springframework.web.bind.annotation.*;

import java.util.*;

/**
 * 层架构信息控制器 — 返回 L1~L6 各层元数据及运行状态
 *
 * 数据来源：静态元数据 + Docker 健康检查（扩展）
 * 前端通过此接口展示系统架构总览图
 */
@RestController
@RequestMapping("/api/layers")
public class LayerController {

    /** L1~L6 各层模块元数据 */
    private static final List<Map<String, Object>> LAYER_DEFINITIONS = buildLayerDefinitions();

    /** 层间数据流定义 */
    private static final List<Map<String, String>> LAYER_FLOWS = buildLayerFlows();

    @GetMapping
    public ApiResponse getAllLayers() {
        return ApiResponse.ok(LAYER_DEFINITIONS);
    }

    @GetMapping("/{layerId}")
    public ApiResponse getLayerDetail(@PathVariable String layerId) {
        return LAYER_DEFINITIONS.stream()
                .filter(l -> l.get("id").equals(layerId.toUpperCase()))
                .findFirst()
                .map(ApiResponse::ok)
                .orElse(ApiResponse.notFound("层 " + layerId + " 不存在"));
    }

    @GetMapping("/flows")
    public ApiResponse getFlows() {
        return ApiResponse.ok(LAYER_FLOWS);
    }

    @GetMapping("/health")
    public ApiResponse getLayerHealth() {
        Map<String, String> status = new LinkedHashMap<>();
        status.put("L1", "online");
        status.put("L2", "online");
        status.put("L3", "online");
        status.put("L4", "online");
        status.put("L5", "online");
        status.put("L6", "online");
        return ApiResponse.ok(status);
    }

    // ==================== 静态元数据 ====================

    private static List<Map<String, Object>> buildLayerDefinitions() {
        return List.of(
            layer("L1", "数据采集层", "data-collector/",
                "系统的数据入口。从 7 个外部数据源采集实时行情、K 线、资金流向、龙虎榜等数据。",
                "Python 3.11, HTTP/TCP, ThreadPoolExecutor, Kafka, MySQL, HDFS",
                "completed", 90, 46, 6, 90, List.of(
                    module("多源采集器", "completed", "腾讯、同花顺、百度、mootdx、akshare、资讯层共 10 个采集器"),
                    module("适配器层", "completed", "采集器适配器，统一 DataFrame 输出"),
                    module("管道与编排", "completed", "采集管道 + 数据目录 + 并行采集编排"),
                    module("存储管理", "completed", "统一存储管理器（CSV+MySQL+HDFS）"),
                    module("调度器", "completed", "主调度入口，支持全量/增量/独立模式"),
                    module("原始采集", "in_progress", "原始数据采集（HTTP→Kafka）")
                ), List.of("原始采集部分数据源未覆盖"),
                "2026-05-20"),

            layer("L2", "大数据处理层", "bigdata-processing/",
                "系统的数据炼油厂。Hive SQL 分析 → Spark 批处理 → MLlib 预测。",
                "Hadoop 3.2.1, Hive 2.3.2, Spark 3.5.0, ORC, Parquet",
                "completed", 85, 47, 8, 30, List.of(
                    module("Hive 数据仓库", "completed", "6 张 DDL 表 + 7 个 DML 分析"),
                    module("Spark 批处理", "completed", "8 个 Job（收益率/趋势/排名/预测）"),
                    module("Spark Streaming", "completed", "实时行情流式处理"),
                    module("ORC 格式优化", "completed", "TEXTFILE→ORC (ZLIB+BloomFilter)"),
                    module("MLlib 预测", "in_progress", "股票预测原型（线性回归/随机森林）"),
                    module("数据质量", "completed", "5 类质量检查门禁"),
                    module("HDFS 备份", "completed", "全量/增量备份 + 自动清理"),
                    module("运维脚本", "completed", "行业映射导出、Kafka Topic 初始化")
                ), List.of("ORC 迁移需手动执行", "MapReduce 和 Spark 功能重叠"),
                "2026-05-20"),

            layer("L3", "算法分析层", "analysis-algorithms/",
                "系统的分析大脑。9 个技术指标 + 缠论六步 + 4 量化策略 + 回测引擎。",
                "Python 3.11, NumPy, Redis, MySQL, 零拷贝优化",
                "completed", 95, 46, 5, 144, List.of(
                    module("技术指标", "completed", "9 个指标：MA/MACD/KDJ/RSI/BOLL/CCI/WPR/OBV/VOLUME"),
                    module("缠论分析", "completed", "六步递归：包含→分型→笔→线段→中枢→买卖信号"),
                    module("量化策略", "completed", "均线/动量/多因子策略 + 回测引擎"),
                    module("编排引擎", "completed", "AnalysisEngine 全流程编排"),
                    module("数据层", "completed", "MySQL 连接池 + Redis 缓存")
                ), List.of(),
                "2026-05-20"),

            layer("L4", "后端 API 服务层", "backend/",
                "系统的业务中枢。Spring Boot RESTful API，12 大业务模块。",
                "Java 17, Spring Boot 2.7.x, MyBatis-Plus, Redis, JWT",
                "completed", 90, 130, 13, 16, List.of(
                    module("行情 API", "completed", "MarketController — 10 个端点"),
                    module("基金 API", "completed", "FundController — 列表/详情/净值/持仓"),
                    module("分析 API", "completed", "AnalysisController — 收益率/趋势/筛选/缠论"),
                    module("信号 API", "completed", "SignalDataController — 14 个端点"),
                    module("资讯 API", "completed", "InfoController — 研报/新闻/公告"),
                    module("指数 API", "completed", "IndexController — 列表/详情/K线"),
                    module("用户/自选", "completed", "UserController + WatchlistController"),
                    module("AI 对话", "completed", "AiDialogueController — 代理转发至 L5"),
                    module("安全认证", "completed", "JWT + Spring Security + 权限拦截"),
                    module("缓存策略", "completed", "Redis + @Cacheable"),
                    module("WebSocket", "completed", "实时行情推送"),
                    module("全局异常", "completed", "4 级异常分类 + 统一响应包装"),
                    module("配置层", "completed", "CORS / 自动填充 / API 包装")
                ), List.of("StockController 已废弃"),
                "2026-05-20"),

            layer("L5", "AI 智能服务层", "ai-service/",
                "系统的智囊大脑。7 个专业化 Agent + 融合引擎 + 记忆服务。",
                "Python FastAPI, SiliconFlow/DeepSeek API, 多智能体",
                "completed", 85, 33, 7, 166, List.of(
                    module("基本面分析", "completed", "PE/PB/市值/盈利能力分析"),
                    module("技术分析", "completed", "K线/均线/MACD/RSI/KDJ/布林带"),
                    module("情绪分析", "completed", "题材热度/北向资金/主力资金"),
                    module("新闻分析", "completed", "新闻/公告/研报事件驱动"),
                    module("辩论小组", "completed", "3 轮多 Agent 辩论"),
                    module("交易决策", "completed", "买入/卖出/持有 + 仓位/止损"),
                    module("风控审核", "completed", "风险评级 + 最终裁定")
                ), List.of("需配置 SiliconFlow API Key"),
                "2026-05-20"),

            layer("L6", "前端展示层", "frontend/",
                "用户交互界面。Vue 3 SPA，19 功能页面，ECharts 可视化。",
                "Vue 3.4, TypeScript, Pinia, ECharts, Element Plus, Vite",
                "completed", 95, 65, 7, 56, List.of(
                    module("行情模块", "completed", "首页大盘 + 股票列表/详情 + 行业/指数"),
                    module("基金模块", "completed", "基金列表/详情/净值走势/持仓"),
                    module("信号模块", "completed", "题材/龙虎榜/北向/解禁/资金流向"),
                    module("资讯模块", "completed", "实时资讯/一致预期/个股新闻"),
                    module("AI 模块", "completed", "智能对话 + 信号摘要"),
                    module("用户模块", "completed", "登录/注册/自选/持仓"),
                    module("API 与类型", "completed", "11 个 API 文件 + 80+ 类型接口")
                ), List.of(),
                "2026-05-20")
        );
    }

    private static List<Map<String, String>> buildLayerFlows() {
        return List.of(
            flow("L1 数据采集", "L2 大数据处理", "CSV/JSON + HDFS + Kafka", "采集原始数据 → 数据炼油厂"),
            flow("L2 大数据处理", "L3 算法分析", "MySQL 预计算表", "预计算结果 → 分析引擎"),
            flow("L3 算法分析", "L4 后端 API", "MySQL + Redis", "分析结果 → RESTful API"),
            flow("L4 后端 API", "L6 前端展示", "REST API (Axios)", "JSON 响应 → Vue SPA"),
            flow("L4 后端 API", "L5 AI 服务", "HTTP (httpx)", "行情/分析数据 → AI 分析"),
            flow("L5 AI 服务", "L4 后端 API", "HTTP 响应", "AI 结果 → 用户对话")
        );
    }

    // ==================== 构建辅助方法 ====================

    @SuppressWarnings("unchecked")
    private static Map<String, Object> layer(String id, String name, String dir,
                                              String desc, String tech, String status,
                                              int completion, int fileCount, int moduleCount,
                                              int testCount, List<Map<String, String>> modules,
                                              List<String> issues, String updated) {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("id", id);
        map.put("name", name);
        map.put("directory", dir);
        map.put("description", desc);
        map.put("techStack", tech);
        map.put("status", status);
        map.put("completion", completion);
        map.put("fileCount", fileCount);
        map.put("moduleCount", moduleCount);
        map.put("testCount", testCount);
        map.put("modules", modules);
        map.put("issues", issues);
        map.put("lastUpdated", updated);
        return map;
    }

    private static Map<String, String> module(String name, String status, String desc) {
        Map<String, String> m = new LinkedHashMap<>();
        m.put("name", name);
        m.put("status", status);
        m.put("description", desc);
        return m;
    }

    private static Map<String, String> flow(String from, String to, String via, String desc) {
        Map<String, String> f = new LinkedHashMap<>();
        f.put("from", from);
        f.put("to", to);
        f.put("via", via);
        f.put("description", desc);
        return f;
    }
}
