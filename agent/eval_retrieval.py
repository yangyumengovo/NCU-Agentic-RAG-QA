"""阶段 1 一键评测：v1 假 Dense（字符TF-IDF） vs v2 真 Dense（bge）同口径对比。

口径与毕设 advanced_retrieval_tester.py 完全一致，保证数字可比：
- 检索管线：混合检索(alpha=0.6, 粗筛Top10) + LocalReranker 重排；
- 命中判据：target_doc in doc_title 且 target_article 命中 article 或 chapter 字段；
- 指标：Hit@1 / Hit@3 / Hit@5 / MRR@3。

用法：python -m agent.eval_retrieval
"""

import json
from datetime import date

from agent.config import DATA_DIR, VECTOR_STORE_PATH
from agent.embeddings import EMBEDDING_MODEL
from agent.retrieval_v2 import HybridStoreV2
from reranker import LocalReranker
from vector_store_builder import LocalVectorStore

TESTSET_PATH = DATA_DIR / "eval_dataset" / "ncu_qa_testset.json"
REPORT_PATH = DATA_DIR / "eval_dataset" / "stage1_embedding_comparison.md"
TOP_K = 5


def run_pipeline(store, reranker, query: str) -> list[dict]:
    """与 agent 实际使用的检索管线一致：混合粗筛 Top10 → 重排取 TopK。"""
    candidates = store.hybrid_query(query, top_k=10, student_type="all", alpha=0.6)
    reranked = reranker.rerank(query, candidates, top_k=TOP_K)
    return [item["chunk"] for item in reranked]


def first_hit_rank(chunks: list[dict], item: dict):
    for rank, c in enumerate(chunks, 1):
        if item["target_doc"] in c["doc_title"] and (
            item["target_article"] in c["article"] or item["target_article"] in c["chapter"]
        ):
            return rank
    return None


def evaluate(store, reranker, cases) -> tuple[dict, list]:
    ranks = [first_hit_rank(run_pipeline(store, reranker, it["question"]), it) for it in cases]
    n = len(cases)
    metrics = {f"Hit@{k}": sum(r is not None and r <= k for r in ranks) / n for k in (1, 3, 5)}
    metrics["MRR@3"] = sum(1.0 / r for r in ranks if r is not None and r <= 3) / n
    return metrics, ranks


def sweep_alpha(store, reranker, cases, alphas=(0.4, 0.5, 0.6, 0.7, 0.8)) -> list[dict]:
    """alpha（语义/词频权重）扫描：检验结论对超参的稳健性。"""
    rows = []
    for alpha in alphas:
        ranks = [
            first_hit_rank(
                [x["chunk"] for x in reranker.rerank(
                    it["question"],
                    store.hybrid_query(it["question"], top_k=10, student_type="all", alpha=alpha),
                    top_k=TOP_K,
                )],
                it,
            )
            for it in cases
        ]
        n = len(cases)
        rows.append(
            {
                "alpha": alpha,
                "Hit@1": sum(r is not None and r <= 1 for r in ranks) / n,
                "Hit@3": sum(r is not None and r <= 3 for r in ranks) / n,
                "MRR@3": sum(1.0 / r for r in ranks if r is not None and r <= 3) / n,
            }
        )
    return rows


