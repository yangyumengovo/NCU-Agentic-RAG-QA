import re

# 高校口语化词汇到规范制度同义词/关联词的全面映射字典 (涵盖 12 大校规领域)
SYNONYM_DICTIONARY = {
    "挂科": "课程考核不及格 不合格 补考 重修 成绩记载",
    "保研": "推荐优秀应届本科毕业生免试攻读硕士学位研究生 推免 综合成绩 必修课无不及格",
    "处分": "违纪处分 警告 严重警告 记过 留校察看 开除学籍 撤销",
    "奖学金": "本科优秀学生奖学金 类别 比例 金额 特等奖学金 一等奖学金 二等奖学金 三等奖学金 国家奖学金 国家励志奖学金",
    "休学": "休学 复学 最长学习年限 停课治疗",
    "重修": "课程重修 补考不及格 重修费",
    "补考": "开学初补考 免费补考 缓考随补考取消考试资格",
    "毕业": "毕业要求 结业证书 换发毕业证书 学位授予",
    "学位": "学士学位 GPA 2.0 毕业论文查重 不授予",
    "转专业": "转专业 GPA 2.5 第一学年 不得转专业 跨类限制",
    "缺考": "缺考 缺课三分之一 旷课3次 取消考试资格",
    "请假": "请假手续 辅导员 3天 7天 销假 病假证明",
    "查重": "毕业论文查重 重合率 15% 30% 学术不端 取消答辩资格",
    "电器": "宿舍大功率电器 违禁电器 800W 限额功率 明火",
    "申诉": "学生申诉 处分异议 10个工作日 15个工作日 申诉委员会"
}

class QueryRewriter:
    def __init__(self):
        pass

    def rewrite_query(self, query):
        """
        Query 改写与扩展：
        1. 保持原始查询意图；
        2. 识别口语化关键词并进行标准化词汇扩充（Query Expansion）；
        3. 返回丰富后的扩展查询字符串。
        """
        expanded_keywords = []
        for word, expansion in SYNONYM_DICTIONARY.items():
            if word in query:
                expanded_keywords.append(expansion)

        if expanded_keywords:
            expanded_str = " ".join(expanded_keywords)
            rewritten_query = f"{query} ({expanded_str})"
        else:
            rewritten_query = query

        return rewritten_query

if __name__ == "__main__":
    rewriter = QueryRewriter()
    print("QueryRewriter 优化完成！")
