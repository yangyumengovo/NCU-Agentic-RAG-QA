"""检索后端三臂一键评测：v1 / v2 / v3 同口径对比。

口径与毕设 advanced_retrieval_tester.py 保持一致，保证数字可比：
- 命中判据：target_doc in doc_title 且 target_article 命中 article 或 chapter 字段；
- 指标：Hit@1 / Hit@3 / Hit@5 / MRR@3；
- 三条管线（召回通道 → 融合 → 重排）：
    v1: 字符TF-IDF Dense + 词频Sparse，alpha=0.6 加权 → LocalReranker 启发式重排
    v2: bge 语义 Dense + 词频Sparse，alpha=0.6 加权  → LocalReranker 启发式重排
    v3: FAISS Dense + BM25 Sparse，RRF(k=60) 融合   → bge-reranker-base 交叉编码器精排

用法：python -m agent.eval_retrieval
"""

import json
from datetime import date

from agent.config import DATA_DIR, VECTOR_STORE_PATH
from agent.embeddings import EMBEDDING_MODEL
from reranker import LocalReranker
from vector_store_builder import LocalVectorStore

TESTSET_PATH = DATA_DIR / "eval_dataset" / "ncu_qa_testset.json"
REPORT_PATH = DATA_DIR / "eval_dataset" / "stage2_hybrid_rrf_comparison.md"
TOP_K = 5


def first_hit_rank(chunks: list[dict], item: dict):
    """毕设判据 + 一处修复：目标条号可能是"第五条、第六条"（多条文），按、拆分后
    任一命中即算——原判据下这类题永远无法匹配单个切片的 article 字段，属指标缺陷。"""
    target_articles = [a.strip() for a in item["target_article"].split("、") if a.strip()]
    for rank, c in enumerate(chunks, 1):
        if item["target_doc"] not in c["doc_title"]:
            continue
        for ta in target_articles:
            if ta in c["article"] or ta in c["chapter"]:
                return rank
    return None


def make_pipeline(store, rerank_fn):
    """闭包一条完整管线：召回粗筛 Top10 → 重排取 TopK（与 agent 实际使用一致）。"""

    def search(query: str) -> list[dict]:
        candidates = store.hybrid_query(query, top_k=10, student_type="all", alpha=0.6)
        reranked = rerank_fn(query, candidates, top_k=TOP_K)
        return [item["chunk"] for item in reranked]

    return search


def build_arms():
    """按依赖可用性装配三臂（v3 依赖 faiss/jieba/rank_bm25/交叉编码器）。"""
    reranker = LocalReranker()
    arms = [
        ("v1 字符TF-IDF+启发式重排", LocalVectorStore.load(str(VECTOR_STORE_PATH)), reranker.rerank),
    ]
    try:
        from agent.retrieval_v2 import HybridStoreV2

        arms.append(("v2 bge语义+启发式重排", HybridStoreV2(), reranker.rerank))
    except Exception as e:
        print(f"[eval] v2 跳过: {e}")
    try:
        from agent import reranker_ce
        from agent.retrieval_v3 import HybridStoreV3

        arms.append(("v3 FAISS+BM25+RRF+交叉精排", HybridStoreV3(), reranker_ce.rerank))
    except Exception as e:
        print(f"[eval] v3 跳过: {e}")
    return arms


def evaluate(search_fn, cases) -> tuple[dict, list]:
    ranks = [first_hit_rank(search_fn(it["question"]), it) for it in cases]
    n = len(cases)
    metrics = {f"Hit@{k}": sum(r is not None and r <= k for r in ranks) / n for k in (1, 3, 5)}
    metrics["MRR@3"] = sum(1.0 / r for r in ranks if r is not None and r <= 3) / n
    return metrics, ranks


