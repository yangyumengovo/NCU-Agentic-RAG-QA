package com.ncu.rag.controller;

import com.ncu.rag.dto.ChatRequest;
import com.ncu.rag.dto.ChatResponse;
import com.ncu.rag.service.RagBridgeService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@RestController
@RequestMapping("/api/chat")
@CrossOrigin(origins = "*") // 跨域支持
public class ChatController {

    private final RagBridgeService ragBridgeService;

    public ChatController(RagBridgeService ragBridgeService) {
        this.ragBridgeService = ragBridgeService;
    }

    @PostMapping("/send")
    public ResponseEntity<ChatResponse> sendMessage(@RequestBody ChatRequest request) {
        if (request.getQuestion() == null || request.getQuestion().trim().isEmpty()) {
            return ResponseEntity.badRequest().build();
        }
        if (request.getConversationId() == null) {
            request.setConversationId(UUID.randomUUID().toString());
        }
        ChatResponse response = ragBridgeService.processChat(request);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/suggestions")
    public ResponseEntity<List<String>> getSuggestedQuestions() {
        List<String> suggestions = Arrays.asList(
            "缺考满多少比例会被取消考试资格？",
            "南昌大学申请学士学位的 GPA 要求是多少？",
            "在校最长修业年限是多少年？",
            "特等奖学金与一等奖学金的评选条件与金额？",
            "受记过处分毕业时能否获得学士学位？"
        );
        return ResponseEntity.ok(suggestions);
    }
}
