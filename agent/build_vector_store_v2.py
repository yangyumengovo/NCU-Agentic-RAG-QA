"""构建 v2 向量库：真 embedding 的 Dense 通道（Sparse 通道继续复用旧 pickle）。

设计意图：v1 → v2 的唯一变量是 Dense 通道（字符TF-IDF → bge 语义向量），
切片、Sparse、重排器全部不变——这样对比实验的因果才是干净的。

用法：python -m agent.build_vector_store_v2
"""

import hashlib
import json

import numpy as np

from agent.config import CHUNKS_PATH, DATA_DIR
from agent.embeddings import EMBEDDING_MODEL, embed_passages

NPZ_PATH = DATA_DIR / "vector_store" / "ncu_regulations_embeddings_v2.npz"


def build() -> None:
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        chunks = json.load(f)

    texts = [c["full_chunk_text"] for c in chunks]
    vectors = np.asarray(embed_passages(texts), dtype=np.float32)

    # 记录切片集合的指纹：切片变了（重切分/新增文档）就能发现需要重建
    digest = hashlib.md5(json.dumps(chunks, ensure_ascii=False).encode()).hexdigest()[:10]
    np.savez_compressed(NPZ_PATH, vectors=vectors, chunks_hash=digest, model=EMBEDDING_MODEL)
    print(f"v2 向量库构建完成: {vectors.shape[0]} 条 x {vectors.shape[1]} 维 -> {NPZ_PATH.name}")
    print(f"模型: {EMBEDDING_MODEL} | 切片指纹: {digest}")


if __name__ == "__main__":
    build()
