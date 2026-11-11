"""agent 包：基于 LangGraph 的 Agentic RAG 骨架。

导入本包时自动把仓库根目录和 scripts/ 加入 sys.path，
这样工具实现里可以直接 `from vector_store_builder import LocalVectorStore`
复用毕设已有的检索/重排/规则引擎代码。
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

for _p in (PROJECT_ROOT, PROJECT_ROOT / "scripts"):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)
