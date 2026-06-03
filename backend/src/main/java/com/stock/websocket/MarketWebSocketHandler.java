package com.stock.websocket;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import javax.websocket.*;
import javax.websocket.server.ServerEndpoint;
import java.io.IOException;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

@Component
@ServerEndpoint("/ws/market")
public class MarketWebSocketHandler {

    private static final Logger log = LoggerFactory.getLogger(MarketWebSocketHandler.class);

    /** topic -> 订阅该 topic 的 Session 集合 */
    private static final ConcurrentHashMap<String, Set<Session>> topicSessions = new ConcurrentHashMap<>();
    /** session -> 该 session 订阅的所有 topic */
    private static final ConcurrentHashMap<Session, Set<String>> sessionTopics = new ConcurrentHashMap<>();

    private static final ObjectMapper objectMapper = new ObjectMapper()
            .registerModule(new JavaTimeModule());

    @OnOpen
    public void onOpen(Session session) {
        log.info("MarketWS连接打开: sessionId={}", session.getId());
        try {
            session.getBasicRemote().sendText("{\"type\":\"connected\"}");
        } catch (IOException e) {
            log.error("发送连接确认失败: {}", e.getMessage());
        }
    }

    @SuppressWarnings("unchecked")
    @OnMessage
    public void onMessage(String message, Session session) {
        try {
            Map<String, Object> msg = objectMapper.readValue(message, Map.class);
            String type = (String) msg.get("type");
            String topic = (String) msg.get("topic");

            if ("subscribe".equals(type) && topic != null) {
                topicSessions.computeIfAbsent(topic, k -> ConcurrentHashMap.newKeySet()).add(session);
                sessionTopics.computeIfAbsent(session, k -> ConcurrentHashMap.newKeySet()).add(topic);
                session.getBasicRemote().sendText(
                        "{\"type\":\"subscribed\",\"topic\":\"" + topic + "\"}");
            } else if ("unsubscribe".equals(type) && topic != null) {
                Set<Session> sessions = topicSessions.get(topic);
                if (sessions != null) sessions.remove(session);
                Set<String> topics = sessionTopics.get(session);
                if (topics != null) topics.remove(topic);
                session.getBasicRemote().sendText(
                        "{\"type\":\"unsubscribed\",\"topic\":\"" + topic + "\"}");
            } else if ("ping".equals(type)) {
                session.getBasicRemote().sendText("{\"type\":\"pong\"}");
            }
        } catch (Exception e) {
            log.warn("MarketWS消息处理失败: {}", e.getMessage());
        }
    }

    @OnClose
    public void onClose(Session session) {
        log.info("MarketWS连接关闭: sessionId={}", session.getId());
        sessionTopics.remove(session);
        topicSessions.values().forEach(s -> s.remove(session));
        topicSessions.entrySet().removeIf(e -> e.getValue().isEmpty());
    }

    @OnError
    public void onError(Session session, Throwable error) {
        log.warn("MarketWS错误: sessionId={}, error={}", session.getId(), error.getMessage());
    }

    /** 向订阅某 topic 的所有客户端推送数据 */
    public static void broadcast(String topic, Object data) {
        Set<Session> sessions = topicSessions.get(topic);
        if (sessions == null || sessions.isEmpty()) return;

        String message;
        try {
            message = objectMapper.writeValueAsString(Map.of("type", "update", "topic", topic, "data", data));
        } catch (Exception e) {
            log.warn("序列化失败 topic={}: {}", topic, e.getMessage());
            return;
        }

        for (Session session : sessions) {
            if (session.isOpen()) {
                try {
                    session.getBasicRemote().sendText(message);
                } catch (IOException e) {
                    log.warn("推送失败 session={}: {}", session.getId(), e.getMessage());
                }
            }
        }
    }

    public static boolean hasSubscribers(String topic) {
        Set<Session> sessions = topicSessions.get(topic);
        return sessions != null && !sessions.isEmpty();
    }
}
