import os
import json
import sqlite3
from datetime import datetime

# 对应同目录下的 code/data/ncu_rag_history.db
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "ncu_rag_history.db"))

class RAGDatabaseManager:
    """基于 SQLite 的历史对话与用户点赞点踩反馈持久化数据库管理器"""
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_tables()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_tables(self):
        """初始化数据库表：会话主表、问答明细表、评分反馈表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. 会话主表
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                conversation_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                student_type TEXT DEFAULT 'undergraduate',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # 2. 问答明细表
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                resolved_query TEXT,
                route TEXT,
                sources_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES chat_sessions(conversation_id)
            )
            """)

            # 3. 用户评分反馈表 (用于 RLHF 与 RAG 质量分析)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_feedbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                conversation_id TEXT NOT NULL,
                rating TEXT NOT NULL,
                feedback_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.commit()

    def save_session(self, conversation_id, title="校规咨询", student_type="undergraduate"):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO chat_sessions (conversation_id, title, student_type, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(conversation_id) DO UPDATE SET
                title = CASE WHEN title LIKE '校规咨询%' OR title LIKE '新制度咨询%' OR title LIKE '新会话%' THEN excluded.title ELSE title END,
                student_type = excluded.student_type,
                updated_at = CURRENT_TIMESTAMP
            """, (conversation_id, title, student_type))
            conn.commit()

    def save_message(self, conversation_id, role, content, resolved_query=None, route=None, sources=None):
        if role == "user":
            clean_text = content.strip()
            auto_title = clean_text[:20] + ("..." if len(clean_text) > 20 else "")
            self.save_session(conversation_id, title=auto_title)
        else:
            self.save_session(conversation_id)

        sources_json = json.dumps(sources or [], ensure_ascii=False)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO chat_messages (conversation_id, role, content, resolved_query, route, sources_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (conversation_id, role, content, resolved_query, route, sources_json))
            msg_id = cursor.lastrowid
            conn.commit()
            return msg_id

    def save_feedback(self, conversation_id, rating, message_id=None, feedback_text=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO user_feedbacks (message_id, conversation_id, rating, feedback_text)
            VALUES (?, ?, ?, ?)
            """, (message_id, conversation_id, rating, feedback_text))
            conn.commit()

    def get_all_sessions(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT conversation_id, title, student_type, created_at, updated_at FROM chat_sessions ORDER BY updated_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_session_messages(self, conversation_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, conversation_id, role, content, resolved_query, route, sources_json, created_at FROM chat_messages WHERE conversation_id = ? ORDER BY id ASC", (conversation_id,))
            rows = cursor.fetchall()
            result = []
            for row in rows:
                item = dict(row)
                item["sources"] = json.loads(item["sources_json"]) if item["sources_json"] else []
                result.append(item)
            return result

if __name__ == "__main__":
    db = RAGDatabaseManager()
    print("数据库已成功定位至:", db.db_path)
