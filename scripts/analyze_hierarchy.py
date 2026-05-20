#!/usr/bin/env python3
"""
项目层级结构完成详情分析脚本
项目：L1~L6 六层架构（基金股票智能分析系统 A_system）
用途：提取并计算每个层级的完成进度、已完成/未完成项数量，生成结构化数据输出
"""

import json
import sys
from typing import TypedDict


class ModuleInfo(TypedDict):
    name: str
    status: str  # 'completed' | 'in_progress' | 'blocked' | 'pending'
    description: str


class LayerInfo(TypedDict):
    id: str
    name: str
    directory: str
    completion: int
    fileCount: int
    moduleCount: int
    testCount: int
    modules: list[ModuleInfo]
    issues: list[str]
    status: str


# ── L1~L6 完整数据（来源于 frontend/src/api/layer.ts 及 docs/project-structure.md）──

LAYERS: list[LayerInfo] = [
    {
        "id": "L1",
        "name": "数据采集层",
        "directory": "data-collector/",
        "completion": 100,
        "fileCount": 40,
        "moduleCount": 6,
        "testCount": 90,
        "status": "completed",
        "modules": [
            {"name": "多源采集器", "status": "completed",
             "description": "腾讯、同花顺、百度、mootdx、akshare、资讯层共 9 个采集器"},
            {"name": "适配器层", "status": "completed",
             "description": "采集器适配器，统一 DataFrame 输出"},
            {"name": "管道与编排", "status": "completed",
             "description": "采集管道 + 数据目录注册中心 + 并行采集编排"},
            {"name": "存储管理", "status": "completed",
             "description": "统一存储管理器（CSV + MySQL + HDFS）"},
            {"name": "调度器", "status": "completed",
             "description": "主调度入口，支持全量/增量/独立采集模式"},
            {"name": "原始采集", "status": "completed",
             "description": "8 个原始数据生产者（Tencent/Mootdx/ThsHot/Northbound/Baidu/Akshare/Info/SinaKline）+ 增强调度器"},
        ],
        "issues": [],
    },
    {
        "id": "L2",
        "name": "大数据处理层",
        "directory": "bigdata-processing/",
        "completion": 95,
        "fileCount": 48,
        "moduleCount": 8,
        "testCount": 13,
        "status": "completed",
        "modules": [
            {"name": "Hive 数据仓库", "status": "completed",
             "description": "6 张 DDL 表 + 7 个 DML 分析 + 5 个 UDF"},
            {"name": "Spark 批处理", "status": "completed",
             "description": "8 个 Job（年/月收益率、均线趋势、相关性、行业排行、筛选、趋势判断、预测）"},
            {"name": "Spark Streaming", "status": "completed",
             "description": "实时行情流式处理（DataFrame API 重构版）"},
            {"name": "MapReduce 计算", "status": "completed",
             "description": "5 个作业（行业统计 / 月/年收益 / 技术指标 / 成交量分析）"},
            {"name": "批处理管道", "status": "completed",
             "description": "调度器支持 daily/incremental/rebuild/dry-run/parallel 模式"},
            {"name": "ORC 格式优化", "status": "completed",
             "description": "TEXTFILE → ORC (ZLIB + Bloom Filter)，查询性能 10x+"},
            {"name": "HDFS 备份", "status": "completed",
             "description": "全量/增量备份 + 自动清理"},
            {"name": "运维脚本", "status": "completed",
             "description": "行业映射导出、Kafka Topic 初始化"},
        ],
        "issues": ["ORC 迁移已集成到 start-all.sh（--migrate-orc 参数一键执行）"],
    },
    {
        "id": "L3",
        "name": "算法分析层",
        "directory": "analysis-algorithms/",
        "completion": 98,
        "fileCount": 45,
        "moduleCount": 5,
        "testCount": 45,
        "status": "completed",
        "modules": [
            {"name": "技术指标", "status": "completed",
             "description": "9 个指标：MA/MACD/KDJ/RSI/布林带/CCI/WR/OBV/成交量均线"},
            {"name": "缠论分析", "status": "completed",
             "description": "6 步递归：K线包含→分型→笔→线段→中枢→买卖信号"},
            {"name": "量化策略", "status": "completed",
             "description": "均线 / 动量 / 多因子 策略 + 回测引擎"},
            {"name": "编排引擎", "status": "completed",
             "description": "AnalysisEngine 全流程编排"},
            {"name": "数据层", "status": "completed",
             "description": "MySQL 连接池 + Redis 缓存 + 并行信号读取"},
        ],
        "issues": [],
    },
    {
        "id": "L4",
        "name": "后端 API 服务层",
        "directory": "backend/",
        "completion": 96,
        "fileCount": 129,
        "moduleCount": 13,
        "testCount": 51,
        "status": "completed",
        "modules": [
            {"name": "行情 API", "status": "completed",
             "description": "MarketController — 11 个端点"},
            {"name": "基金 API", "status": "completed",
             "description": "FundController — 列表/详情/净值/持仓"},
            {"name": "分析 API", "status": "completed",
             "description": "AnalysisController — 收益率/趋势/筛选/相关性/排行/缠论"},
            {"name": "信号 API", "status": "completed",
             "description": "SignalDataController — 24 个端点"},
            {"name": "资讯 API", "status": "completed",
             "description": "InfoController — 研报/一致预期/新闻/快讯/公告/PDF"},
            {"name": "指数 API", "status": "completed",
             "description": "IndexController — 列表/详情/K线"},
            {"name": "用户/自选", "status": "completed",
             "description": "UserController + WatchlistController"},
            {"name": "AI 对话", "status": "completed",
             "description": "AiDialogueController — 代理转发至 L5 AI 服务"},
            {"name": "安全认证", "status": "completed",
             "description": "JWT + Spring Security + 权限拦截"},
            {"name": "缓存策略", "status": "completed",
             "description": "Redis TTL=30min + @Cacheable 高频接口加速"},
            {"name": "WebSocket", "status": "completed",
             "description": "实时行情推送"},
            {"name": "全局异常处理", "status": "completed",
             "description": "4 级异常分类 + SLF4J 日志"},
            {"name": "配置层", "status": "completed",
             "description": "CORS / 自动填充 / 通用Bean / API 响应包装"},
        ],
        "issues": [],
    },
    {
        "id": "L5",
        "name": "AI 智能服务层",
        "directory": "ai-service/",
        "completion": 100,
        "fileCount": 29,
        "moduleCount": 7,
        "testCount": 163,
        "status": "completed",
        "modules": [
            {"name": "基本面分析 Agent", "status": "completed",
             "description": "PE/PB/市值/盈利能力分析 + mock 降级"},
            {"name": "技术分析 Agent", "status": "completed",
             "description": "K线/均线/MACD/RSI/KDJ/布林带分析 + mock 降级"},
            {"name": "情绪分析 Agent", "status": "completed",
             "description": "题材热度/北向资金/主力资金 + mock 降级"},
            {"name": "新闻分析 Agent", "status": "completed",
             "description": "新闻/公告/研报事件驱动 + mock 降级"},
            {"name": "辩论小组 Agent", "status": "completed",
             "description": "3 轮多 Agent 辩论"},
            {"name": "交易决策 Agent", "status": "completed",
             "description": "买入/卖出/持有 + 仓位/止损/动态置信度"},
            {"name": "风控审核 Agent", "status": "completed",
             "description": "风险评级 + 调整建议 + 最终裁定"},
        ],
        "issues": [],
    },
    {
        "id": "L6",
        "name": "前端展示层",
        "directory": "frontend/",
        "completion": 98,
        "fileCount": 56,
        "moduleCount": 7,
        "testCount": 36,
        "status": "completed",
        "modules": [
            {"name": "行情模块", "status": "completed",
             "description": "首页大盘 + 股票列表/详情 + 行业详情 + 指数详情"},
            {"name": "基金模块", "status": "completed",
             "description": "基金列表/详情/净值走势/持仓明细"},
            {"name": "信号模块", "status": "completed",
             "description": "题材/龙虎榜/北向/解禁/资金流向/行业对比"},
            {"name": "资讯模块", "status": "completed",
             "description": "实时资讯/一致预期/个股新闻"},
            {"name": "AI 模块", "status": "completed",
             "description": "AI 智能对话 + AI 信号摘要"},
            {"name": "用户模块", "status": "completed",
             "description": "登录/注册/自选/持仓管理"},
            {"name": "API 与类型", "status": "completed",
             "description": "9 个 API 文件 + 类型定义（55+ 接口）"},
        ],
        "issues": [],
    },
]


