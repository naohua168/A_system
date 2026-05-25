package com.stock.config;

import com.stock.dto.ApiResponse;
import org.springframework.core.MethodParameter;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageConverter;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.mvc.method.annotation.ResponseBodyAdvice;

/**
 * 全局响应包装器 — 自动将所有 Controller 返回包装为统一 ApiResponse 格式
 * <p>
 * 修复: 解决前端 request.ts 拦截器期望 { code, data, message } 格式，
 * 但多个 Controller 返回原始 ResponseEntity 导致格式不匹配的问题。
 * 无需修改任何 Controller 代码。
 */
@RestControllerAdvice(basePackages = "com.stock.controller")
public class ApiResponseWrapper implements ResponseBodyAdvice<Object> {

    @Override
    public boolean supports(MethodParameter returnType, Class<? extends HttpMessageConverter<?>> converterType) {
        // 已经包装为 ApiResponse 的跳过
        if (returnType.getParameterType() == ApiResponse.class) {
            return false;
        }
        // String 类型特殊处理 (需单独 MessageConverter)
        if (returnType.getParameterType() == String.class) {
            return false;
        }
        // ResponseEntity 类型 — 保留原始 HTTP 状态码和结构  (如 404 Not Found)
        if (returnType.getParameterType() == ResponseEntity.class) {
            return false;
        }
        return true;
    }

    @Override
    public Object beforeBodyWrite(Object body, MethodParameter returnType,
                                   MediaType selectedContentType,
                                   Class<? extends HttpMessageConverter<?>> selectedConverterType,
                                   ServerHttpRequest request, ServerHttpResponse response) {
        // 如果已经是 ApiResponse 则直接返回
        if (body instanceof ApiResponse) {
            return body;
        }

        // 如果 Controller 返回 null，包装为成功空响应
        if (body == null) {
            return ApiResponse.ok(null);
        }

        // 自动包装为 ApiResponse
        return ApiResponse.ok(body);
    }
}
