package com.stock.dto;

import lombok.Data;

@Data
public class AIResponse {
    private String reply;
    private String status = "success";
}
