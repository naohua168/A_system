package com.stock.controller;

import com.stock.dto.AIRequest;
import com.stock.dto.AIResponse;
import com.stock.service.AIDialogueService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.concurrent.CompletableFuture;

@RestController
@RequestMapping("/api/ai")
public class AiDialogueController {

    @Autowired
    private AIDialogueService aiDialogueService;

    @PostMapping("/chat")
    public CompletableFuture<AIResponse> chat(@RequestBody AIRequest request) {
        // Spring MVC 自动等待 CompletableFuture 完成后返回
        return aiDialogueService.chat(request);
    }

    @GetMapping("/status")
    public Map<String, Object> status() {
        return Map.of(
            "service", "ai-dialogue",
            "aiServiceUrl", "http://localhost:8000",
            "status", "running"
        );
    }
}
