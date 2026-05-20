"""统一模拟引擎 — 所有 Agent 和对话的模拟降级模板集中管理"""
import re

# ============================================================
# 统一模拟模板库
# ============================================================
# 来源: 原 deepseek_client.py 的 MOCK_RESPONSES +
#         原 base_agent.py 的 _mock_reply() +
#         原 simulation.py 的 SIMULATION_TEMPLATES
# 合并时间: 2026-05-20
# ============================================================

UNIFIED_MOCK_DATA = {
    "ma5": "5.28", "ma10": "5.15", "ma20": "4.98", "ma60": "4.50",
    "dif": "0.15", "dea": "0.08", "macd": "0.07",
    "k": "72", "d": "65", "j": "86",
    "rsi": 62.8, "rsi6": 68.5, "rsi12": 62.8, "rsi24": 55.2,
    "boll_up": "16.80", "boll_mid": "5.10", "boll_low": "12.90", "mid": "5.10",
    "cci": 120.5, "wr": -25.3,
    "volume": "8,562", "volume_compare": True, "volume_diff": "15.3",
    "changePercent": 2.35,
    "resistance": "5.60元", "support": "4.80元",
    "central_low": "12.50", "central_high": "13.80",
    "target1": "14.50元", "target2": "15.80元",
    "month_ret": 3.5, "quarter_ret": 8.2, "half_ret": -2.1,
    "max_drawdown": 12.5,
    "top_holdings": "茅台、宁德时代、招商银行",
    "industry": "消费+新能源+金融",
    "conc_level": "较高",
    "volatility": 18.5, "sharpe": 1.2,
    "sh_index": "3,158.26", "sh_change": 0.68,
    "sz_index": "10,542.35", "sz_change": 1.24,
    "cy_index": "2,285.45", "cy_change": 1.86,
    "foreign_inflow": "42.5",
    "hot_sector": "AI算力、半导体",
    "cold_sector": "地产、消费",
    "stock_code": "000001", "stock_name": "示例科技",
    "pe": 25.6, "pb": 3.2, "market_cap": 2000, "cap_type": "大盘",
    "total_market_cap": "85.6亿", "float_market_cap": "62.3亿",
    "hot_count": 8, "main_flow": 1.5,
    "direction": "买入", "position": "30%仓位",
    "stop_loss": "-5%", "target": "+10%",
    "confidence": 7, "reason": "多维度分析综合结果",
    "status": "已批准", "risk_level": "中等",
    "adjustments": "仓位适当降低",
    "final_decision": "谨慎参与",
    "query": "请分析000001",
}


# ── 对话/通用回复模板 ──
DIALOG_TEMPLATES = {
    "trend_bullish": (
        "**技术面看涨信号**：\n\n"
        "1. **均线系统**：MA5({ma5}) > MA10({ma10}) > MA20({ma20})，呈多头排列，短期趋势向上。\n"
        "2. **MACD**：DIF({dif}) 上穿 DEA({dea}) 位于零轴上方，红柱持续放大，多头动能增强。\n"
        "3. **KDJ**：K({k})、D({d}) 值在50上方金叉向上，J值({j})进入强势区，短线偏强。\n"
        "4. **成交量**：近3日成交量温和放大，场外资金入场迹象明显。\n\n"
        "⚠️ **风险提示**：上方{resistance}附近有前期套牢盘压力。"
    ),
    "trend_bearish": (
        "**技术面需谨慎**：\n\n"
        "1. **均线系统**：MA5({ma5}) < MA10({ma10})，短期均线下穿中期均线形成死叉，趋势转弱。\n"
        "2. **MACD**：DIF({dif}) 下穿 DEA({dea}) 形成死叉，绿柱出现，空头动能增强。\n"
        "3. **KDJ**：K({k})、D({d}) 值在50附近死叉向下，J值({j}) 进入弱势区。\n"
        "4. **布林带**：股价触及布林带上轨后回落，有回归中轨{mid}的倾向。\n\n"
        "⚠️ **操作建议**：建议减仓观望，{support}附近为第一支撑位。"
    ),
    "chanlun_buy": (
        "**缠论买点分析**：\n\n"
        "1. **分型结构**：日线级别出现底分型确认，第三元素不破第一元素低点，底部结构扎实。\n"
        "2. **笔的走势**：当前处于向下笔末端，即将形成向上笔，向下笔力度明显减弱（背驰迹象）。\n"
        "3. **中枢分析**：目前在{central_low}-{central_high}区间构建30分钟级别中枢。\n"
        "4. **买卖点**：出现**第三类买点**——股价回抽中枢上沿不破，确认突破有效。\n\n"
        "📌 **目标位**：第一目标{target1}，第二目标{target2}。"
    ),
    "chanlun_sell": (
        "**缠论卖点分析**：\n\n"
        "1. **分型结构**：日线级别出现顶分型确认，第三元素跌破第一元素低点，顶部结构风险加大。\n"
        "2. **笔的走势**：当前向上笔力度减弱，与前一向上笔形成背驰。\n"
        "3. **中枢分析**：股价运行至中枢上沿{central_high}附近遇阻。\n"
        "4. **买卖点**：出现**第二类卖点**——向上笔力度衰竭，反弹至中枢上沿无法突破。\n\n"
        "📌 **操作建议**：建议分批减仓。"
    ),
    "fund_analysis": (
        "**基金综合分析**：\n\n"
        "1. **净值走势**：近1月涨幅{month_ret:.2f}%，近3月涨幅{quarter_ret:.2f}%。\n"
        "2. **最大回撤**：近半年最大回撤{max_drawdown:.2f}%。\n"
        "3. **持仓分析**：前三大持仓为{top_holdings}，集中于{industry}。\n"
        "4. **风险评估**：年化波动率{volatility:.2f}%，夏普比率{sharpe:.2f}。\n\n"
        "📌 建议结合自身风险承受能力配置。"
    ),
    "market_overview": (
        "**市场大盘分析**：\n\n"
        "1. **上证指数**：收于{sh_index}点，涨幅{sh_change:+.2f}%。\n"
        "2. **深证成指**：收于{sz_index}点，涨幅{sz_change:+.2f}%。\n"
        "3. **创业板指**：收于{cy_index}点，涨幅{cy_change:+.2f}%。\n"
        "4. **成交量**：两市合计成交{volume}亿。\n"
        "5. **北向资金**：净流入{foreign_inflow}亿。\n\n"
        "📌 关注{hot_sector}板块的持续性。"
    ),
    "general_advice": (
        "**投资建议**：\n\n"
        "1. **当前策略**：建议以价值投资为主，关注基本面良好的龙头企业。\n"
        "2. **风险管理**：单只股票仓位不超过总资金的20%，设置5%-8%的止损线。\n"
        "3. **定投建议**：对于优质基金，可采用周定投策略平摊成本。\n\n"
        "📌 以上分析不构成投资建议，投资有风险，入市需谨慎。"
    ),
}

