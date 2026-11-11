"""v3 检索后端：FAISS（语义）+ BM25（关键词）双路召回，RRF 融合。

与 v1/v2 的本质区别：
1. 融合算法：v1/v2 用 alpha 加权融合两路分数——余弦与 TF-IDF 量纲不可比，
   alpha 是需要扫描调优的超参；v3 用 RRF（Reciprocal Rank Fusion）只看
   两路各自的排名，量纲无关，k=60 是标准值，无需调参。
2. 稀疏通道：v2 复用词频 TF-IDF 余弦；v3 换 BM25（词频饱和 + 文档长度
   归一），对"条款号/数字门槛"（GPA 2.5、800W、第十一条）这类精确词更稳健。

架构说明：98 条切片下 FAISS IndexFlatIP 与暴力点积等价（同为精确检索），
此处用 FAISS 主要是对齐工业标准栈、为语料扩展做准备——向量规模上万后
换 IVF/HNSW 索引时上层代码零改动。精排（交叉编码器）不在本模块，
由 _retrieval.hybrid_search 按后端选择，保持"store 只管召回融合"的分工。
"""

import json

import numpy as np

from agent.config import CHUNKS_PATH
from agent.embeddings import embed_query
from agent.retrieval_v2 import NPZ_PATH as V2_NPZ_PATH


def rrf_fuse(rank_lists: list[list[int]], k: int = 60) -> dict[int, float]:
    """RRF: score(d) = Σ_i 1/(k + rank_i(d))。k=60 为论文通用标准值。"""
    scores: dict[int, float] = {}
    for ranks in rank_lists:
        for pos, idx in enumerate(ranks, 1):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + pos)
    return scores


class HybridStoreV3:
    def __init__(self):
        with open(CHUNKS_PATH, encoding="utf-8") as f:
            self.chunks = json.load(f)

        # ---- Dense 通道：FAISS 精确内积索引（向量复用 v2 的 bge 编码产物）----
        import faiss

        npz = np.load(V2_NPZ_PATH, allow_pickle=False)
        vectors = npz["vectors"].astype(np.float32)
        if len(vectors) != len(self.chunks):
            raise RuntimeError("v2 向量库与切片数量不一致，请重跑 python -m agent.build_vector_store_v2")
        self._faiss = faiss.IndexFlatIP(vectors.shape[1])
        self._faiss.add(vectors)  # 向量已 L2 归一化，内积即余弦

        # ---- Sparse 通道：BM25（jieba 分词）----
        import jieba
        from rank_bm25 import BM25Okapi

        self._jieba = jieba
        corpus_tokens = [list(jieba.cut(c["full_chunk_text"])) for c in self.chunks]
        self._bm25 = BM25Okapi(corpus_tokens)

    def hybrid_query(self, query_text, top_k=10, student_type=None, category=None, **_):
        """双路召回（各取全量排序）→ RRF 融合 → 返回融合 Top-N 候选。

        返回结构与 v1/v2 一致（score/dense_rank/sparse_rank/chunk），
        score 为 RRF 分数，供上层统一处理。
        """
        # 作用域先过滤：两路在同一个候选池上排名，RRF 的排名才有可比性
        pool_idx = [
            i
            for i, c in enumerate(self.chunks)
            if (not student_type or student_type == "all" or c.get("student_type") in [student_type, "all"])
            and (not category or category == "all" or c.get("category") == category)
        ]
        if not pool_idx:
            return []
        pool_set = set(pool_idx)

        # Dense: FAISS 全库精确排序后投影到池内
        q_vec = np.asarray([embed_query(query_text)], dtype=np.float32)
        _, dense_rank_all = self._faiss.search(q_vec, len(self.chunks))
        dense_ranks = [i for i in dense_rank_all[0].tolist() if i in pool_set]

        # Sparse: BM25 池内打分排序
        bm25_scores = self._bm25.get_scores(list(self._jieba.cut(query_text)))
        sparse_ranks = sorted(pool_idx, key=lambda i: bm25_scores[i], reverse=True)

        fused = rrf_fuse([dense_ranks, sparse_ranks])
        ranked = sorted(fused.items(), key=lambda x: x[1], reverse=True)[:top_k]

        dense_pos = {i: p for p, i in enumerate(dense_ranks, 1)}
        sparse_pos = {i: p for p, i in enumerate(sparse_ranks, 1)}
        return [
            {
                "score": float(s),
                "dense_rank": dense_pos.get(i),
                "sparse_rank": sparse_pos.get(i),
                "chunk": self.chunks[i],
            }
            for i, s in ranked
        ]
