"""工具 2：读取某条校规的完整原文（按文档 + 条号精确定位，用于溯源）。"""

from langchain_core.tools import tool

from agent.config import CHUNKS_PATH
from agent.tools._stub import not_implemented


@tool
def read_full_article(document_title: str, article: str) -> str:
    """读取指定校规文件中某一条的完整原文。当检索到的片段被截断、需要确认完整条款细节时使用。

    何时使用：search_regulations 返回的片段不够完整，或需要向用户展示某条的准确原文时。

    Args:
        document_title: 制度文件名，支持模糊匹配，如 "转专业"、"学士学位授予"。
        article: 条号，如 "第七条"、"7"、"第一条 【国家奖学金评选条件】" 均可。
    """
    # ==================== TODO(你来实现) ====================
    # 实现提示（完成后删除本注释块）：
    #
    #   import json
    #   chunks = json.load(open(CHUNKS_PATH, encoding="utf-8"))
    #
    #   # 1. 模糊匹配文档：document_title in chunk["doc_title"]
    #   # 2. 匹配条号：把 "7" 归一化成 "第七条"（可写一个 arabic->中文数字的小函数，
    #   #    或直接匹配 chunk["article"] 中同时含 document 关键词与 article 的项）
    #   # 3. 同一条可能被切成多个 chunk（按章-节-条切分），把命中的都返回并按顺序拼接
    #   # 4. 找不到时返回 {"status": "not_found", ...}，让模型决定换关键词或拒答
    # ==========================================================
    return not_implemented("read_full_article")
