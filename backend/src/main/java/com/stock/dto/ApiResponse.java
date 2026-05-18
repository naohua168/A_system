package com.stock.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

/**
 * 统一 API 响应包装 — 所有控制器统一使用此类返回
 *
 * 成功: ApiResponse.ok(data)
 * 分页: ApiResponse.page(records, total, page, size)
 * 失败: ApiResponse.error(404, "股票不存在")
 * 异常: ApiResponse.exception(e)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ApiResponse {

    private int code;
    private String message;
    private Object data;
    private Long timestamp = System.currentTimeMillis();

    // ======================== 静态工厂 ========================

    public static ApiResponse ok(Object data) {
        return new ApiResponse(200, "success", data, System.currentTimeMillis());
    }

    public static ApiResponse ok() {
        return ok(null);
    }

    public static ApiResponse page(List<?> records, long total, int page, int size) {
        return ok(Map.of(
                "records", records,
                "total", total,
                "page", page,
                "size", size,
                "totalPages", (int) Math.ceil((double) total / size)
        ));
    }

    public static ApiResponse error(int code, String message) {
        return new ApiResponse(code, message, null, System.currentTimeMillis());
    }

    public static ApiResponse error(String message) {
        return error(400, message);
    }

    public static ApiResponse notFound(String message) {
        return error(404, message);
    }

    public static ApiResponse exception(Exception e) {
        return error(500, "服务器内部错误: " + e.getMessage());
    }

    public static ApiResponse created(Object data) {
        return new ApiResponse(201, "created", data, System.currentTimeMillis());
    }
}
