import os
import json
from vector_store_builder import LocalVectorStore

def calculate_metrics(test_cases, vector_store, top_k_list=[1, 3, 5]):
    """
    RAG 检索评估的核心实现：
    针对每一个测试问题，在向量数据库中检索 Top-K Chunk。
    判断包含 Ground Truth 出处的 Chunk 是否被正确召回，
    并计算 Hit Rate@K (命中率) 和 MRR (平均逆排名 Mean Reciprocal Rank)。
    """
    print(f"\n================ 检索能力自动化评测报告 ================")
    print(f"测试集规模: {len(test_cases)} 道高校规章制度测试题\n")
    
    hits = {k: 0 for k in top_k_list}
    rr_total = {k: 0.0 for k in top_k_list}
    
    results_detail = []

    for item in test_cases:
        qid = item["id"]
        query = item["question"]
        target_doc = item["target_doc"]
        target_article = item["target_article"]

        # 执行向量检索
        max_k = max(top_k_list)
        search_results = vector_store.query(query, top_k=max_k)

        first_hit_rank = None
        
        for rank_idx, res in enumerate(search_results, start=1):
            chunk = res["chunk"]
            doc_title = chunk["doc_title"]
            article = chunk["article"]
            chapter = chunk["chapter"]
            
            # 判断命中逻辑
            if target_doc in doc_title and (target_article in article or target_article in chapter):
                if first_hit_rank is None:
                    first_hit_rank = rank_idx
                break

        # 累计统计指标
        for k in top_k_list:
            if first_hit_rank is not None and first_hit_rank <= k:
                hits[k] += 1
                rr_total[k] += 1.0 / first_hit_rank

        hit_info = f"Top-1 命中 (Rank #{first_hit_rank})" if first_hit_rank == 1 else (f"Top-{first_hit_rank} 命中" if first_hit_rank else "未召回")
        top1_chunk = search_results[0]["chunk"] if search_results else None
        top1_str = f"{top1_chunk['doc_title']} {top1_chunk['article']}" if top1_chunk else "无"
        
        results_detail.append({
            "id": qid,
            "question": query,
            "target": f"{target_doc} ({target_article})",
            "hit_rank": first_hit_rank,
            "status": hit_info,
            "top1_retrieved": top1_str,
            "score": round(search_results[0]["score"], 4) if search_results else 0
        })

    # 输出逐题检索评估明细
    print(f"{'ID':<3} | {'检索评估状态':<15} | {'预期出处':<28} | {'相似度':<6} | {'检索到的Top-1结果'}")
    print("-" * 88)
    for r in results_detail:
        print(f"{r['id']:<3} | {r['status']:<15} | {r['target']:<28} | {r['score']:<6.4f} | {r['top1_retrieved']}")

    # 汇总统计表格
    total_num = len(test_cases)
    print("\n" + "=" * 55)
    print(f"{'评估指标 (Metric)':<18} | {'Hit Rate (命中率)':<20} | {'MRR (平均逆排名)'}")
    print("-" * 55)
    
    summary_report = {}
    for k in top_k_list:
        hit_rate = hits[k] / total_num
        mrr = rr_total[k] / total_num
        print(f"Top-{k:<13} | {hit_rate * 100:>6.2f}% ({hits[k]}/{total_num})       | {mrr:>6.4f}")
        summary_report[f"HitRate@{k}"] = round(hit_rate, 4)
        summary_report[f"MRR@{k}"] = round(mrr, 4)
        
    print("=" * 55 + "\n")
    return summary_report

def run_retrieval_test():
    store_path = r"f:\毕业论文\data\vector_store\ncu_regulations_vectors.pkl"
    eval_set_path = r"f:\毕业论文\data\eval_dataset\ncu_qa_testset.json"

    if not os.path.exists(store_path):
        raise FileNotFoundError(f"向量库不存在，请先运行 vector_store_builder.py 构建！")

    if not os.path.exists(eval_set_path):
        raise FileNotFoundError(f"未找到测试集文件: {eval_set_path}")

    with open(eval_set_path, 'r', encoding='utf-8') as f:
        test_cases = json.load(f)

    vector_store = LocalVectorStore.load(store_path)
    calculate_metrics(test_cases, vector_store, top_k_list=[1, 3, 5])

if __name__ == "__main__":
    run_retrieval_test()
