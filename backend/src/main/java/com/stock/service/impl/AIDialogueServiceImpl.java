package com.stock.service.impl;

import com.stock.dto.AIRequest;
import com.stock.dto.AIResponse;
import com.stock.service.AIDialogueService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

@Service
public class AIDialogueServiceImpl implements AIDialogueService {

    private final RestTemplate restTemplate = new RestTemplate();

    @Value("${ai.service.url:http://localhost:8000}")
    private String aiServiceUrl;

    @Override
    public AIResponse chat(AIRequest request) {
        try {
            String url = aiServiceUrl + "/api/ai/chat";
            return restTemplate.postForObject(url, request, AIResponse.class);
        } catch (Exception e) {
            // 降级：ai-service 不可用时返回模拟回复
            return fallbackReply(request.getMessage(), request.getStockCode());
        }
    }

    private AIResponse fallbackReply(String message, String stockCode) {
        String reply = generateMockReply(message, stockCode);
        AIResponse resp = new AIResponse();
        resp.setReply(reply);
        resp.setStatus("degraded");
        return resp;
    }

    private String generateMockReply(String message, String stockCode) {
        String s = (stockCode != null && !stockCode.isEmpty()) ? "（代码: " + stockCode + "）" : "";
        String msg = message.toLowerCase();

        if (msg.contains("缠论") || msg.contains("买点") || msg.contains("卖点")) {
            return "**缠论分析**" + s + "：\n\n"
                + "当前日线级别出现底分型确认，形成标准" + (msg.contains("买") ? "一买" : "二卖") + "信号。\n"
                + "• 分型结构：底分型第三元素不破第一元素低点，底部确认\n"
                + "• 笔的走势：向" + (msg.contains("买") ? "下" : "上") + "笔力度明显减弱，出现背驰\n"
                + "• 中枢分析：30分钟级别中枢（12.50-13.80）下沿附近获得有效支撑\n\n"
                + "⚠️ **风险提示**：建议结合成交量变化确认信号有效性，设置止损位。";
        } else if (msg.contains("基金") || msg.contains("净值")) {
            return "**基金分析**" + s + "：\n\n"
                + "• 近1月涨幅：+3.52%\n"
                + "• 近3月涨幅：+8.17%\n"
                + "• 近6月涨幅：-2.08%\n"
                + "• 最大回撤：12.50%（控制能力中等）\n"
                + "• 前十大持仓占比：48.3%\n"
                + "• 行业分布：消费（35%）、新能源（28%）、金融（22%）\n\n"
                + "📌 **建议**：该基金行业分布较均衡，适合作为组合底仓配置，建议定投方式入场。";
        } else if (msg.contains("大盘") || msg.contains("市场") || msg.contains("指数")) {
            return "**市场概览**：\n\n"
                + "• 上证指数：3,158.26（+0.68%）\n"
                + "• 深证成指：10,542.35（+1.24%）\n"
                + "• 创业板指：2,285.45（+1.86%）\n"
                + "• 两市成交额：8,562亿（较昨日放量15.3%）\n"
                + "• 北向资金净流入：42.5亿\n\n"
                + "📌 **总结**：市场放量反弹，AI算力、半导体板块领涨。短期关注量能持续性，"
                + "若能维持万亿级别成交，反弹有望延续。操作上建议持股为主，不宜追高。";
        } else if (msg.contains("涨") || msg.contains("看多")) {
            return "**看涨分析**" + s + "：\n\n"
                + "• MA5（5.28）> MA10（5.15）> MA20（4.98），多头排列\n"
                + "• MACD金叉，DIF（0.15）位于DEA（0.08）上方，红柱持续放大\n"
                + "• KDJ指标：K72、D65、J86，处于强势区间\n"
                + "• 成交量温和放大，资金入场迹象明显\n\n"
                + "⚠️ **注意**：上方5.60元附近有前期压力位，建议关注突破情况。若放量突破可加仓，"
                + "缩量回调则适当减仓锁定利润。";
        } else if (msg.contains("跌") || msg.contains("看空")) {
            return "**看空分析**" + s + "：\n\n"
                + "• MA5（5.28）< MA10（5.15），短期均线下穿形成死叉\n"
                + "• MACD死叉形成，绿柱出现，空头动能增强\n"
                + "• KDJ指标：K72、D65死叉向下，有调整需求\n"
                + "• 股价触及布林带上轨后回落，有回归中轨倾向\n\n"
                + "⚠️ **建议**：短期以减仓观望为主。下方4.80元为第一支撑位，"
                + "若放量跌破需考虑止损。等待企稳信号后再入场。";
        } else {
            return "**投资建议**：\n\n"
                + "1. **当前市场**：市场处于震荡整理阶段，建议控制仓位在50%-70%\n"
                + "2. **持仓建议**：单只股票仓位不超过20%，设置5%-8%止损线\n"
                + "3. **操作策略**：高抛低吸，切忌追涨杀跌\n"
                + "4. **板块关注**：AI算力、半导体、新能源（中长期逻辑清晰）\n"
                + "5. **风险提示**：关注美联储利率决议和地缘政治风险\n\n"
                + "📌 以上分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。";
        }
    }
}
