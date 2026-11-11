"""检索后端：懒加载、进程内单例，供多个工具共用。

支持 v1/v2 双后端切换（环境变量 RETRIEVAL_BACKEND，默认 auto）：
- v1: 毕设原版（字符 TF-IDF 假 Dense + 词频 Sparse），作为基线保留；
- v2: 真 Dense（bge 语义向量）+ 复用 v1 的 Sparse 通道，阶段 1 升级成果；
- auto: 存在 v2 向量库就用 v2，否则回落 v1（clone 后未重建时也能跑）。

设计要点：
- 懒加载：agent 启动时不加载（纯闲聊用不到检索），首次调用才加载索引；
- 进程内单例：向量库/重排器/切片 JSON 各只加载一次。
"""

import json
import os

from agent.config import CHUNKS_PATH, VECTOR_STORE_PATH
from agent.retrieval_v2 import NPZ_PATH


class _RetrievalBackend:
    def __init__(self):
        self._store = None
        self._reranker = None
        self._chunks = None

    @property
    def store(self):
        """v1 基线向量库（毕设原版）。"""
        if self._store is None:
            from vector_store_builder import LocalVectorStore  # scripts/ 已在 sys.path

            self._store = LocalVectorStore.load(str(VECTOR_STORE_PATH))
        return self._store

    @property
    def reranker(self):
        if self._reranker is None:
            from reranker import LocalReranker

            self._reranker = LocalReranker()
        return self._reranker

    @property
    def chunks(self):
        if self._chunks is None:
            with open(CHUNKS_PATH, encoding="utf-8") as f:
                self._chunks = json.load(f)
        return self._chunks


_backend = _RetrievalBackend()
_active_store = None


def _get_store():
    global _active_store
    if _active_store is None:
        mode = os.getenv("RETRIEVAL_BACKEND", "auto")
        if mode in ("auto", "v2") and NPZ_PATH.exists():
            from agent.retrieval_v2 import HybridStoreV2

            _active_store = HybridStoreV2()
        elif mode == "v2":
            raise RuntimeError(
                "RETRIEVAL_BACKEND=v2 但未构建 v2 向量库，请先运行: python -m agent.build_vector_store_v2"
            )
        else:
            _active_store = _backend.store  # v1 基线
    return _active_store


def hybrid_search(query: str, student_type: str = "all", top_k: int = 3) -> list[dict]:
    """混合检索 + 交叉重排（v1/v2 后端透明切换，返回结构一致）。

    返回按相关性降序的条文列表：
    [{"doc_title", "chapter", "article", "content", "score"}]
    """
    store = _get_store()
    candidates = store.hybrid_query(query, top_k=10, student_type=student_type)
    reranked = _backend.reranker.rerank(query, candidates, top_k=top_k)
    return [
        {
            "doc_title": item["chunk"]["doc_title"],
            "chapter": item["chunk"]["chapter"],
            "article": item["chunk"]["article"],
            "content": item["chunk"]["content"],
            "score": item["rerank_score"],
        }
        for item in reranked
    ]
