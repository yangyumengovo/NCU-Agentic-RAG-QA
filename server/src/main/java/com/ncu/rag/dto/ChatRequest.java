package com.ncu.rag.dto;

public class ChatRequest {
    private String question;
    private String conversationId;
    private Integer topK;

    public ChatRequest() {}

    public ChatRequest(String question, String conversationId, Integer topK) {
        this.question = question;
        this.conversationId = conversationId;
        this.topK = topK;
    }

    public String getQuestion() {
        return question;
    }

    public void setQuestion(String question) {
        this.question = question;
    }

    public String getConversationId() {
        return conversationId;
    }

    public void setConversationId(String conversationId) {
        this.conversationId = conversationId;
    }

    public Integer getTopK() {
        return topK;
    }

    public void setTopK(Integer topK) {
        this.topK = topK;
    }
}
