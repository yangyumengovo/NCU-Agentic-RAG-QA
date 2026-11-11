import re

class RuleGuidedEngine:
    """
    结构化硬规则查验小引擎 (Rule-Guided Hard-Rule Validator)
    基于精确正则数值提取与校规逻辑算符，对 GPA、处分、查重率、电器功率等提出诊断分析
    """
    def __init__(self):
        pass

    def evaluate_rules(self, query: str) -> dict:
        """
        解析用户提问中的数值参数，匹配硬规则并生成结构化诊断报告
        """
        results = []
        
        # 提取 GPA
        gpa_match = re.search(r'(?:gpa|绩点)[^\d]*([0-4](?:\.\d{1,2})?)', query, re.IGNORECASE)
        gpa_val = float(gpa_match.group(1)) if gpa_match else None

        # 提取处分
        has_punishment = bool(re.search(r'(处分|记过|警告|留校察看)', query))

        # 提取查重率
        similarity_match = re.search(r'(?:查重|重合度|重复率)[^\d]*(\d{1,2}(?:\.\d)?)\s*%', query)
        similarity_val = float(similarity_match.group(1)) if similarity_match else None

        # 提取电器功率
        power_match = re.search(r'(\d{3,4})\s*(?:w|瓦)', query, re.IGNORECASE)
        power_val = float(power_match.group(1)) if power_match else None

        # 规则 1: 转专业门槛诊断 (GPA >= 2.5 且无处分)
        if "转专业" in query and (gpa_val is not None or has_punishment):
            status = True
            reasons = []
            if gpa_val is not None:
                if gpa_val >= 2.5:
                    reasons.append(f"✅ GPA ({gpa_val}) 达到转专业门槛 (>= 2.5)")
                else:
                    status = False
                    reasons.append(f"❌ GPA ({gpa_val}) 未达到转专业门槛 (>= 2.5)")
            if has_punishment:
                status = False
                reasons.append("❌ 存在纪律处分记录，不符合转专业资格")

            results.append({
                "rule_name": "转专业资格规则校验",
                "passed": status,
                "details": "；".join(reasons)
            })

        # 规则 2: 学士学位授予诊断 (GPA >= 2.0)
        if "学位" in query and gpa_val is not None:
            status = gpa_val >= 2.0
            results.append({
                "rule_name": "学士学位 GPA 规则校验",
                "passed": status,
                "details": f"✅ GPA ({gpa_val}) 达到学位授予要求 (>= 2.0)" if status else f"❌ GPA ({gpa_val}) 低于学士学位最低标准 (< 2.0)"
            })

        # 规则 3: 毕业论文查重判定
        if similarity_val is not None:
            if similarity_val < 15.0:
                results.append({
                    "rule_name": "论文查重检测校验",
                    "passed": True,
                    "details": f"✅ 查重率 {similarity_val}% < 15%，属于合格范围，可直接参加答辩"
                })
            elif 15.0 <= similarity_val < 30.0:
                results.append({
                    "rule_name": "论文查重检测校验",
                    "passed": False,
                    "details": f"⚠️ 查重率 {similarity_val}% 在 15%~30% 之间，属于轻度抄袭，需修改后复查"
                })
            else:
                results.append({
                    "rule_name": "论文查重检测校验",
                    "passed": False,
                    "details": f"❌ 查重率 {similarity_val}% >= 30%，属于严重抄袭，取消当次答辩资格！"
                })

        # 规则 4: 宿舍电器功率检测
        if power_val is not None:
            status = power_val <= 800
            results.append({
                "rule_name": "宿舍违禁电器功率校验",
                "passed": status,
                "details": f"✅ 额定功率 {power_val}W 在安全限额范围内 (<= 800W)" if status else f"❌ 额定功率 {power_val}W 超过宿舍限额 (800W)，属于违禁电器！"
            })

        return {
            "has_rule_evaluation": len(results) > 0,
            "evaluations": results
        }

if __name__ == "__main__":
    engine = RuleGuidedEngine()
    test_q = "我的 GPA 是 2.3，且有一次记过处分，请问能申请转专业和学士学位吗？"
    res = engine.evaluate_rules(test_q)
    print("规则校验测试分析:")
    print(res)
