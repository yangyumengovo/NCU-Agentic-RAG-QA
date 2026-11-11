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

# 3. 运行（首次会自动下载 bge-small-zh-v1.5 模型 ~95MB，走 hf-mirror 镜像）
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
| `embeddings.py` | 真 embedding 后端：本地 bge-small-zh-v1.5（阶段 1） |
| `retrieval_v2.py` | v2 混合检索：真 Dense + 复用 v1 Sparse，接口与 v1 一致 |
| `build_vector_store_v2.py` | 构建 v2 向量库（98×512 维，`python -m agent.build_vector_store_v2`） |
| `eval_retrieval.py` | 一键评测：v1 vs v2 同口径对比 + alpha 扫描 + 失败分析 |
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

## 阶段 1 成果：真 embedding 升级（已完成）

旧版 `vector_store_builder.py` 的"Dense 密集特征"实为字符级 TF-IDF（词面匹配，
"挂科"永远匹配不到"不及格"）。阶段 1 换成本地 **bge-small-zh-v1.5**（512 维语义
向量，零 API 成本、可离线复现），Sparse 通道与重排器不动——v1→v2 的唯一变量是
Dense 通道，对比口径与毕设论文一致（`python -m agent.eval_retrieval` 重跑可复现）：

| 后端（同管线：混合 alpha=0.6 + 重排） | Hit@1 | Hit@3 | MRR@3 |
| :--- | :--- | :--- | :--- |
| v1 字符 TF-IDF Dense（基线） | 50.0% | 60.0% | 0.5500 |
| **v2 bge 语义 Dense** | **60.0%** | **70.0%** | **0.6333** |

- alpha 扫描（0.4~0.8）显示结论稳健：v2 各配置的 Hit@1/MRR 均不低于 v1 最优配置；
- 口语化问法收益最直观："挂科太多会被开除吗"这类与原文"不及格/退学"词面零重合的
  问题，v2 能直接召回正确条文；
- 完整报告（含逐题对比与失败分析）：`data/eval_dataset/stage1_embedding_comparison.md`。
  已知数据问题：题 4 的评测标注与切片内容错位（详见报告），且评测集仅 10 题，
  **扩充评测集到 30~50 题是可信度的关键下一步**。

### 环境变量

| 变量 | 默认 | 说明 |
| :--- | :--- | :--- |
| `RETRIEVAL_BACKEND` | `auto` | `auto`/`v2`/`v1`：检索后端切换（auto=有 v2 库就用 v2） |
| `EMBEDDING_MODEL` | `BAAI/bge-small-zh-v1.5` | 本地 embedding 模型，可换 bge-base/large 提精度 |

### 下一步（阶段 2+）

1. 扩充评测集（30~50 题，覆盖更多口语化问法与多文档问题）；
2. 把 `server/` 的 Java 桥接层与 `web/` 前端接回 agent（SSE 流式输出工具调用轨迹）；
3. 接入 Langfuse 自托管，记录每次工具调用轨迹，README 放 trace 截图；
4. 多步任务评测：构造"判断我能不能保研，不行的话转专业来不来得及"类任务集，
   量化 agent 的端到端任务成功率。
