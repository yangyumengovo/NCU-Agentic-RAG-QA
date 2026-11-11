"""工具 3：硬规则校验（封装毕设已有的 rule_engine，最简单，建议第一个实现）。"""

from langchain_core.tools import tool

from agent.tools._stub import not_implemented


@tool
def check_rule(question: str) -> str:
    """对用户问题做结构化硬规则校验，判断 GPA/绩点、处分记录、论文查重率、宿舍电器功率
    等数值条件是否满足校规门槛（如转专业要求 GPA>=2.5 且无处分、学位授予要求 GPA>=2.0 等）。

    何时使用：用户给出了具体数值并询问"我能不能/符不符合/是否达到"这类资格判断问题时调用。
    注意：传入的应是包含完整数值信息的句子，如 "我 GPA 2.3，有一次记过处分，能转专业吗"。

    Args:
        question: 用户的原始问题（需包含 GPA/绩点/查重率/功率等数值与处分等关键信息）。
    """
    # ==================== TODO(你来实现) ====================
    # 实现提示（完成后删除本注释块）：
    #
    #   from rule_engine import RuleGuidedEngine
    #   result = RuleGuidedEngine().evaluate_rules(question)
    #   # result 形如:
    #   # {"has_rule_evaluation": True,
    #   #  "evaluations": [{"rule_name": "...", "passed": bool, "details": "..."}]}
    #   import json
    #   return json.dumps(result, ensure_ascii=False)
    # ==========================================================
    return not_implemented("check_rule")
