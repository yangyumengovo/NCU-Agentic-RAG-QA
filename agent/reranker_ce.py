"""交叉编码器精排（BAAI/bge-reranker-base）。

与 LocalReranker（关键词加权启发式）同接口、同输入输出结构，可直接替换：
输入 query + 候选列表，返回按相关性降序的 top_k。

区别于双塔 embedding（query 与文档各自独立编码再算相似度），交叉编码器把
(query, 文档) 拼在一起过模型，能看到词与词之间的交互——对"词面不同但语义
相关/无关"的判断远强于启发式规则。代价是必须逐对打分：模型 ~1.1GB，
CPU 上对 10 对约 1~2 秒，所以只用于对召回粗筛后的 Top-10 精排。
"""

import os

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

RERANKER_MODEL = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder

        _model = CrossEncoder(RERANKER_MODEL, max_length=512)
    return _model


def rerank(query: str, candidate_items: list[dict], top_k: int = 3) -> list[dict]:
    """candidate_items: [{"score": ..., "chunk": {...}}]（与 LocalReranker.rerank 一致）。

    返回 [{"rerank_score": sigmoid∈(0,1), "original_score": 召回阶段分数, "chunk": ...}]。
    """
    if not candidate_items:
        return []
    pairs = [(query, item["chunk"]["full_chunk_text"]) for item in candidate_items]
    scores = _get_model().predict(pairs)
    ranked = [
        {
            "rerank_score": round(float(s), 4),
            "original_score": item.get("score"),
            "chunk": item["chunk"],
        }
        for s, item in zip(scores, candidate_items)
    ]
    ranked.sort(key=lambda x: x["rerank_score"], reverse=True)
    return ranked[:top_k]
