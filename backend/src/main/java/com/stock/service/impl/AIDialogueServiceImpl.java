package com.stock.service.impl;

import com.stock.dto.AIRequest;
import com.stock.dto.AIResponse;
import com.stock.service.AIDialogueService;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import io.github.resilience4j.timelimiter.annotation.TimeLimiter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.concurrent.CompletableFuture;

@Service
public class AIDialogueServiceImpl implements AIDialogueService {

    private static final Logger log = LoggerFactory.getLogger(AIDialogueServiceImpl.class);

    private final RestTemplate restTemplate = new RestTemplate();

    @Value("${ai.service.url:http://localhost:8000}")
    private String aiServiceUrl;

    @Override
    @CircuitBreaker(name = "ai-service", fallbackMethod = "fallbackChat")
    @TimeLimiter(name = "ai-service")
    public CompletableFuture<AIResponse> chat(AIRequest request) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                String url = aiServiceUrl + "/api/ai/chat";
                log.debug("AI对话请求: message={}, stockCode={}", request.getMessage(), request.getStockCode());
                AIResponse response = restTemplate.postForObject(url, request, AIResponse.class);
                if (response == null) {
                    throw new RuntimeException("AI 服务返回空响应");
                }
                return response;
            } catch (Exception e) {
                log.warn("AI服务调用失败: {}", e.getMessage());
                throw new RuntimeException("AI 服务调用异常", e);
            }
        });
    }

    /**
     * 熔断降级方法 — AI 服务不可用时返回模拟回复
     */
    @SuppressWarnings("unused")
    private AIResponse fallbackChat(AIRequest request, Throwable t) {
        log.warn("熔断器触发 (ai-service): {}", t.getMessage());
        String reply = generateMockReply(request.getMessage(), request.getStockCode());
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
            + "启动后即可获取基于 AI 大模型的真实分析回复。";
    }
}