def main() -> None:
    with open(TESTSET_PATH, encoding="utf-8") as f:
        cases = json.load(f)

    print(f"评测集: {len(cases)} 题 | 管线: 召回粗筛Top10 → 重排Top{TOP_K} | 命中判据同毕设口径")
    arms = build_arms()

    results = []
    for name, store, rerank_fn in arms:
        print(f"评测 {name} ...")
        metrics, ranks = evaluate(make_pipeline(store, rerank_fn), cases)
        results.append((name, metrics, ranks))

    header = f"{'管线':<28} {'Hit@1':>7} {'Hit@3':>7} {'Hit@5':>7} {'MRR@3':>8}"
    print("\n" + header)
    print("-" * len(header))
    for name, m, _ in results:
        print(f"{name:<28} {m['Hit@1']:>7.1%} {m['Hit@3']:>7.1%} {m['Hit@5']:>7.1%} {m['MRR@3']:>8.4f}")

    # 逐题对比
    print("\n逐题排名对比（- 表示未命中）：")
    ids = [str(i) for i in range(1, len(cases) + 1)]
    title = f"{'id':>3} " + " ".join(f"{name.split()[0]:>4}" for name, _, _ in results)
    print(title)
    for q in range(len(cases)):
        row = f"{q + 1:>3} "
        for _, _, ranks in results:
            r = ranks[q]
            row += f"{'-' if r is None else r:>4} "
        print(row)

    # 导出 Markdown 报告
    md = f"""# 阶段 2 对照实验：高级 RAG 检索（双路召回 + RRF 融合 + 交叉编码器精排）

- 日期：{date.today()} | 评测集：{len(cases)} 题（毕设原版 ncu_qa_testset.json）
- 三臂唯一差异在检索管线本身，其余（切片、评测集、判据）完全一致
- Dense 模型：{EMBEDDING_MODEL}；精排模型：BAAI/bge-reranker-base（交叉编码器）

| 管线 | 召回 | 融合 | 重排 | Hit@1 | Hit@3 | Hit@5 | MRR@3 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
"""
    pipeline_desc = {
        "v1": ("TF-IDF Dense + 词频 Sparse", "alpha=0.6 加权", "LocalReranker 启发式"),
        "v2": ("bge 语义 Dense + 词频 Sparse", "alpha=0.6 加权", "LocalReranker 启发式"),
        "v3": ("FAISS Dense + BM25 Sparse", "RRF (k=60)", "bge-reranker-base 交叉编码器"),
    }
    for name, m, _ in results:
        key = name.split()[0]
        recall, fuse, rerank = pipeline_desc[key]
        md += (
            f"| **{name}** | {recall} | {fuse} | {rerank} | {m['Hit@1']:.1%} | "
            f"{m['Hit@3']:.1%} | {m['Hit@5']:.1%} | {m['MRR@3']:.4f} |\n"
        )

    md += "\n## 逐题排名（- 为未命中）\n\n| id | " + " | ".join(n.split()[0] for n, _, _ in results) + " |\n"
    md += "| :--- | " + " | ".join([":---"] * len(results)) + " |\n"
    for q in range(len(cases)):
        row = [str(q + 1)] + [
            "-" if (r := ranks[q]) is None else str(r) for _, _, ranks in results
        ]
        md += "| " + " | ".join(row) + " |\n"

    md += """
## 说明

- 判据在毕设口径基础上修复了一处缺陷：多条文目标（"第五条、第六条"）按、拆分后
  任一命中即计（原判据下此类题不可能命中）；三臂使用同一判据，对比仍然公平；
- v3 用 RRF 替代 alpha 加权：分数只来自两路排名（量纲无关），消除了需要扫描调优的超参；
- 交叉编码器精排只作用于融合后的 Top-10（CPU 上逐对打分，全量精排不现实）；
- FAISS IndexFlatIP 在 98 条切片下与暴力点积等价（精确检索），价值在于语料
  扩展到万级以上时换 IVF/HNSW 索引、上层代码零改动；
- 已知数据问题：题 4 的评测标注与切片内容存在错位（详见阶段 1 报告）；
  评测集仅 10 题，单题翻动即 ±10 个百分点，扩充评测集是下一步。
"""

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"\n报告已导出: {REPORT_PATH}")


if __name__ == "__main__":
    main()
