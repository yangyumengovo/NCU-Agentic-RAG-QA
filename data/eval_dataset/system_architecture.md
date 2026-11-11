# 基于 RAG 的高校制度文档智能问答系统 - 系统总体架构图与设计说明

**论文题目**：基于 RAG 的高校制度文档智能问答系统  
**设计标准**：符合计算机科学与技术 / 软件工程专业毕业论文规范学术风格

---

## 一、 系统总体架构图 (Mermaid Academic Diagram)

```mermaid
graph TD
    %% 样式定义：符合学术出版物灰度/经典蓝色调
    classDef layerBox fill:#f8fafc,stroke:#1e293b,stroke-width:2px,color:#0f172a,font-weight:bold;
    classDef compBox fill:#ffffff,stroke:#0284c7,stroke-width:1.5px,color:#0f172a;
    classDef dbBox fill:#eff6ff,stroke:#1d4ed8,stroke-width:1.5px,color:#1e3a8a;
    classDef llmBox fill:#faf5ff,stroke:#7e22ce,stroke-width:1.5px,color:#581c87;

    subgraph Layer1 ["用户交互层 (User Presentation Layer / Vue3 UI)"]
        UI_Web["昌大青蓝标准 UI 对话框"]
        UI_Scope["身份作用域选择器 (Scope Selector)"]
        UI_SSE["SSE 打字机流式推流渲染器"]
        UI_Source["官方依据卡片与点赞反馈组件"]
    end

    subgraph Layer2 ["应用接口层 (API Gateway & Service Layer)"]
        API_FastAPI["FastAPI AI 接口服务端 (Port 8000)"]
        API_SSE["/api/rag/chat/stream 流式推流端点"]
        API_FB["/api/rag/feedback 反馈端点"]
        API_SpringBoot["Spring Boot Java 业务控制网关"]
    end

    subgraph Layer3 ["核心 RAG 算法引擎层 (Core RAG Algorithm Engine Layer)"]
        ALG_Route["双路意图路由器 (Dual-Route Intent Router)"]
        ALG_Memory["多轮指代消解器 (Coreference Resolver)"]
        ALG_Rewrite["Query 扩展与学术同义词改写器"]
        
        subgraph Alg_Search ["混合检索与重排序模块 (Hybrid Retrieval & Reranking)"]
            SRCH_Dense["Dense 密集语义向量相似度 (TF-IDF)"]
            SRCH_Sparse["Sparse 稀疏关键词匹配 (BM25)"]
            SRCH_Fusion["混合得分加权融合器 (Score Fusion)"]
            SRCH_Filter["Scope 作用域与业务分类过滤器"]
            SRCH_Rerank["Cross-Encoder 交叉重排序器 (Reranker)"]
        end
    end

    subgraph Layer4 ["大语言模型推理层 (LLM Inference Layer)"]
        LLM_Prompt["Prompt 模板构建与切片 Context 注入器"]
        LLM_Engine["智谱 AI GLM-4-Flash / OpenAI 标准兼容基类"]
    end

    subgraph Layer5 ["数据与持久化层 (Data & Persistence Layer)"]
        DB_Raw["12 大领域规章 Markdown 原文库"]
        DB_Chunk["98 个带 Scope Metadata 结构化切片"]
        DB_Vectors["ncu_regulations_vectors.pkl 混合向量库"]
        DB_SQLite["ncu_rag_history.db (会话/消息/反馈表)"]
    end

    %% 数据流走向连接关系
    UI_Web -->|"1. 提交口语化提问"| API_SSE
    UI_Scope -->|"带入 Scope 身份参数"| API_SSE
    API_SSE -->|"2. 调用算法管线"| ALG_Memory
    
    ALG_Memory -->|"3. 指代消解重构"| ALG_Route
    ALG_Route -->|"政策类问答"| ALG_Rewrite
    ALG_Route -->|"通用闲聊"| LLM_Engine

    ALG_Rewrite -->|"4. 扩展查询"| SRCH_Dense
    ALG_Rewrite -->|"4. 扩展查询"| SRCH_Sparse
    
    DB_Vectors -.->|"向量读取"| SRCH_Dense
    DB_Vectors -.->|"索引读取"| SRCH_Sparse

    SRCH_Dense --> SRCH_Fusion
    SRCH_Sparse --> SRCH_Fusion
    SRCH_Fusion --> SRCH_Filter
    DB_Chunk -.->|"Metadata 校验"| SRCH_Filter
    SRCH_Filter -->|"粗筛候选集"| SRCH_Rerank
    
    SRCH_Rerank -->|"5. 准确 Top-3 切片"| LLM_Prompt
    DB_Raw -.->|"提供原文条目"| LLM_Prompt
    LLM_Prompt -->|"6. 包含 Context 的 Prompt"| LLM_Engine

    LLM_Engine -->|"7. SSE 逐字流式推流"| API_SSE
    API_SSE -->|"8. 实时打字机展现"| UI_SSE
    UI_Source -.->|"9. 点击点赞/点踩"| API_FB
    API_FB -->|"10. 持久化落盘"| DB_SQLite
    API_SSE -.->|"自动保存问答历史"| DB_SQLite

    class Layer1,Layer2,Layer3,Layer4,Layer5 layerBox;
    class UI_Web,UI_Scope,UI_SSE,UI_Source,API_FastAPI,API_SSE,API_FB,API_SpringBoot compBox;
    class ALG_Route,ALG_Memory,ALG_Rewrite,SRCH_Dense,SRCH_Sparse,SRCH_Fusion,SRCH_Filter,SRCH_Rerank compBox;
    class LLM_Prompt,LLM_Engine llmBox;
    class DB_Raw,DB_Chunk,DB_Vectors,DB_SQLite dbBox;
```

