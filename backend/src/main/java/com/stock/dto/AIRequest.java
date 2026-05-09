package com.stock.dto;

import lombok.Data;

@Data
public class AIRequest {
    private String message;
    private String stockCode = "";
    private java.util.List<ChatMessage> history;
}
