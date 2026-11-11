"""真语义 Embedding 后端：本地 bge-small-zh-v1.5（默认）。

与旧版 vector_store_builder 里字符级 TF-IDF 的"Dense"不同，这里是真正的语义向量：
"挂科"能匹配"课程不及格"（词面零重合但语义相近，实测相似度 0.75 vs 无关句 0.36）。

- 模型 ~95MB，首次下载后缓存在 ~/.cache/huggingface，之后离线可用；
- 国内网络默认走 hf-mirror 镜像（设环境变量 HF_ENDPOINT 可覆盖）；
- 后续想换智谱 embedding-3 等 API 版本，只需在这里加一个分支，其余代码不动。
"""

import os

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")

# bge 系列官方建议：检索场景给 query 加这句指令，passage 不加
_QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_passages(texts: list[str]):
    """语料入库用：批量编码，L2 归一化（归一化后点积 = 余弦相似度）。"""
    return _get_model().encode(texts, normalize_embeddings=True, show_progress_bar=False)


def embed_query(query: str):
    """查询用：加 bge 检索指令后编码，返回归一化向量。"""
    return _get_model().encode([_QUERY_INSTRUCTION + query], normalize_embeddings=True)[0]
