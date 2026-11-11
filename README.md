# 基于 RAG 的高校制度文档智能问答系统
### Nanchang University Campus Regulation RAG Q&A System

![Python Version](https://img.shields.io/badge/Python-3.10-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![Vue.js](https://img.shields.io/badge/Vue.js-3.0-brightgreen.svg)
![LLM](https://img.shields.io/badge/LLM-GLM--4--Flash%20%7C%20DeepSeek-purple.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

本项目为**本科毕业设计课题成果**，是一套专为高校（以南昌大学为例）设计的基于**检索增强生成（Retrieval-Augmented Generation, RAG）**的规章制度智能问答系统。针对传统校规查询检索慢、口语化匹配差、缺乏多轮对话记忆等痛点，实现了从结构化公文解析、双路混合检索、 Cross-Rerank 重排序、多轮指代消解到 SSE 实时流式打字推送的全栈解决方案。

---

## 🌟 核心特性 (Key Features)

1. 📖 **12 大领域公文与结构感知切片 (Structure-Aware Chunking)**
   - 覆盖学籍、学位、奖学金、处分、保研、转专业、课程考核、宿舍管理、学术不端、考勤请假、国家奖学金及申诉处理等 12 大权威发文。
   - 正则提取“章-节-条”与 Scope 身份标记（`student_type`, `category`），生成 98 个高密度结构化切片，彻底避免传统切片语义断裂。

2. ⚡ **双路混合检索与 Cross-Rerank 重排序 (Hybrid Retrieval & Reranker)**
   - **BM25 稀疏特征**（擅长专有名词） + **TF-IDF Dense 密集特征**（擅长同义表达）加权融合（$\alpha = 0.6$）。
   - 引入交叉重排序器（Local Cross-Encoder）实施二次粗精排，显著提升召回率（Hit Rate@3）与相关度（MRR@3）。

3. 🧠 **多轮指代消解与双路意图路由 (Coreference & Router)**
   - 维护 `ConversationMemoryManager` 会话历史栈，自动补全追问中的模糊代词（如“它”、“这个”）。
   - 意图路由器自动分流政策检索通道与通用问候通道。

4. 📊 **结构化硬规则诊断引擎 (Rule-Guided Validator)**
   - 内置校规硬规则逻辑算符。当提问包含 `GPA` 绩点、`处分`、`查重率`、`违禁功率` 等参数时，自动在回答头部优先高亮生成**结构化诊断报告卡片**。

5. 🛡️ **防幻觉与据答安全机制 (Hallucination Prevention Guard)**
   - 结合异构词汇拦截与底层相关度阈值判定。当遇到超纲或与校规无关的提问时，主动拒答并给出权威安全提示。

6. 🎨 **官方品牌 VI 视觉与 SSE 流式打字推送 (Official VI & SSE Streaming)**
   - 前端采用 Vue3 结合 2022 版南昌大学官方品牌 VI 标准色（昌大青蓝 `#12368F`）。
   - FastAPI 后端配合 Server-Sent Events (SSE) 实现实时打字机光标效果。
   - SQLite 数据库自动实现首句提问提取会话标题、历史记录及用户点赞/点踩反馈落盘。

---

## 📁 目录结构 (Repository Architecture)

```
code/
├── data/                             # 统一数据与数据库存储
│   ├── raw_documents/                # 12 份南昌大学官方规章制度 Markdown 原文
│   ├── processed_chunks/             # 98 个带 Scope Metadata 结构化切片 JSON
│   ├── vector_store/                 # Dense + BM25 混合向量数据库序列化文件
│   ├── eval_dataset/                 # Ground Truth 评测集与对比实验报告
│   └── ncu_rag_history.db            # SQLite 会话与反馈落盘数据库
├── scripts/                          # 核心算法与离线数据处理模块
│   ├── structure_chunker.py          # 结构感知切片解析器
│   ├── vector_store_builder.py       # 混合索引构建器
│   ├── query_rewriter.py             # Query 改写与扩充模块
│   ├── reranker.py                   # Local Cross-Encoder 重排序器
│   ├── conversation_memory.py        # 多轮对话记忆与指代消解
│   ├── rule_engine.py                # 结构化硬规则诊断引擎
│   └── rag_generator.py              # 核心 RAG 生成与流式推流引擎
├── server/                           # API 接口服务端
│   └── app_rag_service.py            # FastAPI 异步高并发 HTTP/SSE 接口
└── web/                              # 前端 UI
    ├── index.html                    # 昌大官方 VI 视觉 Vue3 问答界面
    └── *.png                         # 2022 版南昌大学官方 Logo 素材
```

---

## 🚀 快速开始 (Quick Start)

### 1. 环境准备 (Environment Setup)

建议使用 Conda 创建独立的 Python 3.10 虚拟环境：

```bash
# 1. 创建并激活 Python 3.10 环境
conda create -n ncu_rag python=3.10 -y
conda activate ncu_rag

# 2. 安装依赖包
pip install fastapi uvicorn openai sklearn numpy requests pydantic
```

### 2. 离线构建向量库 (Build Vector Store)

运行切片工程与混合向量库构建脚本：

```bash
# 结构化解析 12 份 Markdown 文档
python code/scripts/structure_chunker.py

# 构建 Dense + BM25 混合向量索引
python code/scripts/vector_store_builder.py
```

### 3. 启动 FastAPI 服务端 (Start Backend Server)

启动 AI 问答 API 服务（默认运行于 `http://127.0.0.1:8000`）：

```bash
python code/server/app_rag_service.py
```

### 4. 体验前端问答 (Access Web UI)

在浏览器中直接打开 `code/web/index.html` 即可体验实时打字流问答！

---

## 📊 系统总体架构 (System Architecture)

```
[ 用户交互层 ] ─── Vue3 前端 (昌大青蓝 VI) + Scope 过滤器 + SSE 流式推流
       │
[ 接口控制层 ] ─── FastAPI REST/SSE 接口 (Port 8000) + SQLite 历史/评分落盘
       │
[ RAG 算法层 ] ─── 意图路由 -> 指代消解 -> Query改写 -> 混合检索(BM25+Dense) -> Scope过滤 -> Cross-Reranker
       │
[ 模型推理层 ] ─── Prompt 结构化注入 + 智谱 AI GLM-4-Flash / OpenAI 兼容基类
       │
[ 数据存储层 ] ─── 12 大领域 Markdown 公文 + 98 结构化切片 + Pickle 向量库
```

---

## 📝 毕业论文对应与参考 (Thesis References)

- 架构图说明：详见 [system_architecture.md](code/data/eval_dataset/system_architecture.md)
- 对比实验数据：详见 [advanced_retrieval_comparison.md](code/data/eval_dataset/advanced_retrieval_comparison.md)
- 毕业论文初稿：详见 [毕业论文初稿_基于RAG的高校制度文档智能问答系统.md](毕业论文初稿_基于RAG的高校制度文档智能问答系统.md)

---

## 📄 开源协议 (License)

本项目基于 [MIT License](LICENSE) 协议开源。欢迎学术交流与二次开发！
