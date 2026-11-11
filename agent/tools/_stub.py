"""工具骨架的公共占位返回。

在工具实现填完之前，统一返回"未实现"标记，让 agent 循环
不做任何工具实现也能端到端跑通——你可以先用 main.py 观察模型
如何决定调用哪个工具（这就是 agent 的核心行为）。
"""

import json


def not_implemented(tool_name: str) -> str:
    return json.dumps(
        {
            "status": "not_implemented",
            "tool": tool_name,
            "message": "该工具后端尚未实现（骨架占位）。请如实告诉用户：此功能正在开发中，暂时无法查询。",
        },
        ensure_ascii=False,
    )
