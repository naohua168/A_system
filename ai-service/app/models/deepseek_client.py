"""通用 AI 大模型客户端（支持 DeepSeek / OpenAI 兼容协议）"""
import json
import httpx
from loguru import logger
from typing import Optional

from app.config import settings

# ── 股市分析系统提示词 ──
SYSTEM_PROMPT = """你是一位专业的股市分析专家，擅长股票基金技术分析。
你能回答的问题包括：
1. 股票/基金行情分析：K线形态、趋势判断、支撑位/压力位
2. 技术指标解读：MA、MACD、KDJ、RSI、布林带等
3. 缠论分析：分型、笔、线段、中枢、买卖点
4. 行业板块分析：热点追踪、轮动判断
5. 投资策略建议：均线策略、趋势跟踪、风险控制

回答要求：
- 基于技术分析给出客观判断，不承诺收益
- 提及具体的技术指标数值作为论据
- 提示风险，说明分析仅供参考
- 回答简洁专业，控制在200-500字"""

# ── 模拟回复库（无 API Key 时使用） ──
MOCK_RESPONSES = {
    "trend_bullish": "**技术面看涨信号**：\n\n1. **均线系统**：MA5({ma5}) > MA10({ma10}) > MA20({ma20})，呈多头排列，短期趋势向上。\n2. **MACD**：DIF({dif}) 上穿 DEA({dea}) 位于零轴上方，红柱持续放大，多头动能增强。\n3. **KDJ**：K({k})、D({d}) 值在50上方金叉向上，J值({j})进入强势区，短线偏强。\n4. **成交量**：近3日成交量温和放大，场外资金入场迹象明显。\n\n⚠️ **风险提示**：上方{resistance}附近有前期套牢盘压力，建议若放量突破可继续持有，缩量回调则注意止盈。",

    "trend_bearish": "**技术面需谨慎**：\n\n1. **均线系统**：MA5({ma5}) < MA10({ma10})，短期均线下穿中期均线形成死叉，趋势转弱。\n2. **MACD**：DIF({dif}) 下穿 DEA({dea}) 形成死叉，绿柱出现，空头动能增强。\n3. **KDJ**：K({k})、D({d}) 值在50附近死叉向下，J值({j}) 进入弱势区，短期有调整需求。\n4. **布林带**：股价触及布林带上轨后回落，有回归中轨{mid}的倾向。\n\n⚠️ **操作建议**：建议减仓观望，等待企稳信号。下方{support}附近为第一支撑位，若放量跌破需止损。",

    "chanlun_buy": "**缠论买点分析**：\n\n1. **分型结构**：日线级别出现底分型确认，且第三元素不破第一元素低点，底部结构扎实。\n2. **笔的走势**：当前处于向下笔末端，即将形成向上笔。向下笔力度较前一笔明显减弱（背驰迹象）。\n3. **中枢分析**：目前在{central_low}-{central_high}区间构建30分钟级别中枢，中枢下沿获得支撑。\n4. **买卖点**：出现**第三类买点**——股价回抽中枢上沿不破，确认突破有效。\n\n📌 **目标位**：第一目标{target1}，第二目标{target2}。止损位设于{support}下方。",

    "chanlun_sell": "**缠论卖点分析**：\n\n1. **分型结构**：日线级别出现顶分型确认，第三元素跌破第一元素低点，顶部结构风险加大。\n2. **笔的走势**：当前向上笔力度减弱，与前一向上笔形成背驰。\n3. **中枢分析**：股价运行至中枢上沿{central_high}附近遇阻。\n4. **买卖点**：出现**第二类卖点**——向上笔力度衰竭，反弹至中枢上沿无法突破。\n\n📌 **操作建议**：建议分批减仓。若后续跌破中枢下沿{central_low}需果断离场。",

    "fund_analysis": "**基金综合分析**：\n\n1. **净值走势**：近1月涨幅{month_ret:.2f}%，近3月涨幅{quarter_ret:.2f}%，近6月涨幅{half_ret:.2f}%。\n2. **最大回撤**：近半年最大回撤{max_drawdown:.2f}%，回撤控制{'较好' if max_drawdown < 10 else '一般' if max_drawdown < 20 else '较差'}。\n3. **持仓分析**：前三大持仓为{top_holdings}，集中于{industry}板块，行业集中度{conc_level}。\n4. **风险评估**：年化波动率{volatility:.2f}%，夏普比率{sharpe:.2f}（>1表示性价比尚可）。\n\n📌 **建议**：{'适合风险偏好较低的投资者作为底仓配置' if max_drawdown < 10 else '需关注市场风格切换风险，建议分批建仓' if max_drawdown < 20 else '波动较大，建议观望或小额定投'}。",

    "market_overview": "**市场大盘分析**：\n\n1. **上证指数**：收于{sh_index}点，涨幅{sh_change:+.2f}%。\n2. **深证成指**：收于{sz_index}点，涨幅{sz_change:+.2f}%。\n3. **创业板指**：收于{cy_index}点，涨幅{cy_change:+.2f}%。\n4. **成交量**：两市合计成交{volume}亿，较前一交易日{'放' if volume_compare > 0 else '缩'}量{volume_diff}%。\n5. **北向资金**：净流入{foreign_inflow}亿，{'外资看好当前点位' if foreign_inflow > 0 else '外资流出压力增大'}。\n\n📌 **总结**：{'市场情绪回暖，短期可适度乐观' if sh_change > 0 else '市场仍处调整期，建议控制仓位'}。关注{hot_sector}板块的持续性。",

    "general_advice": "**投资建议**：\n\n1. **当前策略**：{'市场处于震荡区间，建议高抛低吸，控制仓位在50%-70%' if '震荡' in query else '趋势向上时顺势持仓，跌破关键支撑位减仓' if '趋势' in query else '建议以价值投资为主，关注基本面良好的龙头企业'}。\n2. **风险管理**：单只股票仓位不超过总资金的20%，设置5%-8%的止损线。\n3. **定投建议**：对于优质基金，可采用周定投策略平摊成本。\n4. **长期视角**：短期波动不改长期趋势，保持耐心和纪律。\n\n📌 以上分析不构成投资建议，投资有风险，入市需谨慎。",
}

