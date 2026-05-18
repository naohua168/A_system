package com.stock.security;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.method.HandlerMethod;
import org.springframework.web.servlet.HandlerInterceptor;

import java.lang.reflect.Method;

/**
 * 权限注解拦截器 — 解析 @RequirePermission 注解并校验权限
 * <p>
 * 在请求进入 Controller 之前拦截，根据注解中的权限要求进行校验。
 */
@Slf4j
@Component
public class PermissionInterceptor implements HandlerInterceptor {

    private final SecurityLevelService securityLevelService;

    public PermissionInterceptor(SecurityLevelService securityLevelService) {
        this.securityLevelService = securityLevelService;
    }

    @Override
    public boolean preHandle(HttpServletRequest request,
                             HttpServletResponse response,
                             Object handler) throws Exception {

        if (!(handler instanceof HandlerMethod handlerMethod)) {
            return true;
        }

        Method method = handlerMethod.getMethod();

        // 获取方法上的 @RequirePermission 注解
        RequirePermission annotation = method.getAnnotation(RequirePermission.class);
        if (annotation == null) {
            // 尝试从类级别获取
            annotation = handlerMethod.getBeanType().getAnnotation(RequirePermission.class);
        }
        if (annotation == null) {
            return true; // 无注解则放行
        }

        // 从请求中获取当前用户角色
        UserRole currentRole = extractUserRole(request);
        String requiredPermission = annotation.value();

        // 先检查角色级别
        if (!currentRole.canAccess(annotation.role())) {
            log.warn("角色级别不足: 当前={}, 需要={}", currentRole, annotation.role());
            response.setStatus(HttpServletResponse.SC_FORBIDDEN);
            response.setContentType("application/json;charset=UTF-8");
            response.getWriter().write("{\"code\":403,\"message\":\"" + annotation.message() + "\"}");
            return false;
        }

        // 再检查具体权限
        if (!securityLevelService.hasPermission(currentRole, requiredPermission)) {
            log.warn("权限不足: 用户角色={}, 所需权限={}", currentRole, requiredPermission);
            response.setStatus(HttpServletResponse.SC_FORBIDDEN);
            response.setContentType("application/json;charset=UTF-8");
            response.getWriter().write("{\"code\":403,\"message\":\"" + annotation.message() + "\"}");
            return false;
        }

        return true;
    }

    /**
     * 从请求中提取用户角色
     * 仅从 SecurityContextHolder 中 JwtFilter 注入的认证信息获取
     * 修复: 移除 X-User-Role Header 后门，防止权限提升攻击
     */
    private UserRole extractUserRole(HttpServletRequest request) {
        // 从 JwtFilter 设置的 attribute 中获取
        Object roleObj = request.getAttribute("userRole");
        if (roleObj instanceof UserRole) {
            return (UserRole) roleObj;
        }
        return UserRole.USER; // 默认普通用户
    }
}
