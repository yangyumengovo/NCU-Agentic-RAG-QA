import os
import json
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class LocalVectorStore:
    def __init__(self):
        # 1. 密集语义特征向量器 (Dense Embedding Feature)
        self.dense_vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4))
        # 2. 稀疏关键词词频向量器 (Sparse BM25 Keyword Feature)
        self.sparse_vectorizer = TfidfVectorizer(analyzer='word', token_pattern=r'(?u)\b\w+\b')
        
        self.dense_vectors = None
        self.sparse_vectors = None
        self.chunks = []

    def fit_and_save(self, chunks, save_path):
        self.chunks = chunks
        corpus = [c["full_chunk_text"] for c in chunks]
        
        print(f"正在提取 {len(chunks)} 个切片的【密集语义】与【稀疏关键词】特征向量...")
        self.dense_vectors = self.dense_vectorizer.fit_transform(corpus)
        self.sparse_vectors = self.sparse_vectorizer.fit_transform(corpus)
        
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'wb') as f:
            pickle.dump({
                "dense_vectorizer": self.dense_vectorizer,
                "sparse_vectorizer": self.sparse_vectorizer,
                "dense_vectors": self.dense_vectors,
                "sparse_vectors": self.sparse_vectors,
                "chunks": self.chunks
            }, f)
        print(f"混合索引向量库构建成功！维度: Dense {self.dense_vectors.shape}, Sparse {self.sparse_vectors.shape}")

    @classmethod
    def load(cls, save_path):
        store = cls()
        with open(save_path, 'rb') as f:
            data = pickle.load(f)
            store.dense_vectorizer = data["dense_vectorizer"]
            store.sparse_vectorizer = data["sparse_vectorizer"]
            store.dense_vectors = data["dense_vectors"]
            store.sparse_vectors = data["sparse_vectors"]
            store.chunks = data["chunks"]
        return store

    def hybrid_query(self, query_text, top_k=5, student_type=None, category=None, alpha=0.6):
        """
        核心方法：【混合检索 (Hybrid Search)】+ 【作用域过滤 (Scope Filtering)】
        - alpha: 密集语义得分权重 (0.6)，1 - alpha: 稀疏关键词得分权重 (0.4)
        - student_type: 作用域过滤（如 'undergraduate', 'postgraduate', 'all'）
        - category: 业务分类过滤（如 '学籍管理', '学位授予'）
        """
        q_dense = self.dense_vectorizer.transform([query_text])
        dense_scores = cosine_similarity(q_dense, self.dense_vectors)[0]

        q_sparse = self.sparse_vectorizer.transform([query_text])
        sparse_scores = cosine_similarity(q_sparse, self.sparse_vectors)[0]

        hybrid_scores = alpha * dense_scores + (1 - alpha) * sparse_scores

        candidates = []
        for idx, chunk in enumerate(self.chunks):
            if student_type and student_type != 'all':
                if chunk.get("student_type") not in [student_type, 'all']:
                    continue
            
            if category and category != 'all':
                if chunk.get("category") != category:
                    continue

            candidates.append({
                "score": float(hybrid_scores[idx]),
                "dense_score": float(dense_scores[idx]),
                "sparse_score": float(sparse_scores[idx]),
                "chunk": chunk
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:top_k]

def build_vector_store():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    chunks_path = os.path.join(base_dir, "data", "processed_chunks", "ncu_regulations_chunks.json")
    save_path = os.path.join(base_dir, "data", "vector_store", "ncu_regulations_vectors.pkl")
    
    if not os.path.exists(chunks_path):
        raise FileNotFoundError(f"找不到处理好的 Chunk 数据: {chunks_path}")
        
    print("1. 读取包含 Scope Metadata 的切片数据...")
    with open(chunks_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
        
    print(f"包含 {len(chunks)} 个结构化 Chunk。")

    print("\n2. 构建离线混合索引与作用域过滤存储...")
    store = LocalVectorStore()
    store.fit_and_save(chunks, save_path)

if __name__ == "__main__":
    build_vector_store()