MOCK_TEMPLATES = {k: v for k, v in MOCK_RESPONSES.items()}


class AIClient:
    """AI 大模型客户端，支持 DeepSeek 兼容协议，无 API Key 时使用模拟模式"""

    def __init__(self):
        self.api_key = settings.deepseek_api_key
        self.api_url = settings.deepseek_api_url
        self.model = settings.deepseek_model
        self.mock_mode = not bool(self.api_key)
        if self.mock_mode:
            logger.warning("⚠️ 未配置 DEEPSEEK_API_KEY，将使用模拟回复模式")

    async def chat(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 1024) -> str:
        """发送对话请求"""
        if self.mock_mode:
            return self._mock_reply(messages)
        return await self._real_chat(messages, temperature, max_tokens)

    async def _real_chat(self, messages: list[dict], temperature: float, max_tokens: int) -> str:
        """调用真实 API"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                payload = {
                    "model": self.model,
                    "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                resp = await client.post(self.api_url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"AI API 调用失败: {e}")
            return self._mock_reply(messages)

    def _mock_reply(self, messages: list[dict]) -> str:
        """模拟回复（用于演示/开发阶段）"""
        last_msg = messages[-1]["content"] if messages else ""
        query = last_msg.lower()

        # 根据关键词选择合适的回复模板
        mock_data = {
            "ma5": "5.28", "ma10": "5.15", "ma20": "4.98",
            "dif": "0.15", "dea": "0.08",
            "k": "72", "d": "65", "j": "86",
            "resistance": "5.60元", "support": "4.80元",
            "mid": "5.10",
            "central_low": "12.50", "central_high": "13.80",
            "target1": "14.50元", "target2": "15.80元", "support": "12.00",
            "month_ret": 3.5, "quarter_ret": 8.2, "half_ret": -2.1,
            "max_drawdown": 12.5,
            "top_holdings": "茅台、宁德时代、招商银行",
            "industry": "消费+新能源+金融",
            "conc_level": "较高",
            "volatility": 18.5, "sharpe": 1.2,
            "sh_index": "3,158.26", "sh_change": 0.68,
            "sz_index": "10,542.35", "sz_change": 1.24,
            "cy_index": "2,285.45", "cy_change": 1.86,
            "volume": "8,562", "volume_compare": True, "volume_diff": "15.3",
            "foreign_inflow": "42.5",
            "hot_sector": "AI算力、半导体",
            "query": query,
        }

        if "缠论" in query or "买点" in query or "卖点" in query:
            template = MOCK_TEMPLATES.get("chanlun_buy" if "买" in query else "chanlun_sell", MOCK_TEMPLATES["chanlun_buy"])
        elif "基金" in query or "净值" in query:
            template = MOCK_TEMPLATES["fund_analysis"]
        elif "大盘" in query or "指数" in query or "市场" in query:
            template = MOCK_TEMPLATES["market_overview"]
        elif "涨" in query or "看多" in query or "买入" in query:
            template = MOCK_TEMPLATES["trend_bullish"]
        elif "跌" in query or "看空" in query or "卖出" in query:
            template = MOCK_TEMPLATES["trend_bearish"]
        else:
            template = MOCK_TEMPLATES["general_advice"]

        try:
            return template.format(**mock_data)
        except KeyError:
            return MOCK_TEMPLATES["general_advice"].format(query=query)

    @property
    def status(self) -> dict:
        return {
            "mode": "mock" if self.mock_mode else "real",
            "model": self.model if not self.mock_mode else "mock-deepseek",
            "api_configured": not self.mock_mode,
            "hint": "配置 DEEPSEEK_API_KEY 环境变量可使用真实 AI 模型" if self.mock_mode else "已连接 DeepSeek API",
        }


client = AIClient()
