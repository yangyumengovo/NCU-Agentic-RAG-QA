# NCU 校规智能问答 · Agentic RAG

> 南昌大学规章制度智能问答系统：由固定流水线 RAG 重构为 **LangGraph Agent** 驱动的
> Agentic RAG——LLM 自主决策调用校规检索、硬规则校验、条文溯源等工具，检索层历经
> v1→v2→v3 三代演进（FAISS+BM25 双路召回 + RRF 融合 + 交叉编码器精排），全部实验
> 结果可由脚本一键复现。

## 架构

```
毕设原版（固定流水线）                          当前版本（Agentic RAG）
─────────────────────────                      ─────────────────────────────
用户问题 → [正则意图路由]                       用户问题 → LLM 决策 ──有工具调用──▶ 执行工具 ──┐
        → [规则改写]                                        ▲                        │
        → [检索]                                            └──── 继续决策 ◀────────┘
        → [重排]                                            │
        → [生成]                                            └── 信息足够 ──▶ 最终回答
  （顺序与分支全部写死在 Python 里）              （调什么工具、调几次、何时停止由模型决定）

web/index.html (Vue3) ──SSE(工具轨迹+流式)──▶ agent/api_service.py (:8000)
                                                 └─ LangGraph ReAct 循环（graph.py）
                                                       ├─ search_regulations  校规语义检索
                                                       ├─ read_full_article   条文溯源
                                                       ├─ check_rule          硬规则校验
                                                       └─ compare_policies    跨文档政策对比
                                                       └─ 检索层 v1/v2/v3 可切换（_retrieval.py）
```

## 快速开始

```bash
# 1. 环境（Python 3.10+）
python -m venv .venv
.venv\Scripts\activate                    # Windows；Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt           # 走清华镜像可加 -i https://pypi.tuna.tsinghua.edu.cn/simple

# 2. 密钥：复制 .env.example 为 .env，填入智谱开放平台 API Key
#    （glm-4-flash 免费；套餐 key 见 .env 内注释切换 coding 端点 + glm-5.3）

# 3. 运行（首次自动从 hf-mirror 下载本地模型：bge-small-zh-v1.5 ~95MB + bge-reranker-base ~1.1GB）
python -m agent.main                      # CLI 问答（打印完整工具调用轨迹）
python -m agent.main --ask "我绩点3.1有记过处分，能转专业吗"

# 4. Web Demo（两个终端）
python -m agent.api_service               # AI 服务 :8000
cd web && python -m http.server 8080      # 前端静态服务
# 浏览器打开 http://127.0.0.1:8080/index.html
```

## 目录结构

```
agent/                     核心包：LangGraph Agent + 检索演进 + 评测 + API 服务
├── graph.py               ReAct 循环组装（agent ⇄ tools，可注入假模型做离线测试）
├── prompts.py             系统提示词（自主决策/检索重试/引用出处/拒答边界）
├── main.py                CLI 入口（工具调用轨迹打印）
├── api_service.py         FastAPI 服务：SSE 流式 + 工具轨迹事件，会话 SQLite 落盘
├── tools/                 四个工具 + 共享检索后端 _retrieval.py（v1/v2/v3 管线切换）
├── embeddings.py          本地 bge-small-zh-v1.5 语义编码（懒加载）
├── retrieval_v2.py        v2 检索：真 Dense + 复用 v1 Sparse，alpha 加权
├── retrieval_v3.py        v3 检索：FAISS Dense + BM25 双路召回 → RRF(k=60) 融合
├── reranker_ce.py         bge-reranker-base 交叉编码器精排
├── build_vector_store_v2.py   构建 v2 语义向量库（98×512）
├── eval_retrieval.py      检索多臂评测（--testset 可选数据集，题型分层报表）
└── eval_refusal.py        拒答评测（跑完整 agent，规则+LLM 裁判双判）
scripts/                   毕设组件（v1 基线 + 被 v2/v3 复用的部分）
├── structure_chunker.py   原始公文 → 章-节-条结构化切片（含 Scope 元数据）
├── vector_store_builder.py    v1 向量库（字符 TF-IDF Dense + 词频 Sparse）
├── reranker.py            LocalReranker 启发式重排（v1/v2 臂使用）
├── rule_engine.py         硬规则校验引擎（check_rule 工具封装）
└── db_manager.py          SQLite 会话/反馈落盘
data/
├── raw_documents/         12 份校规公文（Markdown）
├── processed_chunks/      98 个结构化切片
├── vector_store/          v1 pickle + v2 npz 向量库
└── eval_dataset/          ncu_qa_testset.json（分层 68 题：45 检索 + 20 拒答 + 3 对比）
web/                       Vue3 前端（工具调用轨迹面板 + 流式打字机 + 出处卡片）
```

## 检索管线演进与实验复现

