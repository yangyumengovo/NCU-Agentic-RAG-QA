"""命令行入口：跑通 agent 循环并打印完整的工具调用轨迹。

用法（在仓库根目录）：
    交互模式:  python -m agent.main
    单次提问:  python -m agent.main --ask "我绩点3.1有记过处分，能转专业吗"

输出中的三类行：
    🛠  Agent 决定调用工具: xxx(...)   ← 模型的自主决策（agent 的核心）
    📦 工具返回 [xxx]: ...            ← 工具执行结果（未实现时返回占位 JSON）
    🤖 ...                            ← 模型的最终自然语言回答
"""

import argparse
import sys

from langchain_core.messages import HumanMessage

from agent.config import LLM_MODEL
from agent.graph import build_graph


def _print_message(msg) -> None:
    if msg.type == "tool":
        preview = msg.content if len(msg.content) <= 160 else msg.content[:160] + " ..."
        print(f"  📦 工具返回 [{msg.name}]: {preview}")
    elif getattr(msg, "tool_calls", None):
        for tc in msg.tool_calls:
            args_str = ", ".join(f"{k}={v!r}" for k, v in tc["args"].items())
            print(f"  🛠  Agent 决定调用工具: {tc['name']}({args_str})")
    elif msg.content:
        print(f"  🤖 {msg.content}")


def run_turn(graph, history: list, question: str) -> list:
    """执行一轮对话：把整段历史交给图，流式打印每个节点的增量消息。"""
    print(f"\n你: {question}")
    history.append(HumanMessage(content=question))
    config = {"recursion_limit": 20}  # 防止模型无限调工具

    for update in graph.stream({"messages": history}, config, stream_mode="updates"):
        for node_name, payload in update.items():
            for msg in payload.get("messages", []):
                _print_message(msg)
                history.append(msg)
    return history


def main() -> None:
    parser = argparse.ArgumentParser(description="NCU 校规 Agentic RAG 助手")
    parser.add_argument("--ask", help="单次提问（不进入交互模式）", default=None)
    args = parser.parse_args()

    graph = build_graph()
    print(f"Agentic RAG 就绪（模型: {LLM_MODEL}）。输入 exit/退出 结束。")

    if args.ask:
        run_turn(graph, [], args.ask)
        return

    history: list = []
    while True:
        try:
            question = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question or question.lower() in {"exit", "quit", "退出"}:
            break
        run_turn(graph, history, question)

    print("再见！")


if __name__ == "__main__":
    try:  # Windows 控制台中文兼容
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
