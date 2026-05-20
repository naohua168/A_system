package com.stock.service;

import com.stock.dto.AIRequest;
import com.stock.dto.AIResponse;

import java.util.concurrent.CompletableFuture;

public interface AIDialogueService {
    /** AI 对话（异步，支持熔断和超时） */
    CompletableFuture<AIResponse> chat(AIRequest request);
}
