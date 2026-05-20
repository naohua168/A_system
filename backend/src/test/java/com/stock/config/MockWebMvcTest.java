package com.stock.config;

import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.core.annotation.AliasFor;

import java.lang.annotation.*;

/**
 * 组合注解: @WebMvcTest + Mock SecurityLevelService
 *
 * 替代 @WebMvcTest(SomethingController.class)，自动处理安全依赖。
 *
 * 用法:
 * <pre>
 * &#064;MockWebMvcTest(UserController.class)
 * class UserControllerTest { ... }
 * </pre>
 */
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@WebMvcTest
@Import(WebMvcTestConfig.class)
public @interface MockWebMvcTest {

    @AliasFor(annotation = WebMvcTest.class, attribute = "controllers")
    Class<?>[] value() default {};

    @AliasFor(annotation = WebMvcTest.class, attribute = "controllers")
    Class<?>[] controllers() default {};
}