def main() -> None:
    with open(TESTSET_PATH, encoding="utf-8") as f:
        cases = json.load(f)

    reranker = LocalReranker()
    print(f"评测集: {len(cases)} 题 | 管线: 混合检索(alpha=0.6, Top10) + 重排(Top{TOP_K})")
    print("加载 v1 基线库（字符TF-IDF Dense）...")
    v1_store = LocalVectorStore.load(str(VECTOR_STORE_PATH))
    print("加载 v2 升级库（bge 语义 Dense）...")
    v2_store = HybridStoreV2()

    v1_metrics, v1_ranks = evaluate(v1_store, reranker, cases)
    v2_metrics, v2_ranks = evaluate(v2_store, reranker, cases)

    print("\nalpha 权重扫描（稳健性检验）...")
    v1_sweep = sweep_alpha(v1_store, reranker, cases)
    v2_sweep = sweep_alpha(v2_store, reranker, cases)

    header = f"{'后端':<28} {'Hit@1':>8} {'Hit@3':>8} {'Hit@5':>8} {'MRR@3':>8}"
    print("\n" + header)
    print("-" * len(header))
    for name, m in (("v1 字符TF-IDF Dense（基线）", v1_metrics), ("v2 bge 语义 Dense", v2_metrics)):
        print(
            f"{name:<28} {m['Hit@1']:>7.1%} {m['Hit@3']:>8.1%} {m['Hit@5']:>8.1%} {m['MRR@3']:>8.4f}"
        )

    # 逐题对比：v2 改善/恶化/持平 的题一眼可见
    print("\n逐题排名对比（- 表示未命中）：")
    print(f"{'id':>3} {'v1':>4} {'v2':>4}  变化")
    for i, (r1, r2) in enumerate(zip(v1_ranks, v2_ranks), 1):
        f1 = "-" if r1 is None else r1
        f2 = "-" if r2 is None else r2
        arrow = "改善" if (r2 is not None and (r1 is None or r2 < r1)) else (
            "恶化" if (r1 is not None and (r2 is None or r1 < r2)) else "持平")
        print(f"{i:>3} {f1!s:>4} {f2!s:>4}  {arrow}")

    # 导出 Markdown 报告（可直接贴进 README / 简历附件）
    md = f"""# 阶段 1 对照实验：字符 TF-IDF "Dense" vs 真 bge 语义 Dense

- 日期：{date.today()} | 评测集：{len(cases)} 题（毕设原版 ncu_qa_testset.json）
- 管线（两臂完全一致，唯一变量为 Dense 通道）：混合检索(alpha=0.6, 粗筛Top10) + LocalReranker 重排
- v1 Dense：TfidfVectorizer(char_wb 2-4gram)；v2 Dense：{EMBEDDING_MODEL}（本地，512 维）

| 后端 | Hit@1 | Hit@3 | Hit@5 | MRR@3 |
| :--- | :--- | :--- | :--- | :--- |
| v1 字符TF-IDF Dense（基线） | {v1_metrics['Hit@1']:.1%} | {v1_metrics['Hit@3']:.1%} | {v1_metrics['Hit@5']:.1%} | {v1_metrics['MRR@3']:.4f} |
| **v2 bge 语义 Dense** | **{v2_metrics['Hit@1']:.1%}** | **{v2_metrics['Hit@3']:.1%}** | **{v2_metrics['Hit@5']:.1%}** | **{v2_metrics['MRR@3']:.4f}** |

## 逐题排名（- 为未命中）

| id | v1 排名 | v2 排名 | 变化 |
| :--- | :--- | :--- | :--- |
"""
    for i, (r1, r2) in enumerate(zip(v1_ranks, v2_ranks), 1):
        f1 = "-" if r1 is None else r1
        f2 = "-" if r2 is None else r2
        arrow = "改善" if (r2 is not None and (r1 is None or r2 < r1)) else (
            "恶化" if (r1 is not None and (r2 is None or r1 < r2)) else "持平")
        md += f"| {i} | {f1} | {f2} | {arrow} |\n"

    md += "\n## alpha 权重扫描（稳健性检验）\n\n| 后端 | alpha | Hit@1 | Hit@3 | MRR@3 |\n| :--- | :--- | :--- | :--- | :--- |\n"
    for rows, name in ((v1_sweep, "v1"), (v2_sweep, "v2")):
        for r in rows:
            md += f"| {name} | {r['alpha']} | {r['Hit@1']:.0%} | {r['Hit@3']:.0%} | {r['MRR@3']:.4f} |\n"

    md += """
## 已知数据问题（失败分析）

- 题 4（学位授予 GPA 最低要求）两后端表现均异常：评测集标注目标为《学士学位授予
  实施细则》第四条（GPA≥2.0），但切片数据中该"第四条"的实际内容是政治条件条款，
  标注与切片内容错位。v1 在字符串判据下的"命中"命中的是内容不匹配的条文（假阳性）；
  v2 的排序更符合语义但按判据不计命中。
- 评测集仅 10 题，单题翻动即 ±10 个百分点；扩充评测集是提升结论可信度的下一步。
"""

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"\n报告已导出: {REPORT_PATH}")


if __name__ == "__main__":
    main()
