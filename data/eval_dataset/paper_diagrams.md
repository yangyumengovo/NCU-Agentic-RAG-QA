# 基于 RAG 的高校制度问答系统 - 论文级流程图设计指南与高清示例

**适用范围**：本科/硕士毕业论文、学术会议期刊论文结构图设计  
**设计目标**：精准匹配顶级计算机学术论文（如 IEEE/ACM/AAAI）的图表排版风格，供后续绘图软件（Draw.io / Visio / ProcessOn）手搓使用。

---

## 风格一：3 阶段虚线框模块化工程流程图 (Structured Pipeline Architecture)

适合作为论文 **【第二章 算法设计与工程实现】** 或 **【整体算法流程图】** 使用。结构清晰、阶段分明（数据预处理 $\rightarrow$ 索引与重排 $\rightarrow$ 上下文消解与 LLM 生成），底部带有“核心路径摘要”。

![风格一：3 阶段虚线框模块化工程流程图](C:\Users\meng\.gemini\antigravity\brain\2ee94b74-a197-4436-b728-f1a694229c05\rag_pipeline_style1_1785052403295.jpg)

### 风格一手搓元件与排版布局指南：
1. **三大主模块虚线框 (Phase Containers)**：
   - **模块 1（左侧，蓝色虚线框 `1. 语料预处理与结构化切片工程`）**：
     - ① 原始 12 份 Markdown 发文原文 $\rightarrow$ ② 结构感知解析器（章节条分类） $\rightarrow$ ③ Scope Metadata 标注（`student_type`, `category`） $\rightarrow$ 生成文件 `ncu_regulations_chunks.json` (98 Chunks)。
   - **模块 2（中间，绿色虚线框 `2. 离线双路索引与 Cross-Rerank 重排引擎`）**：
     - ④ TF-IDF Dense 密集语义向量 + ⑤ BM25 Sparse 稀疏关键词词频 $\rightarrow$ ⑥ 混合得分融合 ($\alpha = 0.6$) $\rightarrow$ ⑦ Cross-Encoder 重排序精排 $\rightarrow$ 导出 `ncu_regulations_vectors.pkl`。
   - **模块 3（右侧，橙色虚线框 `3. 多轮上下文消解与流式 LLM 生成`）**：
     - ⑧ 多轮指代消解器 $\rightarrow$ ⑨ 作用域权限过滤器 $\rightarrow$ ⑩ Prompt 上下文拼接 $\rightarrow$ ⑪ 智谱 GLM-4-Flash LLM SSE 实时推流 $\rightarrow$ ⑫ SQLite 数据库持久化。
2. **底部核心路径摘要栏 (Bottom Summary Flow)**：
   - 带有图标的水平流程带：`文档解析` $\rightarrow$ `双路混合索引` $\rightarrow$ `指代消解` $\rightarrow$ `Cross-Rerank` $\rightarrow$ `流式 LLM 推送`。

---

## 风格二：现代 AI 大模型组件系统架构图 (Modern AI Agent System Architecture)

适合作为论文 **【第三章 系统总体架构设计】** 或 **【系统框图】** 使用。采用模块化圆角卡片、多源输入侧栏、中枢 RAG 引擎大框以及多彩输出控制区，极具现代 Top-Tier 大模型论文范儿。

![风格二：现代 AI 大模型组件系统架构图](C:\Users\meng\.gemini\antigravity\brain\2ee94b74-a197-4436-b728-f1a694229c05\rag_system_style2_1785052437195.jpg)

### 风格二手搓元件与排版布局指南：
1. **左侧多源输入栏 (Input & Sources Column)**：
   - 采用浅黄色圆角卡片，从上到下堆叠：
     - 🏢 **校规公文库**（12 大领域 Markdown 公文）
     - 💬 **用户口语化提问**（例如：“挂科会影响保研吗？”）
     - 🛡️ **身份作用域**（本科生 / 研究生 / 全校）
     - 🧠 **多轮历史会话**（Memory 缓存）
2. **中央 RAG 中枢引擎 (RAG Core Engine Box)**：
   - 采用亮橙色/金色高亮大圆角框，内部包含：
     - 🔍 **多轮指代消解器 (Anaphora Resolver)**
     - ⚡ **BM25 + Dense 双路混合检索**
     - 🎯 **Scope 规则过滤器**
     - 🚀 **Cross-Encoder 交叉重排序器 (Reranker)**
3. **右侧大模型推理与输出区 (LLM Inference & Output Column)**：
   - 采用蓝紫色渐变与浅蓝色容器：
     - 📝 **Prompt 结构化注入器**
     - 🤖 **智谱 AI GLM-4-Flash 大语言模型**
     - 🌊 **SSE 实时打字机流式推流**
     - 💾 **SQLite 数据库持久化落盘**

---

## 三、 手搓推荐矢量绘图工具与配色方案 (Drawing Tools & Color Codes)

建议在 Visio 或 Draw.io 中使用以下**正规学术配色方案**进行手搓：

| 元素板块 | Fill 色值 (填充色) | Stroke 色值 (边框色) | 适用于 |
| :--- | :--- | :--- | :--- |
| **数据与预处理** | `#F0F7FF` (浅蓝) | `#0284C7` (深蓝) | 阶段一 / 外部数据输入 |
| **核心算法与索引** | `#F0FDF4` (浅绿) | `#16A34A` (翠绿) | 阶段二 / RAG 中枢引擎 |
| **大模型与输出** | `#FFF7ED` (浅橙) | `#EA580C` (深橙) | 阶段三 / LLM 模块 |
| **大模型高亮组件** | `#FAF5FF` (淡紫) | `#7E22CE` (紫色) | GLM-4-Flash / Prompt |
