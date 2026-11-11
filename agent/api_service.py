"""Agentic RAG 演示服务：把 LangGraph agent 接回原 FastAPI 接口契约。

兼容性设计：
- 接口路径/请求响应结构与旧版 server/app_rag_service.py 完全一致 →
  Java 桥接层（server/，指向 /api/rag/chat）零改动继续可用；
- SSE 事件向后兼容：保留 content/done，新增 tool_call / tool_result /
  metadata(route=AGENT) 事件——旧前端会忽略未知事件，新前端渲染工具轨迹。

多轮会话说明：为演示服务做了简化，会话历史保存 (用户问, 助手答) 文本对，
不回放中间工具消息（agent 每轮都会重新自主决策检索）。

启动：python -m agent.api_service   （http://127.0.0.1:8000）
"""

import json
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.config import LLM_MODEL
from agent.graph import build_graph
from agent.tools._retrieval import _get_pipeline

app = FastAPI(title="南昌大学 Agentic RAG 智能问答服务", version="4.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

graph = build_graph()

# 会话历史（内存态）：conversation_id -> [HumanMessage/AIMessage 文本对]
_sessions: dict = {}

# 复用毕设的 SQLite 落盘层（失败则纯内存，不影响问答）
try:
    from db_manager import RAGDatabaseManager  # scripts/ 已在 sys.path

    db = RAGDatabaseManager()
except Exception as e:  # pragma: no cover
    print(f"[api] SQLite 落盘不可用（{e}），会话仅保存在内存")
    db = None


@app.on_event("startup")
def warmup() -> None:
    """启动时预热：加载检索后端与模型，避免演示第一问等待过久。"""
    name, _, _ = _get_pipeline()
    print(f"[api] 预热完成 | 检索后端: {name} | LLM: {LLM_MODEL}")


class ChatReq(BaseModel):
    question: str
    top_k: Optional[int] = 3
    conversation_id: Optional[str] = "conv_default"
    student_type: Optional[str] = "undergraduate"
    category: Optional[str] = None


class ChatResp(BaseModel):
    conversationId: str
    question: str
    answer: str
    sources: List[str]
    route: str


class FeedbackReq(BaseModel):
    conversation_id: str
    rating: str
    message_id: Optional[int] = None
    feedback_text: Optional[str] = None


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n"


def _extract_sources(tool_name: str, tool_output) -> list:
    """从检索类工具的返回 JSON 中提取出处标签。"""
    if tool_name not in ("search_regulations", "compare_policies"):
        return []
    try:
        data = json.loads(tool_output)
    except Exception:
        return []
    tags = []

    def _collect(articles):
        for r in articles:
            tag = f"{r['doc_title']} ({r['chapter']} - {r['article']})"
            if tag not in tags:
                tags.append(tag)

    if tool_name == "search_regulations":
        _collect(data.get("results", []))
    else:
        for key in ("topic_a", "topic_b"):
            _collect(data.get(key, {}).get("articles", []))
    return tags


async def _run_agent_events(question: str, cid: str):
    """驱动 agent 图并以 SSE 事件形式产出（流式/非流式共用）。"""
    from langchain_core.messages import AIMessage, HumanMessage

    history = _sessions.setdefault(cid, [])
    history.append(HumanMessage(content=question))

    sources: list = []
    tool_calls: list = []
    final_answer = ""

    yield _sse({"type": "metadata", "route": "AGENT", "sources": [], "resolved_query": question})

    async for ev in graph.astream_events({"messages": history}, {"recursion_limit": 15}, version="v2"):
        etype, data = ev["event"], ev.get("data", {})
        if etype == "on_tool_start":
            args = data.get("input", {})
            tool_calls.append(ev["name"])
            yield _sse({"type": "tool_call", "name": ev["name"], "args": args})
        elif etype == "on_tool_end":
            out = data.get("output")
            out_text = out.content if hasattr(out, "content") else str(out)
            sources.extend(_extract_sources(ev["name"], out_text))
            yield _sse({"type": "tool_result", "name": ev["name"], "preview": str(out_text)[:160]})
        elif etype == "on_chat_model_stream":
            chunk = data.get("chunk")
            delta = getattr(chunk, "content", "") if chunk else ""
            if isinstance(delta, list):  # 部分模型返回分段 content
                delta = "".join(str(d) for d in delta)
            if delta:
                final_answer += delta
                yield _sse({"type": "content", "delta": delta})

    # 会话与落盘：保存 (问, 答) 文本对
    history.append(AIMessage(content=final_answer))
    sources = list(dict.fromkeys(sources))  # 多次工具调用的出处去重
    if db and final_answer:
        db.save_message(cid, "user", question)
        db.save_message(cid, "assistant", final_answer, route="AGENT", sources=sources)
    yield _sse({"type": "metadata", "route": "AGENT", "sources": sources, "resolved_query": question})
    yield _sse({"type": "done"})


@app.post("/api/rag/chat", response_model=ChatResp)
async def chat_endpoint(req: ChatReq):
    """非流式接口（Java 桥接层调用的是这个，保持契约兼容）。"""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")
    cid = req.conversation_id or "conv_default"

    answer, sources = "", []
    async for event in _run_agent_events(req.question, cid):
        payload = json.loads(event.removeprefix("data: ").strip())
        if payload.get("type") == "content":
            answer += payload["delta"]
        elif payload.get("type") == "metadata" and payload.get("sources"):
            sources = payload["sources"]

    return ChatResp(conversationId=cid, question=req.question, answer=answer,
                    sources=sources, route="AGENT")


@app.post("/api/rag/chat/stream")
async def chat_stream_endpoint(req: ChatReq):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")
    cid = req.conversation_id or "conv_default"
    return StreamingResponse(
        _run_agent_events(req.question, cid),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.post("/api/rag/feedback")
def submit_feedback(req: FeedbackReq):
    if db:
        db.save_feedback(conversation_id=req.conversation_id, rating=req.rating,
                         message_id=req.message_id, feedback_text=req.feedback_text)
    return {"status": "success", "message": "反馈已记录"}


@app.get("/api/rag/sessions")
def get_sessions():
    return db.get_all_sessions() if db else []


@app.get("/api/rag/messages/{conversation_id}")
def get_messages(conversation_id: str):
    return db.get_session_messages(conversation_id) if db else []


@app.get("/api/rag/suggestions")
def get_suggestions():
    return [
        "我绩点3.1，有一次记过处分，能申请转专业吗？",
        "分析一下转专业和保研的要求有什么区别？",
        "宿舍最多能用多大功率的电器？为什么？",
        "一学期挂科太多会不会被退学？",
        "食堂哪个窗口的红烧肉最好吃？",  # 演示拒答
    ]


if __name__ == "__main__":
    print("启动 Agentic RAG 服务 (http://127.0.0.1:8000) ...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
