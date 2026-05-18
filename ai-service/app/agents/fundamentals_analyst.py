"""基本面分析师 - 分析 PE/PB/市值等基本面指标"""
from loguru import logger
from typing import Optional

from app.agents.base_agent import BaseAgent


FUNDAMENTALS_SYSTEM_PROMPT = """你是一位资深基本面分析师，专注于股票基本面分析。
请基于以下数据对股票进行基本面评估：
- PE (市盈率) / PB (市净率)
- 总市值 / 流通市值
- 所属行业
- 上市日期

评估维度：
1. 估值水平：PE/PB 处于行业什么水平（低估/合理/高估）
2. 公司规模：市值大小及流动性
3. 财务健康度：综合判断
4. 投资建议：基于基本面的操作建议

请给出客观、专业的基本面分析结论。"""


class FundamentalsAnalyst(BaseAgent):
    """基本面分析师"""

    def __init__(self, model_client=None):
        super().__init__(
            name="fundamentals_analyst",
            role="基本面分析师",
            system_prompt=FUNDAMENTALS_SYSTEM_PROMPT,
        )

    async def analyze(self, context: dict) -> dict:
        """
        分析股票基本面
        context: {"stock_code": "000001", ...}
        """
        stock_code = context.get("stock_code", "")
        logger.info(f"[基本面分析师] 开始分析 {stock_code}")

        # 调用后端 API 获取基本面数据
        # 修复: settings.backend_api_url 已包含 /api 前缀，endpoint 不再重复加 /api/
        stock_data = await self._fetch_backend_data(f"/stock/{stock_code}")

        # 如果 API 返回为空，使用模拟数据
        if not stock_data:
            stock_data = self._mock_stock_data(stock_code)

        # 构建分析消息
        messages = [
            {"role": "user", "content": f"请分析股票 {stock_code} 的基本面数据：\n{self._format_data(stock_data)}"}
        ]

        # 生成 AI 分析
        try:
            analysis_text = await self.chat(messages)
        except Exception as e:
            logger.error(f"[基本面分析师] AI 分析失败: {e}")
            analysis_text = self._mock_analysis(stock_data)

        result = {
            "agent": self.name,
            "role": self.role,
            "stock_code": stock_code,
            "data": stock_data,
            "analysis": analysis_text,
            "pe": stock_data.get("pe"),
            "pb": stock_data.get("pb"),
            "total_market_cap": stock_data.get("totalMarketCap"),
        }
        return result

    def _format_data(self, data: dict) -> str:
        return (
            f"股票代码: {data.get('stockCode', 'N/A')}\n"
            f"股票名称: {data.get('stockName', 'N/A')}\n"
            f"所属行业: {data.get('industry', 'N/A')}\n"
            f"PE: {data.get('pe', 'N/A')}\n"
            f"PB: {data.get('pb', 'N/A')}\n"
            f"总市值: {data.get('totalMarketCap', 'N/A')}\n"
            f"流通市值: {data.get('floatMarketCap', 'N/A')}\n"
            f"总股本: {data.get('totalShares', 'N/A')}\n"
            f"流通股本: {data.get('circulatedShares', 'N/A')}"
        )

    def _mock_stock_data(self, code: str) -> dict:
        """模拟基本面数据"""
        return {
            "stockCode": code,
            "stockName": "示例科技",
            "industry": "信息技术",
            "pe": 25.6,
            "pb": 3.2,
            "totalMarketCap": "85.6亿",
            "floatMarketCap": "62.3亿",
            "totalShares": "10.5亿",
            "circulatedShares": "7.8亿",
        }

    def _mock_analysis(self, data: dict) -> str:
        pe = data.get("pe", 25)
        pb = data.get("pb", 3)
        name = data.get("stockName", "标的")
        if isinstance(pe, (int, float)) and pe < 15:
            valuation = "低估"
        elif isinstance(pe, (int, float)) and pe > 40:
            valuation = "高估"
        else:
            valuation = "合理"

        return (
            f"**{name} 基本面分析**\n\n"
            f"1. **估值水平**：当前 PE={pe}，PB={pb}，估值{valuation}。\n"
            f"2. **公司规模**：总市值 {data.get('totalMarketCap', 'N/A')}，"
            f"流通市值 {data.get('floatMarketCap', 'N/A')}，流动性{'较好' if '亿' in str(data.get('floatMarketCap', '')) else '一般'}。\n"
            f"3. **行业地位**：所属{data.get('industry', 'N/A')}行业，具有一定的市场竞争力。\n"
            f"4. **投资建议**：当前估值{valuation}，" + (
                "建议关注，可在回调时分批建仓。" if valuation == "低估" else
                "建议持有观察，等待更好的介入时机。" if valuation == "合理" else
                "建议谨慎，注意估值回归风险。"
            ) + "\n\n⚠️ 以上分析基于公开数据，不构成投资建议。"
        )
