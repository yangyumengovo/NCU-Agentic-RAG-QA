"""工具 2：读取某条校规的完整原文（按文档 + 条号精确定位，用于溯源）。"""

import json
import re

from langchain_core.tools import tool

from agent.tools._retrieval import _backend

_CN_NUMS = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]


def _normalize_article(article: str) -> str:
    """把 '7' / '7条' / '第7条' 统一成 '第七条' 再参与匹配。

    必须带"第/条"一起匹配：只拿数字'七'做子串匹配会误命中
    '第十七条'、'第二十七条'（它们也包含'七'）。
    """
    s = article.strip()
    m = re.match(r"^第?(\d{1,3})条?", s)
    if m:
        n = int(m.group(1))
        if n <= 10:
            cn = _CN_NUMS[n]
        elif n < 20:
            cn = "十" + (_CN_NUMS[n % 10] if n % 10 else "")
        else:
            cn = _CN_NUMS[n // 10] + "十" + (_CN_NUMS[n % 10] if n % 10 else "")
        return f"第{cn}条"
    return s  # 本来就是 '第七条' 或完整条名，原样返回


@tool
def read_full_article(document_title: str, article: str) -> str:
    """读取指定校规文件中某一条的完整原文。当检索到的片段被截断、需要确认完整条款细节时使用。

    何时使用：search_regulations 返回的片段不够完整，或需要向用户展示某条的准确原文时。

    Args:
        document_title: 制度文件名，支持模糊匹配，如 "转专业"、"学士学位授予"。
        article: 条号，如 "第七条"、"7"、"第一条 【国家奖学金评选条件】" 均可。
    """
    chunks = _backend.chunks  # 已缓存的切片列表，避免每次调用都重新读文件

    # 1. 文档名模糊匹配（子串包含）；找不到时把 12 个文件名返回给模型，便于它换名重试
    doc_hits = [c for c in chunks if document_title.strip() in c["doc_title"]]
    if not doc_hits:
        available = sorted({c["doc_title"] for c in chunks})
        return json.dumps(
            {"status": "not_found", "message": "未找到匹配的制度文件", "available_docs": available},
            ensure_ascii=False,
        )

    # 2. 条号归一化后在命中文档内匹配
    target = _normalize_article(article)
    hits = [c for c in doc_hits if target and target in c["article"]]
    if not hits:
        return json.dumps(
            {
                "status": "not_found",
                "message": f"未找到条号「{target}」",
                "hint": "可先调用 search_regulations 定位具体条款",
            },
            ensure_ascii=False,
        )

    # 3. 同一条可能被切成多个 chunk：按文件分组、保持原始顺序拼接 content
    grouped: dict[str, list] = {}
    for c in hits:
        grouped.setdefault(c["doc_title"], []).append(c)

    return json.dumps(
        {
            "status": "success",
            "articles": [
                {
                    "doc_title": doc,
                    "chapter": cs[0]["chapter"],
                    "article": cs[0]["article"],
                    "full_text": "\n".join(c["content"] for c in cs),
                }
                for doc, cs in grouped.items()
            ],
        },
        ensure_ascii=False,
    )
