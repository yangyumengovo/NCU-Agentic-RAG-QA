# agent/ — LangGraph Agentic RAG 骨架

把毕设的**固定流水线 RAG** 重构为 **LLM 自主决策的工具调用循环（Agentic RAG）**。

## 与旧版的本质区别

```
旧版（scripts/rag_generator.py）：
  用户问题 → [正则意图路由] → [改写] → [检索] → [重排] → [生成]
              └────────── 顺序与分支全部写死在 Python 里 ──────────┘

新版（agent/）：
  用户问题 → LLM 决策 ──有工具调用──▶ 执行工具 ──结果回给 LLM──┐
                ▲                                            │
                └────────────── 继续决策 ◀───────────────────┘
                │
                └── 信息足够/无工具调用 ──▶ 输出最终回答
```

决策权从代码转移到模型：调不调工具、调哪个、调几次、结果不够怎么换关键词重试，
都由 LLM 根据对话上下文自己判断。`query_rewriter.py` 和 `conversation_memory.py`
的功能被自然吸收进这个循环——模型带着完整历史 formulate 工具参数时，指代消解是顺带完成的。

## 快速开始

```bash
# 1. 激活虚拟环境（已创建好）
.venv\Scripts\activate        # CMD/PowerShell
source .venv/Scripts/activate # Git Bash

# 2. 配置密钥（首次）
cp .env.example .env          # 然后编辑 .env 填入智谱 API Key

# 3. 先什么都不实现，直接跑通循环
python -m agent.main --ask "我绩点3.1有记过处分，能转专业吗"
python -m agent.main          # 交互模式
```

工具未实现时会返回占位 JSON，模型会如实告知"功能开发中"——
但你能看到它**决定调用哪个工具、传什么参数**，这就是要学习的 agent 行为。

## 目录结构

| 文件 | 职责 |
|---|---|
| `config.py` | 读 .env：LLM 参数 + 数据路径（key 不再硬编码进源码） |
| `prompts.py` | 系统提示词：告诉模型"自主决策"的工作方式与拒答边界 |
| `tools/_stub.py` | 未实现工具的占位返回，保证循环可端到端运行 |
| `tools/search_regulations.py` | 🔧 TODO：语义检索校规（复用混合检索+重排） |
| `tools/read_full_article.py` | 🔧 TODO：按文档+条号读完整条文（溯源） |
| `tools/check_rule.py` | 🔧 TODO：硬规则校验（复用 rule_engine） |
| `tools/compare_policies.py` | 🔧 TODO：跨文档政策对比（全新能力） |
| `tools/__init__.py` | 工具注册表 TOOLS（新增工具在此登记） |
| `graph.py` | StateGraph 组装：agent ⇄ tools 的 ReAct 循环 |
| `main.py` | CLI 入口，打印完整工具调用轨迹 |

## 你的 TODO（建议按此顺序）

| 顺序 | 工具 | 复用什么 | 难度 |
|---|---|---|---|
| 1 | `check_rule` | `rule_engine.py` 的 `evaluate_rules()`，3 行搞定 | ⭐ |
| 2 | `search_regulations` | `vector_store_builder.py` + `reranker.py` | ⭐⭐ |
| 3 | `read_full_article` | `data/processed_chunks/*.json` 的结构化字段 | ⭐⭐ |
| 4 | `compare_policies` | 复用 2 的检索逻辑，自己设计返回结构 | ⭐⭐⭐ |

每个工具文件里有带 `TODO(你来实现)` 标记的实现提示（import 什么、调什么、返回什么格式），
照着写即可；**每完成一个就 `git commit` 一次**，跑几组问题对比行为变化：

- 实现 1 之后：问"我 GPA 2.3 有记过能转专业吗"，观察模型把规则诊断与检索结果**组合**成结论；
- 实现 2 之后：问"挂科了还能转专业吗"（检索词面不匹配），观察模型**换关键词重检索**；
- 全部完成后：问"分析我能不能保研，不行的话转专业来不来得及"，观察**多步任务拆解**。

## 阶段 1 提醒（换真 embedding）

`vector_store_builder.py` 的"Dense 密集特征"是字符级 TF-IDF，不是语义向量。
等你把 `search_regulations` 跑通后，第一件事就是把 embedding 换成真模型
（智谱 embedding-3 或开源 bge-m3），并保留 Pickle 版做基线对比——这正是简历上
"混合检索 Hit@3 从 X 提升到 Y" 数据的来源。
