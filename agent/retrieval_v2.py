"""v2 混合检索：真 Dense（bge 语义向量）+ Sparse（复用旧 pickle 的词频通道）。

与 LocalVectorStore.hybrid_query 保持同签名、同返回结构（score/dense_score/
sparse_score/chunk），因此 reranker 和上层工具完全不用改——这就是
"接口不变、实现升级"的好处。
"""

import numpy as np

from agent.config import DATA_DIR, VECTOR_STORE_PATH
from agent.embeddings import embed_query

NPZ_PATH = DATA_DIR / "vector_store" / "ncu_regulations_embeddings_v2.npz"


class HybridStoreV2:
    def __init__(self):
        from sklearn.metrics.pairwise import cosine_similarity  # noqa: F401 (说明 sparse 通道依赖)
        from vector_store_builder import LocalVectorStore

        # 旧 pickle 提供：切片元数据 + Sparse 词频通道（保证专名/条款号精确命中）
        legacy = LocalVectorStore.load(str(VECTOR_STORE_PATH))
        self.chunks = legacy.chunks
        self.sparse_vectorizer = legacy.sparse_vectorizer
        self.sparse_vectors = legacy.sparse_vectors

        if not NPZ_PATH.exists():
            raise RuntimeError(
                f"未找到 v2 向量库 {NPZ_PATH.name}，请先运行: python -m agent.build_vector_store_v2"
            )
        npz = np.load(NPZ_PATH, allow_pickle=False)
        self.dense_vectors = npz["vectors"].astype(np.float32)  # 已 L2 归一化
        if len(self.dense_vectors) != len(self.chunks):
            raise RuntimeError("v2 向量库与切片数量不一致，请重跑 python -m agent.build_vector_store_v2")

    def hybrid_query(self, query_text, top_k=5, student_type=None, category=None, alpha=0.6):
        """混合打分：alpha * 语义余弦 + (1-alpha) * 词频余弦，alpha 默认 0.6（与 v1 相同）。"""
        q_dense = embed_query(query_text)
        dense_scores = self.dense_vectors @ q_dense  # 归一化后点积即余弦

        q_sparse = self.sparse_vectorizer.transform([query_text])
        from sklearn.metrics.pairwise import cosine_similarity

        sparse_scores = cosine_similarity(q_sparse, self.sparse_vectors)[0]

        hybrid_scores = alpha * dense_scores + (1 - alpha) * sparse_scores

        candidates = []
        for idx, chunk in enumerate(self.chunks):
            if student_type and student_type != "all":
                if chunk.get("student_type") not in [student_type, "all"]:
                    continue
            if category and category != "all":
                if chunk.get("category") != category:
                    continue
            candidates.append(
                {
                    "score": float(hybrid_scores[idx]),
                    "dense_score": float(dense_scores[idx]),
                    "sparse_score": float(sparse_scores[idx]),
                    "chunk": chunk,
                }
            )
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:top_k]
