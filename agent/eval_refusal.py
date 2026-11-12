"""拒答题自动评测：跑完整 agent（LLM+工具循环），量化防幻觉拒答能力。

设计要点：
- 跑完整 agent 图而非只跑检索——拒答是"模型决策 + 工具反馈"的综合行为；
- 双重判定：规则（拒答话术标记，便宜但粗）+ LLM 裁判（独立判断是否给出实质
  制度性内容）。两者不一致的样本单独标出，通常是最有分析价值的边角案例；
- 分层指标：完全无关 / 校园相关但库外 / 语料内无答案，难度依次递增。

用法：python -m agent.eval_refusal [--limit 3]   # limit 用于快速冒烟
"""

import argparse
import json
from datetime import date

from agent.config import DATA_DIR, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from agent.graph import build_graph

TESTSET_PATH = DATA_DIR / "eval_dataset" / "ncu_qa_testset.json"
REPORT_PATH = DATA_DIR / "eval_dataset" / "refusal_eval_report.md"

# 规则判定的拒答话术标记（命中任一即判"拒答"）
REFUSAL_MARKERS = [
    "未找到", "没有找到", "没有相关", "无相关", "未能找到", "没有查询到",
    "无法回答", "无法提供", "无法查询", "不能提供", "不属于", "不在我的",
    "超出", "能力范围", "建议咨询", "建议您咨询", "建议直接咨询", "暂无",
]

JUDGE_PROMPT = """你是评测裁判。判断助手对下面问题的回答属于哪一类：
- 拒答：明确表示无相关规定 / 超出能力范围 / 建议咨询相关部门，未给出具体的制度内容、数字或流程结论
- 实质回答：给出了具体的规定内容、数字、流程或实质性结论（即使同时表达了抱歉/不确定也算实质回答）

【问题】{question}
【助手回答】{answer}

严格按以下两行输出，不要输出其他内容：
判定：拒答 或 实质回答
理由：一句话"""


def run_agent(graph, question: str) -> tuple[str, list[str]]:
    """返回 (最终回答, 调用过的工具名列表)。"""
    result = graph.invoke({"messages": [("user", question)]}, {"recursion_limit": 15})
    tool_calls, final_answer = [], ""
    for msg in result["messages"]:
        if getattr(msg, "tool_calls", None):
            tool_calls.extend(tc["name"] for tc in msg.tool_calls)
        if msg.type == "ai" and msg.content:
            final_answer = msg.content
    return final_answer, tool_calls


def rule_verdict(answer: str) -> str:
    return "拒答" if any(m in answer for m in REFUSAL_MARKERS) else "实质回答"


def llm_verdict(question: str, answer: str) -> str | None:
    try:
        from openai import OpenAI

        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": JUDGE_PROMPT.format(question=question, answer=answer[:1500])}],
            temperature=0,
        )
        first_line = resp.choices[0].message.content.strip().splitlines()[0]
        return "拒答" if "拒答" in first_line else "实质回答"
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="只跑前 N 题（冒烟用）")
    args = parser.parse_args()

    with open(TESTSET_PATH, encoding="utf-8") as f:
        items = [it for it in json.load(f) if it.get("type") == "拒答" and it.get("review_status") != "已删除"]
    if args.limit:
        items = items[: args.limit]

    graph = build_graph()
    print(f"拒答评测: {len(items)} 题 | 模型: {LLM_MODEL}")

    records = []
    for it in items:
        answer, tools = run_agent(graph, it["question"])
        v_rule = rule_verdict(answer)
        v_llm = llm_verdict(it["question"], answer)
        final = v_llm or v_rule
        records.append({
            **it, "answer": answer, "tools": tools,
            "verdict_rule": v_rule, "verdict_llm": v_llm, "verdict": final,
            "correct": final == "拒答",
        })
        flag = "  ⚠️规则/LLM不一致" if v_llm and v_rule != v_llm else ""
        print(f"Q{it['id']:>3} [{it['subtype']}] {final} (工具:{tools or '无'}){flag}")

    n = len(records)
    acc = sum(r["correct"] for r in records) / n
    print(f"\n拒答正确率: {acc:.1%}（误答率 {1 - acc:.1%}）")
    print("\n分层正确率:")
    for sub in ("完全无关", "校园相关但库外", "语料内无答案"):
        grp = [r for r in records if r["subtype"] == sub]
        if grp:
            print(f"  {sub}: {sum(r['correct'] for r in grp) / len(grp):.1%} ({len(grp)} 题)")
    tool_counts = [len(r["tools"]) for r in records]
    print(f"平均工具调用: {sum(tool_counts) / n:.1f} 次/题")

    md = [f"# 拒答题评测报告（防幻觉误答率）", "",
          f"- 日期：{date.today()} | 模型: {LLM_MODEL} | {n} 题（完全无关/校园库外/语料内无答案三层）",
          f"- 判定：规则 + LLM 裁判双判，不一致样本单独标注", "",
          f"**总体拒答正确率: {acc:.1%}（误答率 {1 - acc:.1%}）**", "",
          "| id | 子类型 | 判定 | 规则判 | LLM判 | 工具调用 |", "| :--- | :--- | :--- | :--- | :--- | :--- |"]
    for r in records:
        md.append(f"| Q{r['id']} | {r['subtype']} | {'✅拒答' if r['correct'] else '❌误答'} | "
                  f"{r['verdict_rule']} | {r['verdict_llm'] or '-'} | {','.join(r['tools']) or '无'} |")
    md.append("\n## 失败样本全文（人工归因用）\n")
    for r in records:
        if not r["correct"] or (r["verdict_llm"] and r["verdict_rule"] != r["verdict_llm"]):
            md.append(f"### Q{r['id']} [{r['subtype']}] {r['question']}\n")
            md.append(f"- 工具调用: {r['tools'] or '无'} | 规则判: {r['verdict_rule']} | LLM判: {r['verdict_llm']}\n")
            md.append(f"- 回答: {r['answer'][:600]}\n")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"\n报告已导出: {REPORT_PATH}")


if __name__ == "__main__":
    main()
