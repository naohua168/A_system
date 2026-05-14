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
        return "**AI分析服务暂不可用**\n\n"
            + "后端 AI 对话服务（FastAPI）尚未启动或连接超时。\n\n"
            + "您的问题：\"" + message + "\" " + s + "\n\n"
            + "**请确保以下服务已启动：**\n"
            + "1. `ai-service` 模块：`cd ai-service && python -m app.main`\n"
            + "2. 后端服务已正确配置 `ai.service.url`\n\n"
            + "启动后即可获取基于 DeepSeek/Kimi 的真实 AI 分析回复。";
    }
}
