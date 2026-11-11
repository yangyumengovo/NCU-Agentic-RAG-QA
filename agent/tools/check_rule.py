"""工具 3：硬规则校验（封装毕设已有的 rule_engine）。"""

import json

from langchain_core.tools import tool

from rule_engine import RuleGuidedEngine  # scripts/ 已在 sys.path


@tool
def check_rule(question: str) -> str:
    """对用户问题做结构化硬规则校验，判断 GPA/绩点、处分记录、论文查重率、宿舍电器功率
    等数值条件是否满足校规门槛（如转专业要求 GPA>=2.5 且无处分、学位授予要求 GPA>=2.0 等）。

    何时使用：用户给出了具体数值并询问"我能不能/符不符合/是否达到"这类资格判断问题时调用。
    注意：传入的应是包含完整数值信息的句子，如 "我 GPA 2.3，有一次记过处分，能转专业吗"。

    Args:
        question: 用户的原始问题（需包含 GPA/绩点/查重率/功率等数值与处分等关键信息）。
    """
    result = RuleGuidedEngine().evaluate_rules(question)
    if not result.get("has_rule_evaluation"):
        # 没提取到数值条件时明确告知，模型就不会拿空结果硬编结论
        return json.dumps(
            {
                "has_rule_evaluation": False,
                "hint": "未识别出可校验的数值条件（GPA/绩点、处分、查重率%、电器功率W）",
            },
            ensure_ascii=False,
        )
    return json.dumps(result, ensure_ascii=False)
