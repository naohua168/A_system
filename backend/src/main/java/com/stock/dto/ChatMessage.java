package com.stock.dto;

import lombok.Data;

@Data
public class ChatMessage {
    private String role;  // "user" | "assistant"
    private String content;
}
