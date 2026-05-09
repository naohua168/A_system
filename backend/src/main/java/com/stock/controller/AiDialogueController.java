package com.stock.controller;

import com.stock.dto.AIRequest;
import com.stock.dto.AIResponse;
import com.stock.service.AIDialogueService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/ai")
public class AiDialogueController {

    @Autowired
    private AIDialogueService aiDialogueService;

    @PostMapping("/chat")
    public AIResponse chat(@RequestBody AIRequest request) {
        return aiDialogueService.chat(request);
    }

    @GetMapping("/status")
    public java.util.Map<String, Object> status() {
        return java.util.Map.of(
            "service", "ai-dialogue",
            "aiServiceUrl", "http://localhost:8000",
            "status", "running"
        );
    }
}
