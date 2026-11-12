"""检索管线多臂评测：v1/v2/v3 同口径对比，内置分层评测集（按题型分层出分）。

口径：
- 命中判据：任一 (target_doc, target_article) 目标对命中即算；目标条号支持
  "第五条、第六条" 多条文与多文档列表（v2 数据集特性）；
- 指标：Hit@1 / Hit@3 / Hit@5 / MRR@3；
- 拒答/对比题无检索目标，跳过（属 agent 级评测，后续接入）。

用法：
    python -m agent.eval_retrieval          # 内置分层评测集（45 道检索题，题型分层报表）
"""

import argparse
import json
from datetime import date
from pathlib import Path

from agent.config import DATA_DIR, VECTOR_STORE_PATH
from agent.embeddings import EMBEDDING_MODEL
from reranker import LocalReranker
from vector_store_builder import LocalVectorStore

TESTSET_PATH = DATA_DIR / "eval_dataset" / "ncu_qa_testset.json"
TOP_K = 5
RETRIEVAL_TYPES = ("direct", "paraphrase", "numeric", "combo")


def target_pairs(item: dict) -> list[tuple[str, str]]:
    docs = item["target_doc"]
    arts = item["target_article"]
    docs = docs if isinstance(docs, list) else [docs]
    arts = arts if isinstance(arts, list) else [arts]
    pairs = []
    for d, a in zip(docs, arts):
        for sub in str(a).split("、"):
            if sub.strip():
                pairs.append((d, sub.strip()))
    return pairs


def first_hit_rank(chunks: list[dict], item: dict):
    """任一目标对（文档+条号，条号支持、分隔的多条文）命中即返回排名。"""
    pairs = target_pairs(item)
    for rank, c in enumerate(chunks, 1):
        for d, a in pairs:
            if d in c["doc_title"] and (a in c["article"] or a in c["chapter"]):
                return rank
    return None


def make_pipeline(store, rerank_fn):
    def search(query: str) -> list[dict]:
        candidates = store.hybrid_query(query, top_k=10, student_type="all", alpha=0.6)
        reranked = rerank_fn(query, candidates, top_k=TOP_K)
        return [item["chunk"] for item in reranked]

    return search


def build_arms():
    reranker = LocalReranker()
    arms = [("v1 字符TF-IDF+启发式重排", LocalVectorStore.load(str(VECTOR_STORE_PATH)), reranker.rerank)]
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


def fmt(m: dict) -> str:
    return f"{m['Hit@3']:>5.0%}/{m['MRR@3']:.2f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--testset",
        default=str(TESTSET_PATH),
        help="评测集路径（默认内置分层集，可换自定义集）",
    )
    args = parser.parse_args()

    with open(args.testset, encoding="utf-8") as f:
        all_items = json.load(f)
    items = [it for it in all_items if it.get("review_status") != "已删除"]
    cases = [it for it in items if it.get("type") in RETRIEVAL_TYPES or "type" not in it]
    stratified = any("type" in it for it in cases)

    print(f"评测集: {Path(args.testset).name} | {len(cases)} 道检索题"
          f"（跳过 {len(items) - len(cases)} 道 agent 级题）| 管线: 召回Top10 → 重排Top{TOP_K}")
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

    by_type = {}
    if stratified:
        print("\n分层（Hit@3/MRR@3）：")
        print(f"{'题型':<12} " + " ".join(f"{n.split()[0]:>12}" for n, _, _ in results))
        for t in RETRIEVAL_TYPES:
            sub = [it for it in cases if it.get("type") == t]
            if not sub:
                continue
            row = f"{t:<12} "
            for name, store, rerank_fn in arms:
                m, _ = evaluate(make_pipeline(store, rerank_fn), sub)
                by_type.setdefault(t, {})[name.split()[0]] = m
                row += f"{fmt(m):>12} "
            print(row + f"  ({len(sub)} 题)")

    report_path = DATA_DIR / "eval_dataset" / f"{Path(args.testset).stem}_retrieval_report.md"
    md = f"""# 检索多臂评测报告（{Path(args.testset).name}）

- 日期：{date.today()} | 检索题 {len(cases)} 道（跳过 agent 级 {len(items) - len(cases)} 道）
- Dense: {EMBEDDING_MODEL} | 精排: BAAI/bge-reranker-base | 判据: 多目标对命中（条号支持、分隔）

| 管线 | Hit@1 | Hit@3 | Hit@5 | MRR@3 |
| :--- | :--- | :--- | :--- | :--- |
"""
    for name, m, _ in results:
        md += f"| {name} | {m['Hit@1']:.1%} | {m['Hit@3']:.1%} | {m['Hit@5']:.1%} | {m['MRR@3']:.4f} |\n"
    if by_type:
        md += "\n| 题型 | " + " | ".join(f"{n.split()[0]} Hit@3/MRR@3" for n, _, _ in results) + " |\n"
        md += "| :--- | " + " | ".join([":---"] * len(results)) + " |\n"
        for t, arm_metrics in by_type.items():
            md += f"| {t} | " + " | ".join(f"{fmt(m)}" for m in arm_metrics.values()) + " |\n"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"\n报告已导出: {report_path}")


if __name__ == "__main__":
    main()
