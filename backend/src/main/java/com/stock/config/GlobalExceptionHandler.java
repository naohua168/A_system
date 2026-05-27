package com.stock.config;

import com.stock.dto.ApiResponse;
import com.stock.dto.BusinessException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

import javax.validation.ConstraintViolationException;

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

    /**
     * Bean Validation 校验失败 — 对应 HTTP 400
     * 捕获 @Valid / @Validated 自动校验抛出的异常
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ApiResponse handleValidation(MethodArgumentNotValidException e) {
        String msg = e.getBindingResult().getFieldErrors().stream()
                .map(f -> f.getField() + ": " + f.getDefaultMessage())
                .reduce((a, b) -> a + "; " + b)
                .orElse("请求参数校验失败");
        log.warn("参数校验失败: {}", msg);
        return ApiResponse.error(400, "参数校验失败: " + msg);
    }

    /** 请求体/参数约束违规 — 对应 HTTP 400（多在 @RequestParam/@PathVariable 上约束） */
    @ExceptionHandler(ConstraintViolationException.class)
    public ApiResponse handleConstraintViolation(ConstraintViolationException e) {
        log.warn("参数约束违规: {}", e.getMessage());
        return ApiResponse.error(400, "参数约束违规: " + e.getMessage());
    }

    /** 业务异常 — Service 层通过 BusinessException 抛出（code 由业务自行定义） */
    @ExceptionHandler(BusinessException.class)
    public ApiResponse handleBusiness(BusinessException e) {
        log.warn("业务异常[code={}]: {}", e.getCode(), e.getMessage());
        return ApiResponse.error(e.getCode(), e.getMessage());
    }

    /** 无权限 — 对应 HTTP 403 */
    @ExceptionHandler(AccessDeniedException.class)
    public ApiResponse handleAccessDenied(AccessDeniedException e) {
        log.warn("访问被拒绝: {}", e.getMessage());
        return ApiResponse.error(403, "权限不足，无法访问该资源");
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

    /** 请求方法不支持 — 对应 HTTP 405 */
    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ApiResponse handleMethodNotSupported(HttpRequestMethodNotSupportedException e) {
        log.warn("不支持的请求方法: {}", e.getMessage());
        return ApiResponse.error(405, "请求方法不支持: " + e.getMessage());
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