| 版本 | 召回通道 | 融合 | 重排 | 一句话说明 |
| :--- | :--- | :--- | :--- | :--- |
| v1 | 字符TF-IDF"伪Dense" + 词频Sparse | alpha 加权 | 启发式关键词加权 | 毕设原版（词面匹配，"挂科"匹配不到"不及格"） |
| v2 | bge-small-zh-v1.5 真语义 Dense + v1 Sparse | alpha 加权 | 启发式 | 真语义向量引入 |
| v3 | **FAISS Dense + BM25(jieba)** | **RRF (k=60)** | **bge-reranker-base 交叉编码器** | 量纲无关融合 + 神经精排 |

**从零复现全部实验**（语料变动后需要时再跑①②③；评测随跑随出）：

```bash
python scripts/structure_chunker.py        # ① 原始公文 → 切片（仓库已含产物）
python scripts/vector_store_builder.py     # ② 构建 v1 向量库（pickle）
python -m agent.build_vector_store_v2      # ③ 构建 v2 语义向量库（npz）
python -m agent.eval_retrieval             # ④ 三臂评测（45 道检索题，题型分层报表）
python -m agent.eval_refusal               # ⑤ 拒答评测（20 题，跑完整 agent）
```

**核心结果**（分层 45 题人工审核定稿集，同判据同管线，唯一变量为检索层）：

| 管线 | Hit@1 | Hit@3 | Hit@5 | MRR@3 |
| :--- | :--- | :--- | :--- | :--- |
| v1 字符TF-IDF + 启发式重排 | 66.7% | 86.7% | 93.3% | 0.7593 |
| v2 bge 语义 + 启发式重排 | 77.8% | 95.6% | 97.8% | 0.8667 |
| **v3 FAISS+BM25 + RRF + 交叉精排** | **88.9%** | **100.0%** | **100.0%** | **0.9370** |

分层视角：区分度主要来自 direct/paraphrase 两层（Hit@3 均 81%→100%）；
numeric/combo 层已饱和（v1 也 100%，属评测集已知局限）。

## 防幻觉拒答评测（20 题 · 三层子类型）

| 子类型 | 题数 | 严格拒答正确率 | 行为 |
| :--- | :--- | :--- | :--- |
| 完全无关 | 8 | **100%** | 零工具调用直接拒答 |
| 校园相关但库外 | 7 | **85.7%** | 检索 2~3 次确认无果后拒答 |
| 语料内主题无答案 | 5 | 20%（严格口径） | 边界式回答（见归因） |
| **总体** | 20 | **75.0%** | |

失败样本人工归因：**0 例真幻觉**（无编造条文/数字）——1 例为 LLM 裁判误判，
4 例为"给出库内确有信息 + 明确标注所问细节未规定"的边界式回答。评测采用
规则 + 独立 LLM 裁判双判，判定不一致的样本单独标记，恰好圈出全部边界案例。

## Agent 行为（端到端验证过）

- **规则+检索组合**："我绩点3.1有记过处分能转专业吗" → 并行调用 check_rule +
  search_regulations，输出逐条对照表（GPA 3.1 vs 门槛 2.5）并给出处；
- **自适应补检索**：检索结果不充分时自主换关键词重查（对比题场景追加过 2 次精确检索）；
- **口语改写**：把"挂科太多会被开除吗"改写为规范检索词"不及格 退学 开除学籍"；
- **零浪费拒答**：无关问题不调用任何工具直接拒答；
- **多工具链式**：检索 → 主动读整条原文 → 追查关联条文 → 汇总结论。

## 设计决策与已知简化（诚实声明）

- **FAISS 在 98 条切片下与暴力点积等价**（同为精确检索），采用它是为对齐工业栈、
  语料上万后可平滑换 IVF/HNSW 而上层零改动；
- **RRF 取代 alpha 加权**的原因：余弦与 TF-IDF 分数量纲不可比，alpha 是需扫描调优
  的超参，RRF 只看排名、免调参；
- 评测判据在毕设口径上修复了**多条文目标无法命中**的缺陷（"第五条、第六条"按、
  拆分任一命中），并在报告中注明；
- 多轮会话为简化实现：保存问答文本对，不回放中间工具消息（agent 每轮重新自主决策）；
- LLM 调用层暂无重试/降级；`.env` 中的 API Key 严禁提交（历史泄露 key 已作废）。

## 路线图

- [ ] 对比题（3 道）的 agent 级评测：多跳召回 + 综合推理判定
- [ ] LLM 调用容错（重试/降级）与检索置信度闸门（v3 精排分数阈值化）
- [ ] Langfuse 自托管调用追踪
- [ ] 评测集 numeric/combo 层补充"数字陷阱"题（当前已饱和）

## 致谢

基于本人本科毕业设计《基于 RAG 的高校制度文档智能问答系统》重构演进；
语料为南昌大学 12 份现行规章制度公文。
