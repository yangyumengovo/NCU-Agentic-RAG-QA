import re
import json

class ConversationMemoryManager:
    """多轮对话记忆与指代消解管理器"""
    def __init__(self, max_history_turns=5):
        self.max_turns = max_history_turns
        self.memory_store = {}  # {conv_id: [{"role": "user"/"assistant", "content": "..."}]}

    def add_message(self, conv_id, role, content):
        if conv_id not in self.memory_store:
            self.memory_store[conv_id] = []
        
        self.memory_store[conv_id].append({"role": role, "content": content})
        
        # 截断保持最近 max_turns * 2 条记录
        if len(self.memory_store[conv_id]) > self.max_turns * 2:
            self.memory_store[conv_id] = self.memory_store[conv_id][-(self.max_turns * 2):]

    def get_history(self, conv_id):
        return self.memory_store.get(conv_id, [])

    def resolve_coreference(self, conv_id, query, client=None, model_name="deepseek-chat"):
        """
        基于历史对话进行指代消解与语义补全 (Coreference & Anaphora Resolution)
        """
        history = self.get_history(conv_id)
        if not history:
            return query

        # 判断是否包含需要指代消解的泛指/代词/追问关键词
        PRONOUN_PATTERN = re.compile(r'(它|这个|那个|其|该|此|那|那要|要求呢|影响吗|条件呢|怎么办呢|能拿吗)')
        is_followup = bool(PRONOUN_PATTERN.search(query)) or len(query.strip()) <= 10

        if not is_followup:
            return query

        # 如果配置了大模型，使用大模型执行高精度指代消解重构
        if client:
            try:
                formatted_history = ""
                for msg in history[-4:]:
                    role_name = "用户" if msg["role"] == "user" else "助手"
                    formatted_history += f"{role_name}: {msg['content']}\n"

                prompt = f"""你是一个专业的语言学与指代消解助手。请结合下方的多轮对话历史，将用户最新的简短追问重构为一个语义完整、脱离上下文也能被独立理解的查询问句。

【对话历史】:
{formatted_history}

【最新追问】: {query}

【重构要求】:
1. 替换或补全追问中的代词（如“它”、“这个”、“那”），明确指代的主体概念（如学士学位、保研资格、缓考申请等）。
2. 只输出重构后的独立问句，切勿包含任何解释说明文字。
"""
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1
                )
                resolved = response.choices[0].message.content.strip()
                print(f"[指代消解 LLM 重构] 原追问: '{query}' -> 重构后: '{resolved}'")
                return resolved
            except Exception as e:
                print(f"[指代消解 警告] LLM 重构异常: {e}")

        # 启发式规则兜底：从上一轮对话中提取核心概念补全
        last_user_msg = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
        if last_user_msg:
            # 提取上轮主题词（如学士学位、保研、奖学金等）
            topic_match = re.search(r'(学士学位|保研|推免|奖学金|学籍|重修|缺考|处分|GPA|绩点)', last_user_msg)
            if topic_match:
                topic = topic_match.group(1)
                resolved = f"关于{topic}：{query}"
                print(f"[指代消解 规则重构] 原追问: '{query}' -> 重构后: '{resolved}'")
                return resolved

        return query

    def clear(self, conv_id):
        if conv_id in self.memory_store:
            del self.memory_store[conv_id]

if __name__ == "__main__":
    mem = ConversationMemoryManager()
    cid = "test_session_01"
    
    # 模拟第一轮对话
    mem.add_message(cid, "user", "南昌大学申请学士学位的要求是什么？")
    mem.add_message(cid, "assistant", "根据《学士学位授予实施细则》，申请学士学位要求平均学分绩点（GPA）达到2.0以上...")
    
    # 模拟第二轮追问（含代词 "它"）
    query2 = "受过记过处分会影响它吗？"
    resolved2 = mem.resolve_coreference(cid, query2)
    print(f"原始追问: {query2}")
    print(f"消解结果: {resolved2}")
