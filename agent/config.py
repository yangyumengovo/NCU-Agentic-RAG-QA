"""集中管理配置：LLM 接入参数 + 数据文件路径。

所有敏感信息走 .env（已被 .gitignore 排除），不再像旧版
rag_generator.py 那样把 API Key 硬编码进源码。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# ---- LLM（OpenAI 兼容接口，默认指向智谱开放平台）----
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
LLM_MODEL = os.getenv("LLM_MODEL", "glm-4-flash")

# ---- 数据文件路径（工具实现会用到）----
DATA_DIR = PROJECT_ROOT / "data"
CHUNKS_PATH = DATA_DIR / "processed_chunks" / "ncu_regulations_chunks.json"
VECTOR_STORE_PATH = DATA_DIR / "vector_store" / "ncu_regulations_vectors.pkl"


def assert_llm_configured() -> None:
    if not LLM_API_KEY:
        raise RuntimeError(
            "未配置 LLM_API_KEY：请复制 .env.example 为 .env，"
            "填入智谱开放平台(https://open.bigmodel.cn)的 API Key 后重试。"
        )
