"""工具 1：校规语义检索（封装毕设已有的 混合检索 + 重排）。"""

import json

from langchain_core.tools import tool

from agent.config import VECTOR_STORE_PATH
from agent.tools._stub import not_implemented


@tool
def search_regulations(
    query: str, student_type: str = "undergraduate", top_k: int = 3
) -> str:
    """在南昌大学规章制度库（12 份公文、98 个结构化切片）中检索与 query 最相关的条文片段。

    何时使用：任何涉及校规政策内容的问题，回答前都必须先调用本工具检索；
    检索结果不相关时可更换关键词再次调用（最多 2 次）。

    Args:
        query: 检索问题或关键词，如 "转专业的申请条件"、"学位授予的绩点要求"。
        student_type: 作用域过滤，可选 "undergraduate"（本科生，默认）、"postgraduate"、"all"。
        top_k: 返回的最相关条文数量，默认 3。
    """
    # ==================== TODO(你来实现) ====================
    # 实现提示（完成后删除本注释块）：
    #
    #   from vector_store_builder import LocalVectorStore   # scripts/ 已在 sys.path
    #   from reranker import LocalReranker
    #
    #   # 建议在模块级只加载一次（98 个切片加载很快，但没必要每次调用都做）：
    #   _store = LocalVectorStore.load(str(VECTOR_STORE_PATH))
    #   _reranker = LocalReranker()
    #
    #   candidates = _store.hybrid_query(query, top_k=10, student_type=student_type)
    #   results = _reranker.rerank(query, candidates, top_k=top_k)
    #   # results 是 [{"rerank_score": float, "chunk": {...}}, ...]
    #
    #   组装返回值（JSON 字符串，模型直接阅读）：
    #   return json.dumps([
    #       {
    #           "doc_title": item["chunk"]["doc_title"],
    #           "chapter":   item["chunk"]["chapter"],
    #           "article":   item["chunk"]["article"],
    #           "content":   item["chunk"]["content"],
    #           "score":     item["rerank_score"],
    #       } for item in results
    #   ], ensure_ascii=False)
    # ==========================================================
    return not_implemented("search_regulations")
