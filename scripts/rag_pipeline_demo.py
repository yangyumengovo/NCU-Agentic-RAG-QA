import os
import json
from rag_generator import RAGGenerator

def run_pipeline_demo():
    store_path = r"f:\毕业论文\data\vector_store\ncu_regulations_vectors.pkl"
    eval_set_path = r"f:\毕业论文\data\eval_dataset\ncu_qa_testset.json"
    output_log_path = r"f:\毕业论文\data\eval_dataset\rag_generation_results.md"

    rag = RAGGenerator(vector_store_path=store_path)

    with open(eval_set_path, 'r', encoding='utf-8') as f:
        test_cases = json.load(f)

    print("==========================================================")
    print("      基于 RAG 的高校制度智能问答系统 - 端到端生成测试       ")
    print("==========================================================\n")

    markdown_output = "# 基于 RAG 的高校制度智能问答系统 - 问答测试生成记录\n\n"
    markdown_output += f"生成时间：2026年7月25日\n测试样本数：{len(test_cases)} 题\n\n"

    for item in test_cases[:5]: # 测试前 5 道典型代表题
        qid = item["id"]
        q = item["question"]
        
        print(f"【问题 #{qid}】: {q}")
        res = rag.answer_question(q, top_k=3)
        print("-" * 60)
        print(f"【系统回答】:\n{res['answer']}")
        print("=" * 60 + "\n")

        markdown_output += f"### 问题 #{qid}: {q}\n\n"
        markdown_output += f"**系统问答输出**：\n\n{res['answer']}\n\n"
        markdown_output += f"**检索召回出处卡片**：\n"
        for src in res["sources"]:
            markdown_output += f"- `{src}`\n"
        markdown_output += "\n---\n\n"

    os.makedirs(os.path.dirname(output_log_path), exist_ok=True)
    with open(output_log_path, 'w', encoding='utf-8') as f:
        f.write(markdown_output)

    print(f"端到端问答测试完成！详细问答日志已保存至: {output_log_path}")

if __name__ == "__main__":
    run_pipeline_demo()
