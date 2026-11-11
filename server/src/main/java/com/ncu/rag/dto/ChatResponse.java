package com.ncu.rag.dto;

import java.util.List;

public class ChatResponse {
    private String conversationId;
    private String question;
    private String answer;
    private List<String> sources;

    public ChatResponse() {}

    public ChatResponse(String conversationId, String question, String answer, List<String> sources) {
        this.conversationId = conversationId;
        this.question = question;
        this.answer = answer;
        this.sources = sources;
    }

    public String getConversationId() {
        return conversationId;
    }

    public void setConversationId(String conversationId) {
        this.conversationId = conversationId;
    }

    public String getQuestion() {
        return question;
    }

    public void setQuestion(String question) {
        this.question = question;
    }

    public String getAnswer() {
        return answer;
    }

    public void setAnswer(String answer) {
        this.answer = answer;
    }

    public List<String> getSources() {
        return sources;
    }

    public void setSources(List<String> sources) {
        this.sources = sources;
    }
}
