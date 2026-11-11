"""工具 4：跨文档政策对比（新增能力，旧 pipeline 完全没有，留给你自由发挥）。"""

from langchain_core.tools import tool

from agent.tools._stub import not_implemented


@tool
def compare_policies(topic_a: str, topic_b: str) -> str:
    """检索并对比两项校规政策的关键信息（适用条件、门槛、流程、时间节点等），
    返回两个主题各自的要点，供进一步分析使用。

    何时使用：用户问"A 和 B 哪个适合我"、"转专业和保研的要求有什么区别"这类对比型问题时调用。

    Args:
        topic_a: 第一个政策主题，如 "转专业申请条件"。
        topic_b: 第二个政策主题，如 "保研推免条件"。
    """
    # ==================== TODO(你来实现) ====================
    # 实现提示（完成后删除本注释块）：
    #
    # 本工具没有现成代码可复用，思路：复用 search_regulations 的内部逻辑，
    # 分别检索 topic_a / topic_b 的 top 3 条文，返回：
    #
    #   {
    #     "topic_a": {"topic": ..., "articles": [ {doc_title, chapter, article, content}, ... ]},
    #     "topic_b": { ... 同上 ... }
    #   }
    #
    # 对比与综合判断交给模型完成（这正是 agent 相比 pipeline 的优势：
    # 工具只提供数据，推理由模型在循环里做）。
    #
    # 进阶（可选）：把 search_regulations 抽成一个私有函数 _do_search()，
    # 两个工具共用，避免复制粘贴。
    # ==========================================================
    return not_implemented("compare_policies")
