import os
import sys
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))
from rag_generator import AdvancedRAGGenerator
from db_manager import RAGDatabaseManager

app = FastAPI(
    title="南昌大学 RAG 高校制度智能问答系统 AI 服务端",
    version="3.5.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定位至 code/data/vector_store/ncu_regulations_vectors.pkl
store_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "vector_store", "ncu_regulations_vectors.pkl"))
rag_engine = None
db_manager = RAGDatabaseManager()

@app.on_event("startup")
def startup_event():
    global rag_engine
    if os.path.exists(store_path):
        print(f"[FastAPI] 成功加载 RAG 向量数据库: {store_path}")
        rag_engine = AdvancedRAGGenerator(vector_store_path=store_path)
    else:
        print(f"[FastAPI 警告] 向量数据库文件未找到，请检查: {store_path}")

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

@app.post("/api/rag/chat", response_model=ChatResp)
def chat_endpoint(req: ChatReq):
    """单次完整返回接口"""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")
    
    if not rag_engine:
        raise HTTPException(status_code=500, detail="RAG 向量引擎未初始化")

    cid = req.conversation_id or "conv_default"
    res = rag_engine.answer_question(
        query=req.question,
        top_k=req.top_k,
        student_type=req.student_type,
        category=req.category,
        conversation_id=cid
    )
    
    return ChatResp(
        conversationId=cid,
        question=req.question,
        answer=res["answer"],
        sources=res["sources"],
        route=res.get("route", "POLICY_RAG")
    )

@app.post("/api/rag/chat/stream")
def chat_stream_endpoint(req: ChatReq):
    """支持多轮对话与 SSE 打字机流式推流接口"""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")
    
    if not rag_engine:
        raise HTTPException(status_code=500, detail="RAG 向量引擎未初始化")

    cid = req.conversation_id or "conv_default"

    def event_generator():
        for chunk in rag_engine.stream_answer_question(
            query=req.question,
            top_k=req.top_k,
            student_type=req.student_type,
            category=req.category,
            conversation_id=cid
        ):
            yield f"data: {chunk}"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/api/rag/feedback")
def submit_feedback(req: FeedbackReq):
    """保存用户点赞/点踩评分落盘"""
    db_manager.save_feedback(
        conversation_id=req.conversation_id,
        rating=req.rating,
        message_id=req.message_id,
        feedback_text=req.feedback_text
    )
    return {"status": "success", "message": "反馈已成功持久化落盘"}

@app.get("/api/rag/sessions")
def get_sessions():
    """读取所有历史会话列表"""
    return db_manager.get_all_sessions()

@app.get("/api/rag/messages/{conversation_id}")
def get_messages(conversation_id: str):
    """读取具体会话的完整历史问答列表"""
    return db_manager.get_session_messages(conversation_id)

@app.get("/api/rag/suggestions")
def get_suggestions():
    return [
        "挂科会影响保研和申请学士学位吗？",
        "缺考满多少比例会被取消考试资格？",
        "南昌大学申请学士学位的 GPA 要求是多少？",
        "在校最长修业年限是多少年？",
        "特等奖学金与一等奖学金的评选条件与金额？"
    ]

if __name__ == "__main__":
    print("启动 AI RAG 服务 (http://127.0.0.1:8000)...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
