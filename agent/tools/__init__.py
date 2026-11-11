"""工具注册表：agent 可用的全部工具。

四个工具均已实现：
- search_regulations  混合检索+重排（复用毕设 vector_store_builder + reranker）
- read_full_article   按文档+条号读完整条文（读 processed_chunks JSON）
- check_rule          硬规则校验（复用毕设 rule_engine）
- compare_policies    跨文档政策对比（复用检索，推理由模型完成）

新增工具三步：
1. 在本目录新建 xxx.py，用 @tool 装饰器定义函数（docstring 会作为工具说明书暴露给模型）；
2. 在下方 import 并加入 TOOLS；
3. 检索类工具请复用 _retrieval.hybrid_search，不要复制粘贴检索逻辑。
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