---

## 二、 架构分层设计说明 (用于论文正文第三章)

### 1. 用户交互层 (User Presentation Layer)
- **多端适配 Vue3 对话界面**：遵循南昌大学 2022 版官方品牌 VI 规范（昌大青蓝 `#12368F` 与瓷白底色），支持跨设备浏览。
- **动态 Scope 作用域过滤器**：支持用户灵活切换【本科生】/【研究生】/【全校通用】三大权限作用域，从前端源头过滤非目标权限的制度文件。
- **SSE 逐字流式渲染器**：基于 JavaScript `ReadableStream` 与 `TextDecoder`，实现大模型输出的打字机光标（`▌`）实时动效。

### 2. 应用接口与控制层 (API Gateway Layer)
- **FastAPI 异步高并发服务**：运行于 `http://127.0.0.1:8000`，提供 `/api/rag/chat/stream`、`/api/rag/sessions` 和 `/api/rag/feedback` 端点。
- **流式响应控制器**：设置 `media_type="text/event-stream"` 和 `X-Accel-Buffering: no` 消息头，保障数据推流的低时延与零阻塞。

### 3. 核心 RAG 算法引擎层 (Core Algorithm Engine Layer)
- **双路意图路由器 (Dual-Route Router)**：通过正则表达式与关键词识别，自动将请求分流至【通用闲聊通道】或【可信校规 RAG 通道】。
- **多轮指代消解器 (Coreference Resolver)**：维护 `ConversationMemoryManager` 会话记忆，自动补全追问中的模糊代词（如“它”、“这个”），生成独立可检索问句。
- **Query 改写与扩展器 (Query Expansion)**：通过 12 大领域同义词字典将口语化提问标准化扩展（如“挂科” $\rightarrow$ “课程考核不及格 补考 重修”）。
- **混合检索与重排序器 (Hybrid Search & Cross-Reranker)**：
  - **Dense 向量**：TF-IDF 字符 2~4 gram 密集语义计算；
  - **Sparse 向量**：BM25 词频稀疏关键词提取；
  - **Score Fusion**：权重系数 $\alpha = 0.6$ 进行得分线性加权融合；
  - **Cross-Reranker**：对粗筛候选集实施二次交叉比对精排，输出 Top-3 精准切片。

### 4. 大语言模型推理层 (LLM Inference Layer)
- **Prompt 结构化注入**：将匹配出的制度名称、章节、条目及正文填入严格受限的系统 Prompt（System Prompt），要求“必须严格依据参考文档回答”。
- **智谱 AI GLM-4-Flash**：通过兼容 OpenAI SDK 的统一接口发起 API 流式推理，兼具极速响应与强逻辑总结能力。

### 5. 数据与持久化层 (Data & Persistence Layer)
- **规章 Markdown 语料库**：收录 12 大领域权威发文原文。
- **结构化切片库**：包含 98 个富集 `doc_title`, `chapter`, `article`, `student_type`, `category` 的 JSON 结构化切片。
- **SQLite 关系型数据库**：持久化存储 `chat_sessions`（会话表）、`chat_messages`（问答明细表）和 `user_feedbacks`（评分反馈表）。
