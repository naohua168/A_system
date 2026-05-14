"""多智能体模拟降级 — 无需API Key也能运行"""

SIMULATION_TEMPLATES = {
    "fundamentals_analyst": {
        "bullish": (
            "**基本面分析 - {stock_code}**\n\n"
            "PE={pe}，处于行业中等偏低水平，估值合理。\n"
            "PB={pb}，市净率安全。\n"
            "市值{market_cap}亿，{cap_type}股。\n\n"
            "结论：基本面稳健，建议关注。"
        ),
        "bearish": (
            "**基本面分析 - {stock_code}**\n\n"
            "PE={pe}，高于行业平均，估值偏贵。\n"
            "盈利能力需进一步观察。\n\n"
            "结论：估值偏高，建议暂缓介入。"
        ),
    },
    "technical_analyst": {
        "bullish": (
            "**技术分析 - {stock_code}**\n\n"
            "均线：MA5({ma5})>MA10({ma10})>MA20({ma20})，多头排列。\n"
            "MACD：DIF({dif})上穿DEA({dea})，金叉信号。\n"
            "RSI：{rsi}，处于强势区间。\n\n"
            "结论：技术面偏多，短期有机会。"
        ),
        "bearish": (
            "**技术分析 - {stock_code}**\n\n"
            "均线：MA5({ma5})<MA10({ma10})，死叉信号。\n"
            "MACD：DIF({dif})下穿DEA({dea})，动能减弱。\n"
            "RSI：{rsi}，超买后回落。\n\n"
            "结论：技术面转弱，注意回调风险。"
        ),
    },
    "sentiment_analyst": {
        "bullish": (
            "**情绪分析 - {stock_code}**\n\n"
            "题材热度：{hot_count}只相关强势股\n"
            "北向资金：净流入{foreign_inflow}亿\n"
            "主力资金：{main_flow}亿\n\n"
            "结论：资金面偏多，情绪积极。"
        ),
        "bearish": (
            "**情绪分析 - {stock_code}**\n\n"
            "题材热度下降，资金流出\n"
            "北向资金：净流出{foreign_inflow}亿\n\n"
            "结论：资金面偏空，情绪降温。"
        ),
    },
    "trader_agent": {
        "default": (
            "**交易决策**\n\n"
            "方向：{direction}\n"
            "仓位：{position}\n"
            "止损：{stop_loss}\n"
            "目标：{target}\n"
            "信心指数：{confidence}/10\n\n"
            "理由：{reason}"
        ),
    },
    "risk_manager": {
        "default": (
            "**风险评估**\n\n"
            "审核结果：{status}\n"
            "风险等级：{risk_level}\n"
            "调整：{adjustments}\n\n"
            "⚠️ 最终裁定：{final_decision}"
        ),
    },
}


class SimulationEngine:
    """模拟引擎 — 无需AI模型即可生成分析"""

    @staticmethod
    def get_simulation(agent_role: str, context: dict) -> str:
        """获取指定角色的模拟回复"""
        role_key = agent_role.lower().replace(" ", "_").replace("-", "_")
        templates = SIMULATION_TEMPLATES.get(role_key, {})

        if not templates:
            return f"[{agent_role}] 模拟模式 (API Key 未配置)"

        # 根据语境选择看多/看空模板
        sentiment = context.get("sentiment", "bullish")
        template_key = sentiment if sentiment in templates else list(templates.keys())[0]
        template = templates.get(template_key, list(templates.values())[0])

        # 填充默认值
        defaults = {
            "stock_code": "000001",
            "pe": 15, "pb": 1.5, "market_cap": 2000, "cap_type": "大盘",
            "ma5": 5.28, "ma10": 5.15, "ma20": 4.98,
            "dif": 0.15, "dea": 0.08, "rsi": 62,
            "hot_count": 5, "foreign_inflow": 3.2, "main_flow": 1.5,
            "direction": "买入", "position": "30%", "stop_loss": "-5%",
            "target": "+10%", "confidence": 7,
            "reason": "多维度分析综合结果",
            "status": "已批准", "risk_level": "中等",
            "adjustments": "仓位降低至20%", "final_decision": "谨慎参与",
        }
        defaults.update(context)
        return template.format(**defaults)

    @staticmethod
    def analyze_with_simulation(agent_name: str, stock_code: str) -> dict:
        """模拟完整的Agent分析流程"""
        return {
            "agent": agent_name,
            "stock_code": stock_code,
            "mode": "simulation",
            "content": SimulationEngine.get_simulation(agent_name, {"stock_code": stock_code}),
        }
