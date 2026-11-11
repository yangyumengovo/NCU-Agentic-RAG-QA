import os
import re
import json
import time
from vector_store_builder import LocalVectorStore
from query_rewriter import QueryRewriter
from reranker import LocalReranker
from conversation_memory import ConversationMemoryManager
from db_manager import RAGDatabaseManager
from rule_engine import RuleGuidedEngine

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

SYSTEM_PROMPT_RAG = """你是一个专业、严谨的南昌大学规章制度智能问答助手。
请仅根据下方提供的【参考制度文档】和【硬规则结构化校验诊断】内容来解答用户的咨询。

【回答要求】：
1. 答案必须严格基于参考文档，条理清晰、层次分明（建议使用数字序号或加粗标出要点）。
2. 如果存在【硬规则结构化校验诊断】，请在回答最头部优先展示规则诊断结论卡片。
3. 语气客观专业，切勿凭空猜测；结合参考文档进行顺畅的总结提炼。
4. 答复结尾必须明确列出所引用的规章制度名称及条文出处。
5. 如果参考文档中没有包含解答用户问题所需的信息，请明确回答：“查阅现有规章制度库，未找到相关具体规定。”
"""

SYSTEM_PROMPT_GENERAL = """你是一个友好、专业的南昌大学智能助手。
请回答用户的通用咨询或问候，保持礼貌、简洁与专业。
"""

POLICY_KEYWORDS_PATTERN = re.compile(
    r'(学籍|重修|缺考|缓考|处分|纪律|学分|绩点|GPA|学位|毕业|结业|退学|休学|复学|奖学金|评优|保研|推免|违纪|考试|作弊|学术不端|宿舍|规章|制度|规定|转专业|考核|成绩|请假|考勤|申诉|查重|论文|电器|功率|复核)'
)

# 明显与校规无关的异构问题识别正则
OUT_OF_DOMAIN_PATTERN = re.compile(r'(宠物|狗|猫|天气|股票|游戏|点外卖|买手机|明星|电影)')

# 防幻觉安全据答宣告
REFUSAL_SAFETY_TEXT = "查阅南昌大学现有 12 大领域规章制度库，未找到与您提问相关的具体规定。为确保校规解答的权威性与严谨性，避免提供未经核实的模糊猜测，建议您直接咨询各学院教务办或辅导员老师。"

