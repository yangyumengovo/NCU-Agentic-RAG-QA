"""工具 1：校规语义检索（封装毕设已有的 混合检索 + 重排，经 _retrieval 共享后端复用）。"""

import json

from langchain_core.tools import tool

from agent.tools._retrieval import hybrid_search


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
    # 检索逻辑在 _retrieval.hybrid_search（懒加载向量库与重排器，进程内只加载一次）
    results = hybrid_search(query, student_type=student_type, top_k=top_k)
    if not results:
        # 给模型的"自纠错线索"：换关键词重试，而不是硬答
        return json.dumps(
            {"results": [], "hint": "未检索到相关条文，建议更换关键词后重试"},
            ensure_ascii=False,
        )
    return json.dumps({"results": results}, ensure_ascii=False)
