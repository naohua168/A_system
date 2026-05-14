package com.stock.websocket;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import javax.websocket.*;
import javax.websocket.server.PathParam;
import javax.websocket.server.ServerEndpoint;
import java.io.IOException;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

@Component
@ServerEndpoint("/ws/stock/{code}")
public class StockWebSocketHandler {

    private static final Logger log = LoggerFactory.getLogger(StockWebSocketHandler.class);

    /**
     * 股票代码 -> 订阅该股票的Session集合
     */
    private static final ConcurrentHashMap<String, Set<Session>> stockSessions = new ConcurrentHashMap<>();

    private static final ObjectMapper objectMapper = new ObjectMapper()
            .registerModule(new JavaTimeModule());

    @OnOpen
    public void onOpen(Session session, @PathParam("code") String code) {
        log.info("WebSocket连接打开: stock={}, sessionId={}", code, session.getId());
        stockSessions.computeIfAbsent(code, k -> ConcurrentHashMap.newKeySet()).add(session);

        try {
            session.getBasicRemote().sendText("{\"type\":\"connected\",\"code\":\"" + code + "\"}");
        } catch (IOException e) {
            log.error("发送连接确认消息失败: {}", e.getMessage());
        }
    }

    @OnMessage
    public void onMessage(String message, Session session) {
        log.debug("收到WebSocket消息: {}", message);
        try {
            // 解析客户端消息，支持订阅/取消订阅操作
            @SuppressWarnings("unchecked")
            Map<String, Object> msg = objectMapper.readValue(message, Map.class);
            String type = (String) msg.get("type");
            String code = (String) msg.get("code");

            if ("subscribe".equals(type) && code != null) {
                stockSessions.computeIfAbsent(code, k -> ConcurrentHashMap.newKeySet()).add(session);
                session.getBasicRemote().sendText(
                        "{\"type\":\"subscribed\",\"code\":\"" + code + "\"}");
            } else if ("unsubscribe".equals(type) && code != null) {
                Set<Session> sessions = stockSessions.get(code);
                if (sessions != null) {
                    sessions.remove(session);
                    if (sessions.isEmpty()) {
                        stockSessions.remove(code);
                    }
                }
                session.getBasicRemote().sendText(
                        "{\"type\":\"unsubscribed\",\"code\":\"" + code + "\"}");
            } else if ("ping".equals(type)) {
                session.getBasicRemote().sendText("{\"type\":\"pong\"}");
            }
        } catch (Exception e) {
            log.error("处理WebSocket消息失败: {}", e.getMessage());
        }
    }

    @OnClose
    public void onClose(Session session, @PathParam("code") String code) {
        log.info("WebSocket连接关闭: stock={}, sessionId={}", code, session.getId());
        // 从所有订阅中移除该session
        for (Set<Session> sessions : stockSessions.values()) {
            sessions.remove(session);
        }
        // 清理空集合
        stockSessions.entrySet().removeIf(entry -> entry.getValue().isEmpty());
    }

    @OnError
    public void onError(Session session, Throwable error, @PathParam("code") String code) {
        log.error("WebSocket错误: stock={}, sessionId={}, error={}", code, session.getId(), error.getMessage());
    }

    /**
     * 向订阅某只股票的所有客户端推送K线更新数据
     */
    public static void sendKlineUpdate(String code, Object data) {
        Set<Session> sessions = stockSessions.get(code);
        if (sessions == null || sessions.isEmpty()) {
            return;
        }

        String message;
        try {
            message = objectMapper.writeValueAsString(
                    Map.of("type", "kline_update", "code", code, "data", data));
        } catch (Exception e) {
            log.error("序列化K线数据失败: {}", e.getMessage());
            return;
        }

        for (Session session : sessions) {
            if (session.isOpen()) {
                try {
                    session.getBasicRemote().sendText(message);
                } catch (IOException e) {
                    log.warn("向客户端 {} 推送K线数据失败: {}", session.getId(), e.getMessage());
                    sessions.remove(session);
                }
            }
        }
    }

    /**
     * 获取当前订阅的股票代码列表
     */
    public static Set<String> getSubscribedCodes() {
        return stockSessions.keySet();
    }

    /**
     * 获取某只股票的订阅数
     */
    public static int getSubscriberCount(String code) {
        Set<Session> sessions = stockSessions.get(code);
        return sessions == null ? 0 : sessions.size();
    }
}
