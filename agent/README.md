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
| `retrieval_v3.py` | v3 检索：FAISS Dense + BM25 双路召回 → RRF 融合（阶段 2） |
| `reranker_ce.py` | bge-reranker-base 交叉编码器精排（与 LocalReranker 同接口可替换） |
| `build_vector_store_v2.py` | 构建 v2 向量库（98×512 维，`python -m agent.build_vector_store_v2`） |
| `eval_retrieval.py` | 一键评测：多臂对比 + 题型分层报表（`--testset` 可选数据集） |
| `draft_eval_dataset.py` | 分层评测集 v2 起草器（53 题：12文档全覆盖 × 4检索题型 + 拒答/对比） |
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
| `RETRIEVAL_BACKEND` | `auto` | `auto`/`v3`/`v2`/`v1`：检索管线切换（auto=v3→v2→v1 逐级降级） |
| `EMBEDDING_MODEL` | `BAAI/bge-small-zh-v1.5` | 双塔语义模型（召回用） |
| `RERANKER_MODEL` | `BAAI/bge-reranker-base` | 交叉编码器模型（精排用，可换 small 版省内存） |

## 阶段 2 成果：高级 RAG 检索（已完成）

v3 管线：**FAISS（bge 语义向量）+ BM25（jieba 分词）双路召回 → RRF(k=60) 融合
Top-10 → bge-reranker-base 交叉编码器精排 → Top-3**。相对 v1/v2 的两个本质改进：

1. **RRF 替代 alpha 加权融合**：余弦与 TF-IDF 分数量纲不可比，alpha 是需要扫描
   调优的超参；RRF 只看两路排名，量纲无关、免调参；
2. **交叉编码器替代启发式重排**：LocalReranker 靠关键词加权规则，交叉编码器让
   query 与文档联合建模，语义判断能力不同量级。

三臂同口径对比（`python -m agent.eval_retrieval` 重跑可复现；判据在毕设口径上
修复了多条文目标无法匹配的缺陷，三臂同判据）：

| 管线 | 召回 | 融合 | 重排 | Hit@1 | Hit@3 | MRR@3 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| v1 | TF-IDF + 词频 | alpha 加权 | 启发式 | 70.0% | 80.0% | 0.7500 |
| v2 | bge + 词频 | alpha 加权 | 启发式 | 80.0% | 90.0% | 0.8333 |
| **v3** | **FAISS + BM25** | **RRF** | **交叉编码器** | **80.0%** | **100.0%** | **0.9000** |

- v3 全部 10 题命中进 Top-2（仅 q10 第 2、q4 第 2）；阶段 1 中数据错位的 q4
  被交叉编码器救回到第 2 名；
- 诚实的工程判断：98 条切片下 FAISS IndexFlatIP 与暴力点积等价（同为精确检索），
  此处用 FAISS 是对齐工业栈、为语料上万后换 IVF/HNSW 留好接口；
- 完整报告：`data/eval_dataset/stage2_hybrid_rrf_comparison.md`。

### 下一步（阶段 3+）

1. **分层评测集 v2 审核定稿**（起草稿已生成，见下）；
2. 把 `server/` 的 Java 桥接层与 `web/` 前端接回 agent（SSE 流式输出工具调用轨迹）；
3. 接入 Langfuse 自托管，记录每次工具调用轨迹，README 放 trace 截图；
4. agent 级评测：拒答题（误答率）与多步任务题（端到端任务成功率）的自动评测脚本。

## 分层评测集 v2（待人工审核）

`python -m agent.draft_eval_dataset` 生成 53 题（12/12 文档全覆盖）：
直检 16 / 改述 16 / 数字 10 / 组合 3（计入检索指标）+ 拒答 5 / 对比 3（agent 级，暂不计入）。

**审核流程**（约 1~2 小时，无需校规知识）：对照
`data/eval_dataset/ncu_qa_testset_v2_review.md`（每题附来源原文）逐题检查
①问题是否自然 ②改述题是否真的换了口语用词 ③答案是否在原文里，
然后把 JSON 里对应条目的 `review_status` 改为 已确认 / 直接改写 question / 已删除。

审核前后都能跑分层评测（只跳过标记为"已删除"的条目）：

```bash
python -m agent.eval_retrieval --testset data/eval_dataset/ncu_qa_testset_v2.json
```

审核定稿后（46 确认 + 8 处人工口语化改写，改写使 v1 基线显著变难、v3 指标不变，
区分度提升），正式数据（45 检索题）：

| 管线 | Hit@1 | Hit@3 | Hit@5 | MRR@3 |
| :--- | :--- | :--- | :--- | :--- |
| v1 字符TF-IDF+启发式 | 66.7% | 86.7% | 93.3% | 0.7593 |
| v2 bge+启发式 | 77.8% | 95.6% | 97.8% | 0.8667 |
| **v3 FAISS+BM25+RRF+交叉精排** | **88.9%** | **100.0%** | **100.0%** | **0.9370** |

分层（Hit@3）：direct 81%→100%、paraphrase 81%→100%、numeric 与 combo 已饱和（v1 也 100%）。
已知局限：numeric/combo 两层偏易，后续可补更难的数字陷阱题。