def compute_layer_stats(layer: LayerInfo) -> dict:
    """计算单个层的详细统计"""
    modules = layer["modules"]
    total_modules = len(modules)
    done = sum(1 for m in modules if m["status"] == "completed")
    in_progress = sum(1 for m in modules if m["status"] == "in_progress")
    blocked = sum(1 for m in modules if m["status"] == "blocked")
    pending = sum(1 for m in modules if m["status"] == "pending")
    incomplete = total_modules - done

    return {
        "总模块数": total_modules,
        "已完成模块": done,
        "未完成模块": incomplete,
        "开发中": in_progress,
        "阻塞": blocked,
        "待开始": pending,
        "模块完成率": round(done / total_modules * 100, 1) if total_modules else 0,
        "文件数": layer["fileCount"],
        "测试用例数": layer["testCount"],
    }


def build_hierarchy_report() -> dict:
    """构建完整的层级结构完成详情报告"""
    total_files = 0
    total_tests = 0
    total_modules_all = 0
    total_done_modules = 0
    total_incomplete_modules = 0
    total_issues = 0

    layers_report = []
    for layer in LAYERS:
        stats = compute_layer_stats(layer)

        sub_modules = []
        for m in layer["modules"]:
            sub_modules.append({
                "模块名称": m["name"],
                "状态": m["status"],
                "状态描述": {
                    "completed": "已完成",
                    "in_progress": "开发中",
                    "blocked": "阻塞",
                    "pending": "待开始",
                }.get(m["status"], m["status"]),
                "说明": m["description"],
            })

        layer_item = {
            "层级ID": layer["id"],
            "层级名称": layer["name"],
            "目录": layer["directory"],
            "整体状态": layer["status"],
            "完成百分比": layer["completion"],
            "统计": stats,
            "子模块列表": sub_modules,
            "待解决项": layer["issues"],
            "待解决项数": len(layer["issues"]),
            "最后更新": "2026-05-20",
        }
        layers_report.append(layer_item)

        total_files += layer["fileCount"]
        total_tests += layer["testCount"]
        total_modules_all += stats["总模块数"]
        total_done_modules += stats["已完成模块"]
        total_incomplete_modules += stats["未完成模块"]
        total_issues += len(layer["issues"])

    overall_completion = round(
        sum(l["completion"] for l in LAYERS) / len(LAYERS), 1
    )

    report = {
        "项目名称": "基金股票智能分析系统 (A_system)",
        "项目标识": "L1~L6",
        "报告生成时间": "2026-05-20 10:05",
        "总体统计": {
            "总层数": len(LAYERS),
            "总完成度（平均）": f"{overall_completion}%",
            "总文件数": total_files,
            "总模块数": total_modules_all,
            "总测试用例数": total_tests,
            "总待解决项数": total_issues,
        },
        "全局模块统计": {
            "已完成模块": total_done_modules,
            "未完成模块": total_incomplete_modules,
            "模块总体完成率": f"{round(total_done_modules / total_modules_all * 100, 1)}%"
            if total_modules_all
            else "N/A",
        },
        "层级详情": layers_report,
    }
    return report


