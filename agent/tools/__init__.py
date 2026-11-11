"""工具注册表：agent 可用的全部工具。

新增工具三步：
1. 在本目录新建 xxx.py，用 @tool 装饰器定义函数（docstring 会作为工具说明书暴露给模型）；
2. 在下方 import 并加入 TOOLS；
3. 完成 TODO（实现前返回 not_implemented 占位，不影响循环运行）。
"""

from agent.tools.check_rule import check_rule
from agent.tools.compare_policies import compare_policies
from agent.tools.read_full_article import read_full_article
from agent.tools.search_regulations import search_regulations

TOOLS = [
    search_regulations,
    read_full_article,
    check_rule,
    compare_policies,
]