# ── Agent 模拟模板 ──
AGENT_TEMPLATES = {
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
    "news_analyst": {
        "bullish": (
            "**新闻情绪分析 - {stock_code}**\n\n"
            "近期相关新闻情感偏向积极，多篇正面报道。\n"
            "利好因素：行业利好政策出台，公司发布新品。\n\n"
            "结论：消息面偏正面。"
        ),
        "bearish": (
            "**新闻情绪分析 - {stock_code}**\n\n"
            "近期新闻情感偏向消极，负面消息增多。\n"
            "风险提示：行业监管趋严，业绩预警。\n\n"
            "结论：消息面偏负面，注意风险。"
        ),
    },
    "bullish_view": {
        "default": (
            "**看涨论据**：\n"
            "1. 均线多头排列，短期趋势向上\n"
            "2. MACD金叉，红柱持续放大\n"
            "3. 北向资金持续流入，主力加仓\n"
            "4. 行业景气度提升，政策利好\n"
            "结论：建议逢低买入，目标涨幅15-20%"
        ),
    },
    "bearish_view": {
        "default": (
            "**看跌论据**：\n"
            "1. 股价已到前期压力位，量能不足\n"
            "2. RSI进入超买区，回调风险加大\n"
            "3. 主力资金净流出，散户接盘\n"
            "4. 行业估值偏高，有回调需求\n"
            "结论：建议减仓观望，等待回调10-15%"
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


def get_mock_data(query: str = "") -> dict:
    """获取模拟数据，并可基于查询动态调整"""
    data = dict(UNIFIED_MOCK_DATA)
    data["query"] = query
    return data


def select_dialog_template(query: str) -> str:
    """根据查询关键词选择合适的对话模板"""
    q = query.lower()
    if "缠论" in q or "买点" in q or "卖点" in q:
        key = "chanlun_buy" if "买" in q else "chanlun_sell"
    elif "基金" in q or "净值" in q:
        key = "fund_analysis"
    elif "大盘" in q or "指数" in q or "市场" in q:
        key = "market_overview"
    elif "涨" in q or "看多" in q or "买入" in q:
        key = "trend_bullish"
    elif "跌" in q or "看空" in q or "卖出" in q:
        key = "trend_bearish"
    else:
        key = "general_advice"
    return DIALOG_TEMPLATES.get(key, DIALOG_TEMPLATES["general_advice"])


def get_agent_template(agent_role: str, sentiment: str = "bullish") -> str:
    """获取指定 Agent 角色的模拟模板"""
    role_key = agent_role.lower().replace(" ", "_").replace("-", "_")
    templates = AGENT_TEMPLATES.get(role_key, {})
    if not templates:
        return f"[{agent_role}] 模拟模式 (API Key 未配置)"

    template_key = sentiment if sentiment in templates else list(templates.keys())[0]
    return templates.get(template_key, list(templates.values())[0])


class SimulationEngine:
    """模拟引擎 — 无需AI模型即可生成分析"""

    @staticmethod
    def get_simulation(agent_role: str, context: dict) -> str:
        """获取指定角色的模拟回复"""
        template = get_agent_template(agent_role, context.get("sentiment", "bullish"))
        defaults = dict(UNIFIED_MOCK_DATA)
        defaults.update(context)
        try:
            return template.format(**defaults)
        except KeyError as e:
            return DIALOG_TEMPLATES["general_advice"].format(query=context.get("query", ""), **defaults)

    @staticmethod
    def analyze_with_simulation(agent_name: str, stock_code: str) -> dict:
        """模拟完整的Agent分析流程"""
        return {
            "agent": agent_name,
            "stock_code": stock_code,
            "mode": "simulation",
            "content": SimulationEngine.get_simulation(agent_name, {"stock_code": stock_code}),
        }
