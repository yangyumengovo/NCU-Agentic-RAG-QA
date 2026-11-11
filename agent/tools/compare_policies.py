"""工具 4：跨文档政策对比（新增能力，旧 pipeline 完全没有）。

设计哲学：工具只负责"取数"——分别检索两个主题的条文；
对比与综合推理由模型在 agent 循环里完成。这正是 Agentic RAG
相比固定 pipeline 的分工优势。
"""

import json

from langchain_core.tools import tool

from agent.tools._retrieval import hybrid_search


@tool
def compare_policies(topic_a: str, topic_b: str) -> str:
    """检索并对比两项校规政策的关键信息（适用条件、门槛、流程、时间节点等），
    返回两个主题各自的要点，供进一步分析使用。

    何时使用：用户问"A 和 B 哪个适合我"、"转专业和保研的要求有什么区别"这类对比型问题时调用。

    Args:
        topic_a: 第一个政策主题，如 "转专业申请条件"。
        topic_b: 第二个政策主题，如 "保研推免条件"。
    """
    try:
        # 1. 分别检索两个主题，作为对比材料各取 Top 3 即可
        articles_a = hybrid_search(topic_a, student_type="all", top_k=3)
        articles_b = hybrid_search(topic_b, student_type="all", top_k=3)

        # 2. 两边都搜不到才算失败；只有一边有结果时仍返回，由模型判断如何解读
        if not articles_a and not articles_b:
            return json.dumps(
                {"status": "not_found", "message": "未能检索到这两个主题的相关校规。"},
                ensure_ascii=False,
            )

        # 3. 只返回结构化数据，对比分析交给模型完成
        return json.dumps(
            {
                "topic_a": {"topic": topic_a, "articles": articles_a},
                "topic_b": {"topic": topic_b, "articles": articles_b},
                "note": "以上为两个主题各自最相关的条文，请由你（模型）完成对比分析并标注各自出处。",
            },
            ensure_ascii=False,
        )
    except Exception as e:
        # 容错：工具内部报错时返回结构化错误，而不是让整个 agent 图崩溃
        return json.dumps({"error": f"对比检索过程中发生错误: {e}"}, ensure_ascii=False)
