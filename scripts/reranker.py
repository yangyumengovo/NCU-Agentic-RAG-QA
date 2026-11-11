import re
import numpy as np

class LocalReranker:
    def __init__(self):
        pass

    def rerank(self, query, candidate_items, top_k=3):
        """
        Cross-Matching 交叉重排序：
        评估 Query 与各个候选 Chunk 之间的重合度、关键词精确匹配度及上下文相关度，
        对粗筛召回的 Top-N 结果进行细粒度重打分与排序。
        """
        if not candidate_items:
            return []

        query_terms = set(re.findall(r'\w+', query.lower()))
        
        reranked_results = []
        for item in candidate_items:
            chunk = item["chunk"]
            text_lower = chunk["full_chunk_text"].lower()
            
            # 基础粗筛得分
            base_score = item.get("score", 0.0)
            sparse_score = item.get("sparse_score", 0.0)
            dense_score = item.get("dense_score", 0.0)

            # 1. 标题与章节精确匹配加权
            title_boost = 0.0
            for term in query_terms:
                if len(term) > 1:
                    if term in chunk["doc_title"].lower():
                        title_boost += 0.20
                    if term in chunk["chapter"].lower() or term in chunk["article"].lower():
                        title_boost += 0.25

            # 2. 条款核心限定词加权（如数字、门槛）
            keyword_boost = 0.0
            keywords = ["不及格", "三分之一", "GPA", "2.0", "2.5", "800W", "记过", "处分", "开除", "奖学金", "查重", "退学"]
            for kw in keywords:
                if kw.lower() in query.lower() and kw.lower() in text_lower:
                    keyword_boost += 0.30

            # 保持基础得分权重的稳定性
            final_score = base_score * 0.8 + title_boost + keyword_boost + (sparse_score * 0.4)

            reranked_results.append({
                "rerank_score": round(float(final_score), 4),
                "original_score": base_score,
                "chunk": chunk
            })

        # 按重排序得分降序排列
        reranked_results.sort(key=lambda x: x["rerank_score"], reverse=True)
        return reranked_results[:top_k]

if __name__ == "__main__":
    reranker = LocalReranker()
    print("Reranker 模块重构成功！")
