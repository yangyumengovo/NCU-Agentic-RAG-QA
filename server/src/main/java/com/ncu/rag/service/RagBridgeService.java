package com.ncu.rag.service;

import com.ncu.rag.dto.ChatRequest;
import com.ncu.rag.dto.ChatResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

@Service
public class RagBridgeService {

    private final RestTemplate restTemplate;

    @Value("${rag.ai-engine-url:http://127.0.0.1:8000/api/rag/chat}")
    private String aiEngineUrl;

    public RagBridgeService(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    public ChatResponse processChat(ChatRequest request) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("question", request.getQuestion());
        payload.put("top_k", request.getTopK() != null ? request.getTopK() : 3);
        payload.put("conversation_id", request.getConversationId());

        try {
            return restTemplate.postForObject(aiEngineUrl, payload, ChatResponse.class);
        } catch (Exception e) {
            System.err.println("[Spring Boot Warning] AI Engine 暂未连接，启用解耦备用防护模式: " + e.getMessage());
            ChatResponse fallback = new ChatResponse();
            fallback.setConversationId(request.getConversationId());
            fallback.setQuestion(request.getQuestion());
            fallback.setAnswer("依据《南昌大学规章制度》规定：由于 AI 服务正在启动中，系统已记录您的询问：「" + request.getQuestion() + "」。请稍后重试或查看校内门户告示。");
            return fallback;
        }
    }
}
