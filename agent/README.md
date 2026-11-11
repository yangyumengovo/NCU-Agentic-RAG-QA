# agent/ — LangGraph Agentic RAG

把毕设的**固定流水线 RAG** 重构为 **LLM 自主决策的工具调用循环（Agentic RAG）**。
四个工具已全部实现并通过端到端验证。

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

# 2. 配置密钥（首次）：复制 .env.example 为 .env 并填入智谱 API Key
#    套餐 key 用 coding 端点 + glm-5.3；免费 key 用通用端点 + glm-4-flash（.env 里有注释说明）

# 3. 运行
python -m agent.main --ask "我绩点3.1有记过处分，能转专业吗"
python -m agent.main          # 交互模式
```

## 目录结构

| 文件 | 职责 |
|---|---|
| `config.py` | 读 .env：LLM 参数 + 数据路径（key 不再硬编码进源码） |
| `prompts.py` | 系统提示词：告诉模型"自主决策"的工作方式与拒答边界 |
| `tools/_retrieval.py` | 检索共享后端：懒加载向量库/重排器/切片（进程内单例），供多工具复用 |
| `tools/search_regulations.py` | ✅ 混合检索+重排（复用毕设 `vector_store_builder` + `reranker`） |
| `tools/read_full_article.py` | ✅ 按文档+条号读完整条文（条号归一化 + 模糊匹配，用于溯源） |
| `tools/check_rule.py` | ✅ 硬规则校验（复用毕设 `rule_engine`） |
| `tools/compare_policies.py` | ✅ 跨文档政策对比（工具取数，对比推理由模型完成） |
| `tools/__init__.py` | 工具注册表 TOOLS（新增工具在此登记） |
| `graph.py` | StateGraph 组装：agent ⇄ tools 的 ReAct 循环（可注入假模型做离线测试） |
| `main.py` | CLI 入口，打印完整工具调用轨迹 |

## 已验证的 agent 行为（写简历/README 时可引用）

- **规则+检索组合**："我绩点3.1有记过处分能转专业吗" → 并行调用 `check_rule` +
  `search_regulations`，输出逐条对照表（GPA 3.1 vs 门槛 2.5）并给出处；
- **自适应补检索**：对比类问题在 `compare_policies` 返回流程类条文后，模型主动
  追加两次更精确的关键词检索（"绩点要求"、"综合排名 英语要求"）；
- **零浪费拒答**：超纲问题（食堂哪个窗口好吃）不调用任何工具，直接礼貌拒答。

## 踩坑记录（实现这四个工具时真实踩过的坑）

1. **import 拼写**：`from remarker import ...`（应为 `reranker`）——模块级 import
   错误会让整个 agent 启动崩溃，且报错栈很长，第一时间看最底部的 ImportError；
2. **共享函数要先建**：`compare_policies` 引用了尚未存在的 `_do_search`——正确做法
   是把检索逻辑抽到 `_retrieval.hybrid_search`，多个工具共用，绝不复制粘贴；
3. **子串匹配的假阳性**：条号"七"能匹配"第十七条/第二十七条"——匹配必须带上下文
   （"第七条"整体匹配），这类边界在 RAG 溯源场景是高频 bug。

## 阶段 1 提醒（下一步：换真 embedding）

`vector_store_builder.py` 的"Dense 密集特征"是字符级 TF-IDF，不是语义向量。
工具跑通后的第一件事就是把 embedding 换成真模型（智谱 embedding-3 或开源 bge-m3），
保留 TF-IDF 版做基线，用 `data/eval_dataset/ncu_qa_testset.json` 跑
Hit@K / MRR 对比——这就是简历上"混合检索 Hit@3 从 X 提升到 Y"的数据来源。