def print_report(report: dict):
    """美观打印结构化报告到控制台"""
    sep = "=" * 78
    sub_sep = "-" * 78

    print(sep)
    print(f"  项目层级结构完成详情分析报告")
    print(f"  {report['项目名称']}")
    print(f"  {report['项目标识']}")
    print(f"  生成时间: {report['报告生成时间']}")
    print(sep)
    print()

    # 总体统计
    o = report["总体统计"]
    g = report["全局模块统计"]
    print("  【总体统计】")
    print(f"    总层数:           {o['总层数']}")
    print(f"    总完成度（平均）: {o['总完成度（平均）']}")
    print(f"    总文件数:         {o['总文件数']}")
    print(f"    总模块数:         {o['总模块数']}")
    print(f"    总测试用例数:     {o['总测试用例数']}")
    print(f"    总待解决项数:     {o['总待解决项数']}")
    print(f"    已完成模块:       {g['已完成模块']}")
    print(f"    未完成模块:       {g['未完成模块']}")
    print(f"    模块总体完成率:   {g['模块总体完成率']}")
    print()

    # 各层详情
    for idx, layer in enumerate(report["层级详情"]):
        if idx > 0:
            print(sub_sep)
        s = layer["统计"]
        print(f"\n  >> {layer['层级ID']}: {layer['层级名称']}  [{layer['整体状态']}]")
        print(f"     目录: {layer['目录']}")
        print(f"     完成百分比: {layer['完成百分比']}%")
        print(f"     ┌──────────────┬───────┐")
        print(f"     │ 模块总数     │ {s['总模块数']:>3}   │")
        print(f"     │ 已完成模块   │ {s['已完成模块']:>3}   │")
        print(f"     │ 未完成模块   │ {s['未完成模块']:>3}   │")
        print(f"     │ 开发中       │ {s['开发中']:>3}   │")
        print(f"     │ 阻塞         │ {s['阻塞']:>3}   │")
        print(f"     │ 待开始       │ {s['待开始']:>3}   │")
        print(f"     │ 模块完成率   │ {s['模块完成率']:>3}%  │")
        print(f"     │ 文件数       │ {s['文件数']:>3}   │")
        print(f"     │ 测试用例     │ {s['测试用例数']:>3}   │")
        print(f"     └──────────────┴───────┘")

        # 子模块
        print(f"     子模块列表 ({len(layer['子模块列表'])} 个):")
        for m in layer["子模块列表"]:
            icon = {"已完成": "✅", "开发中": "🔄", "阻塞": "❌", "待开始": "⏳"}.get(
                m["状态描述"], "❓"
            )
            print(f"       {icon} {m['模块名称']} ({m['状态描述']})")

        # 待解决项
        if layer["待解决项"]:
            print(f"     待解决项 ({layer['待解决项数']} 项):")
            for issue in layer["待解决项"]:
                print(f"       ⚠️  {issue}")
        else:
            print(f"     待解决项: 无")
        print()

    print(sep)
    print(f"  报告完毕 — 共 {len(report['层级详情'])} 个层级, "
          f"{report['全局模块统计']['已完成模块']}/{report['全局模块统计']['未完成模块'] + report['全局模块统计']['已完成模块']} 模块完成")
    print(sep)


def export_json(report: dict, filepath: str = None):
    """导出报告为 JSON 文件"""
    if filepath is None:
        filepath = "hierarchy_analysis_result.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 JSON 报告已导出到: {filepath}")


def main():
    print("正在分析项目层级结构完成详情...\n")
    report = build_hierarchy_report()
    print_report(report)
    export_json(report)
    print("\n✅ 分析完成！")


if __name__ == "__main__":
    main()
