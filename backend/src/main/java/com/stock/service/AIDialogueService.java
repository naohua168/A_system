package com.stock.service;

import com.stock.dto.AIRequest;
import com.stock.dto.AIResponse;

public interface AIDialogueService {
    AIResponse chat(AIRequest request);
}
