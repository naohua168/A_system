package com.stock.dto;

/**
 * 业务异常 — Service 层抛出自定义业务异常，由 GlobalExceptionHandler 统一处理。
 * <p>用法：throw new BusinessException(400, "股票代码不存在");</p>
 */
public class BusinessException extends RuntimeException {

    private final int code;

    public BusinessException(int code, String message) {
        super(message);
        this.code = code;
    }

    public int getCode() {
        return code;
    }
}
