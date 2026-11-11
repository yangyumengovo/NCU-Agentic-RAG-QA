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
    import json
    import re

    chunks = json.load(open(CHUNKS_PATH, encoding="utf-8"))

    # 1. 辅助函数：把阿拉伯数字转成中文数字（处理 1-99 足够用了）
    def arabic_to_chinese(num_str: str) -> str:
        num_str = str(num_str).strip()
        if num_str.isdigit():
            num = int(num_str)
            chinese_nums = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
            if num <= 10:
                return chinese_nums[num]
            elif num < 20:
                return "十" + chinese_nums[num % 10]
            else:
                tens = chinese_nums[num // 10] + "十"
                ones = chinese_nums[num % 10] if num % 10 != 0 else ""
                return tens + ones
        return num_str

    # 2. 归一化用户的输入条号 (比如把 "7" 变成 "七"，统一用小写中文匹配)
    target_article = arabic_to_chinese(article)
    # 如果用户输入了类似 "第一条 【国家奖学金...】"，我们提取出核心的 "一"
    match = re.search(r'第([一二三四五六七八九十百零两\d]+)条', target_article)
    if match:
        target_article = match.group(1)

    matched_chunks = []
    
    # 3. 遍历寻找匹配项
    for chunk in chunks:
        # 获取当前 chunk 的文档名和条号（注意检查你的 JSON 里实际的键名）
        doc_name = chunk.get("doc_title", "") or chunk.get("document_title", "")
        chunk_article = chunk.get("article", "") or ""
        
        # 文档名模糊匹配
        if document_title in doc_name or doc_name in document_title:
            # 条号匹配：如果目标中文数字在 chunk 的条号里，或者目标就是精确的条号
            if target_article in chunk_article or chunk_article in target_article:
                matched_chunks.append(chunk)

    # 4. 处理结果
    if not matched_chunks:
        return json.dumps({
            "status": "not_found",
            "message": f"未找到文件《{document_title}》中关于'{article}'的内容，请检查文件名或条号是否正确。"
        }, ensure_ascii=False)

    # 5. 同一条款可能被切成了多个 chunk，按原顺序拼接文本
    # （假设你的 JSON 列表本身就是按文档顺序排好的，如果 chunk 有 "chunk_id" 或 "index" 字段可以显式排序）
    full_text = "\n".join([c.get("content", "") for c in matched_chunks])

    return json.dumps({
        "status": "success",
        "document_title": matched_chunks[0].get("doc_title", document_title),
        "article": matched_chunks[0].get("article", article),
        "full_text": full_text
    }, ensure_ascii=False)

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
    #return not_implemented("read_full_article")
