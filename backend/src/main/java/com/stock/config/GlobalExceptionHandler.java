package com.stock.config;

import com.stock.dto.ApiResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

/**
 * 全局异常处理器 — 统一所有 Controller 的异常响应格式。
 * <p>
 * 对应 L3 Python 层的统一异常处理模式：
 * <pre>
 *   try:
 *       ...
 *   except ValueError as e:
 *       return {"code": 400, "message": str(e)}
 *   except Exception as e:
 *       logger.error("...", exc_info=True)
 *       return {"code": 500, "message": "服务器内部错误"}
 * </pre>
 */
@RestControllerAdvice(basePackages = "com.stock.controller")
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    /** 参数缺失 / 参数类型错误 — 对应 HTTP 400 */
    @ExceptionHandler({
            MissingServletRequestParameterException.class,
            MethodArgumentTypeMismatchException.class,
            IllegalArgumentException.class,
            HttpMessageNotReadableException.class,
    })
    public ApiResponse handleBadRequest(Exception e) {
        log.warn("请求参数错误: {}", e.getMessage());
        return ApiResponse.error(400, "请求参数错误: " + e.getMessage());
    }

    /** 数据不存在 / 空结果 — 对应 HTTP 404 */
    @ExceptionHandler({
            java.util.NoSuchElementException.class,
            // EntityNotFoundException 由 JPA 提供，未引入依赖时可去掉
            // jakarta.persistence.EntityNotFoundException.class,
    })
    public ApiResponse handleNotFound(Exception e) {
        log.warn("资源不存在: {}", e.getMessage());
        return ApiResponse.notFound(e.getMessage());
    }

    /** 数据库访问异常 — 对应 HTTP 500 */
    @ExceptionHandler(DataAccessException.class)
    public ApiResponse handleDataAccess(DataAccessException e) {
        log.error("数据库访问异常: ", e);
        return ApiResponse.error(500, "数据库访问异常");
    }

    /** 兜底异常 — 对应 HTTP 500 */
    @ExceptionHandler(Exception.class)
    public ApiResponse handleGeneral(Exception e) {
        log.error("服务器内部错误: ", e);
        return ApiResponse.error(500, "服务器内部错误");
    }
}
