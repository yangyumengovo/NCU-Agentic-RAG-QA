"""检索后端：懒加载毕设已有的向量库与重排器，供多个工具共用。

设计要点：
- 懒加载：agent 启动时不加载（纯闲聊用不到检索），首次调用才加载索引；
- 进程内单例：98 个切片的向量库/重排器/切片 JSON 各只加载一次，
  避免每次工具调用都重复 load——这是对旧版 rag_generator 每问一次
  就重新走一遍完整流程的改进。
"""

import json

from agent.config import CHUNKS_PATH, VECTOR_STORE_PATH


class _RetrievalBackend:
    def __init__(self):
        self._store = None
        self._reranker = None
        self._chunks = None

    @property
    def store(self):
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


def hybrid_search(query: str, student_type: str = "all", top_k: int = 3) -> list[dict]:
    """混合检索 + 交叉重排。

    复用毕设的两个模块：LocalVectorStore.hybrid_query（BM25+TF-IDF 双路混合、
    Scope 过滤）与 LocalReranker.rerank（标题/关键词加权重排）。

    返回按相关性降序的条文列表：
    [{"doc_title", "chapter", "article", "content", "score"}]
    """
    candidates = _backend.store.hybrid_query(query, top_k=10, student_type=student_type)
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
