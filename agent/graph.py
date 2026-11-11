"""LangGraph 图组装：Agentic RAG 的核心循环。

拓扑结构（ReAct 模式）：

                ┌─────────────────────────────┐
                │                             │
    START ──▶  agent(LLM) ─── 有工具调用 ──▶ tools(执行工具) ──┘
                  │
                  └──── 无工具调用 ──▶ END（模型认为信息足够，输出最终回答）

与旧版 rag_generator.py 的对比：
- 旧版：route_intent() 用关键词正则决定走哪条路，检索/重排/生成的顺序写死在 Python 里；
- 新版：LLM 自己看着对话决定"调不调工具、调哪个、调几次"，tools_condition 只是
  把"模型的意图"翻译成图的边（有 tool_calls 就去执行，没有就结束）。

学习建议：在 agent_node 里打断点/加 print，观察 response.tool_calls 的内容，
你会直观看到"决策权从代码转移到了模型"这件事。
"""

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from agent.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, assert_llm_configured
from agent.prompts import SYSTEM_PROMPT
from agent.tools import TOOLS


def build_graph(llm_with_tools=None):
    """构建并编译 agent 图。

    Args:
        llm_with_tools: 已绑定工具的可调用 LLM（Runnable）。不传时用 .env 配置的
            ChatOpenAI；测试时可注入 FakeMessagesListChatModel 等假模型，离线验证循环。
    """
    if llm_with_tools is None:
        assert_llm_configured()
        llm = ChatOpenAI(
            model=LLM_MODEL,
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
            temperature=0.2,
        )
        # bind_tools 会把 TOOLS 的函数签名 + docstring 转成 function-calling 协议下发给模型
        llm_with_tools = llm.bind_tools(TOOLS)

    def agent_node(state: MessagesState):
        # 每轮把系统提示词拼在最前（MessagesState 里只存对话与工具消息）
        response = llm_with_tools.invoke(
            [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
        )
        return {"messages": [response]}

    builder = StateGraph(MessagesState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(TOOLS))  # 执行 tool_calls 并把结果作为 ToolMessage 回填
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)  # 有 tool_calls → tools，否则 → END
    builder.add_edge("tools", "agent")  # 工具结果回到模型，进入下一轮决策
    return builder.compile()


if __name__ == "__main__":
    graph = build_graph()
    print("图编译成功。可用工具:", [t.name for t in TOOLS])