class AdvancedRAGGenerator:
    def __init__(self, vector_store_path=None, api_key=None, base_url=None, model_name=None):
        if not vector_store_path:
            vector_store_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "vector_store", "ncu_regulations_vectors.pkl"))
            
        if not os.path.exists(vector_store_path):
            raise FileNotFoundError(f"向量库不存在: {vector_store_path}")
            
        self.vector_store = LocalVectorStore.load(vector_store_path)
        self.rewriter = QueryRewriter()
        self.reranker = LocalReranker()
        self.memory_manager = ConversationMemoryManager(max_history_turns=5)
        self.db_manager = RAGDatabaseManager()
        self.rule_engine = RuleGuidedEngine()
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "b3fc80904db14c969b05d8b3e0ca4230.GaUVLqz9SF96Kqxm")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
        self.model_name = model_name or os.getenv("LLM_MODEL_NAME", "glm-4-flash")
        
        self.client = None
        if OPENAI_AVAILABLE and self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def route_intent(self, query):
        if POLICY_KEYWORDS_PATTERN.search(query):
            return "ROUTE_POLICY_RAG"
        return "ROUTE_GENERAL_CHAT"

    def format_rule_card(self, rule_res):
        if not rule_res.get("has_rule_evaluation"):
            return ""
        card = "【📊 校规结构化硬规则诊断报告】:\n"
        for item in rule_res["evaluations"]:
            status_icon = "合格/符合" if item["passed"] else "未达标/不符合"
            card += f"• [{item['rule_name']}] - {status_icon}: {item['details']}\n"
        card += "\n"
        return card

    def answer_question(self, query, top_k=3, student_type="undergraduate", category=None, conversation_id="conv_default"):
        resolved_query = self.memory_manager.resolve_coreference(conversation_id, query, client=self.client, model_name=self.model_name)
        route = self.route_intent(resolved_query)
        
        if route == "ROUTE_GENERAL_CHAT":
            if self.client:
                try:
                    resp = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT_GENERAL},
                            {"role": "user", "content": query}
                        ]
                    )
                    ans = resp.choices[0].message.content
                except Exception:
                    ans = "你好！我是南昌大学规章制度智能问答助手。你可以向我咨询关于学籍管理、学士学位授予、奖学金评定、处分规定及推免保研等政策规章！"
            else:
                ans = "你好！我是南昌大学规章制度智能问答助手。你可以向我咨询关于学籍管理、学士学位授予、奖学金评定、处分规定及推免保研等政策规章！"
            
            self.memory_manager.add_message(conversation_id, "user", query)
            self.memory_manager.add_message(conversation_id, "assistant", ans)
            self.db_manager.save_message(conversation_id, "user", query, resolved_query=resolved_query)
            self.db_manager.save_message(conversation_id, "assistant", ans, route="GENERAL_CHAT", sources=[])

            return {
                "route": "GENERAL_CHAT",
                "query": query,
                "resolved_query": resolved_query,
                "answer": ans,
                "sources": []
            }

        # 1. 硬规则诊断
        rule_eval = self.rule_engine.evaluate_rules(resolved_query)
        rule_card_text = self.format_rule_card(rule_eval)

        # 2. 检索与重排序
        rewritten_q = self.rewriter.rewrite_query(resolved_query)
        candidates = self.vector_store.hybrid_query(
            query_text=rewritten_q,
            top_k=10,
            student_type=student_type,
            category=category
        )
        search_results = self.reranker.rerank(resolved_query, candidates, top_k=top_k)

        # 3. 精准防幻觉据答判定：只有当完全匹配不到搜索结果，或者命中超纲无关联关键词且得分极低(<0.01)时才拒答
        top_score = search_results[0]["rerank_score"] if search_results else 0
        is_out_of_domain = bool(OUT_OF_DOMAIN_PATTERN.search(resolved_query))

        if not search_results or top_score < 0.01 or (is_out_of_domain and top_score < 0.10):
            refusal_text = rule_card_text + REFUSAL_SAFETY_TEXT if rule_card_text else REFUSAL_SAFETY_TEXT
            self.memory_manager.add_message(conversation_id, "user", query)
            self.memory_manager.add_message(conversation_id, "assistant", refusal_text)
            self.db_manager.save_message(conversation_id, "user", query, resolved_query=resolved_query)
            self.db_manager.save_message(conversation_id, "assistant", refusal_text, route="POLICY_RAG", sources=[])
            return {
                "route": "POLICY_RAG",
                "query": query,
                "resolved_query": resolved_query,
                "answer": refusal_text,
                "sources": []
            }

        context_str = ""
        sources = []
        for idx, item in enumerate(search_results, 1):
            chunk = item["chunk"]
            source_tag = f"{chunk['doc_title']} ({chunk['chapter']} - {chunk['article']})"
            sources.append(source_tag)
            context_str += f"\n--- 参考片段 [{idx}] (相关度得分: {item.get('rerank_score', 0)}) ---\n"
            context_str += f"出处: {source_tag}\n"
            context_str += f"内容: {chunk['content']}\n"

        sources = list(dict.fromkeys(sources))
        user_prompt = f"{rule_card_text}【参考制度文档】:\n{context_str}\n\n【用户咨询问题】: {query}"

        if self.client:
            try:
                resp = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT_RAG},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2
                )
                answer_content = resp.choices[0].message.content
            except Exception as e:
                answer_content = rule_card_text + self.generate_mock_answer(search_results, sources)
        else:
            answer_content = rule_card_text + self.generate_mock_answer(search_results, sources)

        self.memory_manager.add_message(conversation_id, "user", query)
        self.memory_manager.add_message(conversation_id, "assistant", answer_content)
        self.db_manager.save_message(conversation_id, "user", query, resolved_query=resolved_query)
        self.db_manager.save_message(conversation_id, "assistant", answer_content, route="POLICY_RAG", sources=sources)

        return {
            "route": "POLICY_RAG",
            "query": query,
            "resolved_query": resolved_query,
            "answer": answer_content,
            "sources": sources
        }

    def stream_answer_question(self, query, top_k=3, student_type="undergraduate", category=None, conversation_id="conv_default"):
        resolved_query = self.memory_manager.resolve_coreference(conversation_id, query, client=self.client, model_name=self.model_name)
        route = self.route_intent(resolved_query)
        
        if route == "ROUTE_GENERAL_CHAT":
            sources = []
            yield json.dumps({"type": "metadata", "route": "GENERAL_CHAT", "sources": sources, "resolved_query": resolved_query}) + "\n"
            
            ans = "你好！我是南昌大学规章制度智能问答助手。你可以向我咨询关于学籍管理、学士学位授予、奖学金评定、处分规定及推免保研等政策规章！"
            full_content = ""
            if self.client:
                try:
                    stream_resp = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT_GENERAL},
                            {"role": "user", "content": query}
                        ],
                        stream=True
                    )
                    for chunk in stream_resp:
                        delta = chunk.choices[0].delta.content or ""
                        if delta:
                            full_content += delta
                            yield json.dumps({"type": "content", "delta": delta}) + "\n"
                    
                    self.memory_manager.add_message(conversation_id, "user", query)
                    self.memory_manager.add_message(conversation_id, "assistant", full_content)
                    self.db_manager.save_message(conversation_id, "user", query, resolved_query=resolved_query)
                    self.db_manager.save_message(conversation_id, "assistant", full_content, route="GENERAL_CHAT", sources=[])

                    yield json.dumps({"type": "done"}) + "\n"
                    return
                except Exception:
                    pass

            for char in ans:
                full_content += char
                yield json.dumps({"type": "content", "delta": char}) + "\n"
                time.sleep(0.015)
            
            self.memory_manager.add_message(conversation_id, "user", query)
            self.memory_manager.add_message(conversation_id, "assistant", full_content)
            self.db_manager.save_message(conversation_id, "user", query, resolved_query=resolved_query)
            self.db_manager.save_message(conversation_id, "assistant", full_content, route="GENERAL_CHAT", sources=[])

            yield json.dumps({"type": "done"}) + "\n"
            return

        # 1. 硬规则诊断
        rule_eval = self.rule_engine.evaluate_rules(resolved_query)
        rule_card_text = self.format_rule_card(rule_eval)

        # 2. 检索与重排序
        rewritten_q = self.rewriter.rewrite_query(resolved_query)
        candidates = self.vector_store.hybrid_query(
            query_text=rewritten_q,
            top_k=10,
            student_type=student_type,
            category=category
        )
        search_results = self.reranker.rerank(resolved_query, candidates, top_k=top_k)

        # 3. 精准防幻觉据答判定：只有当完全匹配不到搜索结果，或者命中超纲无关联关键词且得分极低(<0.01)时才拒答
        top_score = search_results[0]["rerank_score"] if search_results else 0
        is_out_of_domain = bool(OUT_OF_DOMAIN_PATTERN.search(resolved_query))

        if not search_results or top_score < 0.01 or (is_out_of_domain and top_score < 0.10):
            sources = []
            yield json.dumps({"type": "metadata", "route": "POLICY_RAG", "sources": sources, "resolved_query": resolved_query}) + "\n"
            refusal_text = rule_card_text + REFUSAL_SAFETY_TEXT if rule_card_text else REFUSAL_SAFETY_TEXT
            
            for char in refusal_text:
                yield json.dumps({"type": "content", "delta": char}) + "\n"
                time.sleep(0.01)

            self.memory_manager.add_message(conversation_id, "user", query)
            self.memory_manager.add_message(conversation_id, "assistant", refusal_text)
            self.db_manager.save_message(conversation_id, "user", query, resolved_query=resolved_query)
            self.db_manager.save_message(conversation_id, "assistant", refusal_text, route="POLICY_RAG", sources=[])

            yield json.dumps({"type": "done"}) + "\n"
            return

        sources = []
        context_str = ""
        for idx, item in enumerate(search_results, 1):
            chunk = item["chunk"]
            source_tag = f"{chunk['doc_title']} ({chunk['chapter']} - {chunk['article']})"
            sources.append(source_tag)
            context_str += f"\n--- 参考片段 [{idx}] ---\n出处: {source_tag}\n内容: {chunk['content']}\n"

        sources = list(dict.fromkeys(sources))
        yield json.dumps({"type": "metadata", "route": "POLICY_RAG", "sources": sources, "resolved_query": resolved_query}) + "\n"

        user_prompt = f"{rule_card_text}【参考制度文档】:\n{context_str}\n\n【用户咨询问题】: {query}"
        full_content = ""

        if self.client:
            try:
                stream_resp = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT_RAG},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2,
                    stream=True
                )
                for chunk in stream_resp:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        full_content += delta
                        yield json.dumps({"type": "content", "delta": delta}) + "\n"

                self.memory_manager.add_message(conversation_id, "user", query)
                self.memory_manager.add_message(conversation_id, "assistant", full_content)
                self.db_manager.save_message(conversation_id, "user", query, resolved_query=resolved_query)
                self.db_manager.save_message(conversation_id, "assistant", full_content, route="POLICY_RAG", sources=sources)

                yield json.dumps({"type": "done"}) + "\n"
                return
            except Exception as e:
                pass

        mock_answer = rule_card_text + self.generate_mock_answer(search_results, sources)
        for char in mock_answer:
            full_content += char
            yield json.dumps({"type": "content", "delta": char}) + "\n"
            time.sleep(0.015)
        
        self.memory_manager.add_message(conversation_id, "user", query)
        self.memory_manager.add_message(conversation_id, "assistant", full_content)
        self.db_manager.save_message(conversation_id, "user", query, resolved_query=resolved_query)
        self.db_manager.save_message(conversation_id, "assistant", full_content, route="POLICY_RAG", sources=sources)

        yield json.dumps({"type": "done"}) + "\n"

    def generate_mock_answer(self, search_results, sources):
        if not search_results:
            return "查阅现有规章制度库，未找到相关具体规定。"
        best_chunk = search_results[0]["chunk"]
        clean_lines = [l for l in best_chunk['content'].split('\n') if not l.startswith('---')]
        
        ans = f"根据《{best_chunk['doc_title']}》的相关规定：\n\n"
        ans += "\n".join(clean_lines)
        return ans

if __name__ == "__main__":
    rag = AdvancedRAGGenerator()
    
    print("--- 1. 验证用户截图中的提问（奖学金类型及其比例）---")
    r1 = rag.answer_question("南昌大学奖学金类型及其比例")
    print(r1["answer"])
    
    print("\n--- 2. 验证真正的超纲据答（宠物）---")
    r2 = rag.answer_question("南昌大学可以带宠物狗进教室上课吗？")
    print(r2["answer"])
