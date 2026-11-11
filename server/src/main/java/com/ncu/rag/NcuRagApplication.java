package com.ncu.rag;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.web.client.RestTemplate;

@SpringBootApplication
public class NcuRagApplication {

    public static void main(String[] args) {
        SpringApplication.run(NcuRagApplication.class, args);
        System.out.println("\n==========================================================");
        System.out.println("  南昌大学 RAG 高校制度智能问答系统 - Spring Boot 服务已启动 ");
        System.out.println("  后端 API 端口: http://127.0.0.1:8081");
        System.out.println("==========================================================\n");
    }

    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }
}
