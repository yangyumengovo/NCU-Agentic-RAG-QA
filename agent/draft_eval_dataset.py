"""起草分层评测数据集 v2（审核稿生成器）。

设计：12 份文档全覆盖 × 4 种检索题型（直检/改述/数字/组合）+ 2 种 agent 级
题型（拒答/对比），共 53 题。每题锚定来源切片，ground_truth 由脚本从切片
原文自动带出——出题与锚定分离，避免标注错误。

题型说明：
- direct 直检：问题用词贴近原文（测 BM25 通道下限）
- paraphrase 改述：刻意口语化、词汇与原文错开（测语义通道真实价值）
- numeric 数字门槛：围绕具体数字/比例/期限（测精确匹配敏感度）
- combo 组合条件：多条件资格判断（测检索+规则组合）
- refusal 拒答：校园无关或语料外问题（测误答率，agent 级评测用）
- compare 对比：跨文档比较（agent 级评测用，不计入检索指标）

用法：python -m agent.draft_eval_dataset
输出：data/eval_dataset/ncu_qa_testset_v2.json（机器可读，含 review_status 字段）
      data/eval_dataset/ncu_qa_testset_v2_review.md（人工审核稿，每题附来源原文对照）
"""

import json
from datetime import date

from agent.config import CHUNKS_PATH

OUT_JSON = CHUNKS_PATH.parent.parent / "eval_dataset" / "ncu_qa_testset_v2.json"
OUT_MD = CHUNKS_PATH.parent.parent / "eval_dataset" / "ncu_qa_testset_v2_review.md"

# (题型, 难度, 问题, 锚定切片[(文档关键词, 条号), ...]，锚定多个=多目标题)
SPECS = [
    # ---- 1. 国家奖学金及国家励志奖学金评选办法 ----
    ("direct", "easy", "南昌大学国家奖学金的奖励金额是多少？申请需要满足哪些条件？", [("国家奖学金", "第一条")]),
    ("paraphrase", "medium", "我家里经济比较困难，成绩也还不错，学校有专门给困难学生的奖学金吗？要排到多少名才能拿？", [("国家奖学金", "第二条")]),
    ("direct", "easy", "国家奖学金的评审流程是怎样的？公示期是多久？", [("国家奖学金", "第三条")]),
    # ---- 2. 学生宿舍管理规定 ----
    ("paraphrase", "medium", "晚上学习回来太晚宿舍是不是就进不去了？门禁是几点？周末也一样吗？", [("宿舍管理", "第一条")]),
    ("paraphrase", "medium", "周末想让我同学来宿舍睡一晚可以吗？", [("宿舍管理", "第二条")]),
    ("numeric", "easy", "在宿舍用电器最多不能超过多少瓦？吹风机算违禁电器吗？", [("宿舍管理", "第三条")]),
    ("direct", "easy", "在宿舍使用违章电器会被怎么处理？", [("宿舍管理", "第四条"), ("违纪处分", "第八条")]),
    # ---- 3. 学生申诉处理办法 ----
    ("direct", "easy", "学生对学校的退学处理决定不服，可以向哪里提出申诉？", [("申诉处理", "第一条")]),
    ("numeric", "easy", "收到处分决定书之后多长时间内可以提出申诉？错过了会怎样？", [("申诉处理", "第三条"), ("违纪处分", "第十一条")]),
    ("paraphrase", "medium", "申诉交上去以后一般多久能有结果？在等结果的这段时间原来的处分还执行吗？", [("申诉处理", "第四条")]),
    # ---- 4. 学生请假与考勤管理办法 ----
    ("direct", "easy", "学校通过哪些方式进行课堂考勤？", [("请假与考勤", "第一条")]),
    ("numeric", "easy", "学生请病假5天需要谁来审批？要提交什么证明？", [("请假与考勤", "第二条")]),
    ("numeric", "medium", "一门课缺课累计超过多少比例就会失去考试资格？", [("请假与考勤", "第三条"), ("学籍管理", "第十一条")]),
    ("paraphrase", "medium", "老是翘课会有什么后果？翘多少个学时最严重会被开除？", [("请假与考勤", "第四条")]),
    # ---- 5. 学生违纪处分办法 ----
    ("direct", "easy", "南昌大学对学生违纪处分一共有哪几种？", [("违纪处分", "第四条")]),
    ("numeric", "easy", "记过处分的处分期是多久？处分期内有什么影响？", [("违纪处分", "第五条")]),
    ("paraphrase", "medium", "考试的时候找别人替我去考被抓到了会怎么处分？", [("违纪处分", "第六条")]),
    ("combo", "hard", "我上学期因为打架受到了记过处分，处分还没解除，今年还能申请国家奖学金吗？", [("违纪处分", "第五条"), ("国家奖学金", "第一条")]),
    # ---- 6. 推免（保研）实施办法 ----
    ("direct", "easy", "申请推免生对外语水平有什么要求？", [("推荐优秀应届", "第三条")]),
    ("numeric", "easy", "推免综合成绩是怎么计算的？学业成绩和综合素质各占多少？", [("推荐优秀应届", "第四条")]),
    ("direct", "easy", "哪些竞赛获奖可以给推免综合素质加分？", [("推荐优秀应届", "第六条")]),
    ("paraphrase", "medium", "想保研的话从申请到最终确定名单要经过哪些环节？名单要公示多久？", [("推荐优秀应届", "第七条")]),
    # ---- 7. 本科优秀学生奖学金评定办法 ----
    ("numeric", "easy", "二等奖学金和三等奖学金的金额与评选比例分别是多少？", [("优秀学生奖学金", "第四条")]),
    ("direct", "easy", "申请优秀学生奖学金对身体素质有什么要求？", [("优秀学生奖学金", "第五条")]),
    ("paraphrase", "medium", "要想拿到一等奖学金，成绩和综测大概要排到专业前多少？", [("优秀学生奖学金", "第六条")]),
    # ---- 8. 本科学生转专业实施办法 ----
    ("direct", "easy", "南昌大学转专业申请需要满足什么基本条件？", [("转专业实施", "第三条")]),
    ("combo", "hard", "我的GPA只有2.3，也没有受过处分，可以申请转专业吗？", [("转专业实施", "第三条")]),
    ("paraphrase", "medium", "我已经转过一次专业了，现在后悔了还能再转回去吗？", [("转专业实施", "第四条")]),
    ("direct", "easy", "转专业一般什么时候申请？可以同时报几个专业？", [("转专业实施", "第五条")]),
    ("paraphrase", "medium", "转专业成功之后，我原来专业修过的课还作数吗？", [("转专业实施", "第六条")]),
    # ---- 9. 学士学位授予实施细则 ----
    ("direct", "medium", "哪些情况下学校不授予学士学位？", [("学士学位", "第五条")]),
    ("direct", "medium", "因为处分原因拿不到学位的学生，还有机会补救吗？需要什么条件？", [("学士学位", "第六条")]),
    ("combo", "hard", "我修满了学分、毕业论文也及格了，但GPA只有1.9，能拿到学士学位吗？", [("学士学位", "第四条")]),
    ("paraphrase", "medium", "已经拿到学位的人后来被发现论文是找人代写的，学校还能把学位收回去吗？", [("学士学位", "第十条")]),
    # ---- 10. 学术不端行为处理办法 ----
    ("direct", "easy", "学校认定的学术不端行为包括哪些？", [("学术不端", "第一条")]),
    ("numeric", "easy", "毕业论文查重率达到多少会被认定为严重抄袭？25%的查重率会怎么处理？", [("学术不端", "第二条")]),
    ("paraphrase", "medium", "买论文或者找人代写被查出来了，毕业证和学位证还能保住吗？", [("学术不端", "第三条")]),
    # ---- 11. 本科生学籍管理办法 ----
    ("numeric", "easy", "百分制成绩85分换算成绩点是多少？60分以下呢？", [("学籍管理", "第九条")]),
    ("paraphrase", "medium", "一学期挂了好几门课，学校会不会直接把我退学？", [("学籍管理", "第二十条")]),
    ("paraphrase", "medium", "休学最长可以休几年？休学期间还算是在校生吗？", [("学籍管理", "第十八条")]),
    ("direct", "medium", "开学后没有按时办理注册会有什么后果？", [("学籍管理", "第七条")]),
    # ---- 12. 课程考核与成绩管理办法 ----
    ("direct", "easy", "期末考试不及格的话有补考机会吗？补考还不过怎么办？", [("课程考核", "第四条")]),
    ("numeric", "easy", "课程总评成绩里平时成绩一般占多大比例？", [("课程考核", "第二条")]),
    ("paraphrase", "medium", "考试前几天突然生病了没法参加期末考试，怎么申请缓考？", [("课程考核", "第三条")]),
    ("paraphrase", "medium", "感觉期末成绩打得有问题，可以申请重新核分查卷吗？", [("课程考核", "第五条")]),
]

# 拒答题：校园无关 / 语料库外，正确行为是拒答并说明（无检索目标，agent 级评测用）
REFUSAL = [
    ("easy", "食堂三楼的麻辣烫好不好吃？"),
    ("easy", "这周末南昌天气怎么样，适合去梅岭爬山吗？"),
    ("easy", "帮我写一篇大学英语四级的作文模板。"),
    ("easy", "英雄联盟赛季末怎么快速冲分上王者？"),
    ("medium", "南昌大学2026年在江西省的录取分数线是多少？"),  # 校园相关但不在12份制度内，测边界
]

# 对比题：跨文档比较（agent 级评测用，不计入检索指标）
COMPARE = [
    ("hard", "转专业和保研对成绩的要求有什么区别？哪个门槛更高？", [("转专业实施", "第三条"), ("推荐优秀应届", "第三条")]),
    ("hard", "国家奖学金和校特等奖学金哪个更难拿？要求有什么不同？", [("国家奖学金", "第一条"), ("优秀学生奖学金", "第六条")]),
    ("hard", "考试作弊和毕业论文抄袭的处分哪个更重？", [("违纪处分", "第六条"), ("学术不端", "第二条")]),
]


def find_chunk(doc_hint: str, article: str, chunks: list) -> tuple[int, dict]:
    hits = [
        (i, c)
        for i, c in enumerate(chunks)
        if doc_hint in c["doc_title"] and article in c["article"]
    ]
    if not hits:
        raise SystemExit(f"锚定失败: 找不到 {doc_hint} + {article}")
    return hits[0]


def main() -> None:
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        chunks = json.load(f)

    items, md = [], ["# 分层评测数据集 v2 · 审核稿", "",
                     f"> 生成日期 {date.today()} | 起草：LLM（锚定切片，答案自动带出）| 待人工审核",
                     "> 审核要点：①问题像不像真学生问的 ②改述题有没有偷懒照抄原文用词 ③答案是否就在下方原文里",
                     "> 每题审核后把 JSON 里对应条目的 review_status 改为 已确认 / 改写(直接改question) / 已删除", ""]

    qid = 0
    # 按文档分组渲染审核稿
    by_doc: dict[str, list] = {}
    for qtype, diff, question, anchors in SPECS:
        qid += 1
        resolved = [find_chunk(d, a, chunks) for d, a in anchors]
        items.append({
            "id": qid, "type": qtype, "difficulty": diff, "question": question,
            "target_doc": [c["doc_title"] for _, c in resolved] if len(resolved) > 1 else resolved[0][1]["doc_title"],
            "target_article": [c["article"].split(" ")[0] for _, c in resolved] if len(resolved) > 1 else resolved[0][1]["article"].split(" ")[0],
            "ground_truth": "\n\n".join(c["content"] for _, c in resolved),
            "source_chunk_ids": [i for i, _ in resolved],
            "review_status": "待审核",
        })
        by_doc.setdefault(resolved[0][1]["doc_title"], []).append((qid, qtype, diff, question, resolved))

    for doc, qs in by_doc.items():
        md.append(f"## {doc}")
        for qid_, qtype, diff, question, resolved in qs:
            md.append(f"\n**Q{qid_}** [{qtype}/{diff}] {question}")
            for i, c in resolved:
                md.append(f"- 锚定: {c['article']}")
                md.append(f"  原文: {c['content'][:220]}{'...' if len(c['content']) > 220 else ''}")
        md.append("")

    md.append("## 拒答题（正确行为：拒答并说明不在校规范围，Q50 预期说明\"制度库无相关规定\"）")
    for diff, question in REFUSAL:
        qid += 1
        items.append({"id": qid, "type": "拒答", "difficulty": diff, "question": question,
                      "expected_behavior": "拒答并说明不在校规咨询范围", "review_status": "待审核"})
        md.append(f"**Q{qid}** [拒答/{diff}] {question}")
    md.append("")

    md.append("## 对比题（agent 级评测用，不计入检索指标）")
    for diff, question, anchors in COMPARE:
        qid += 1
        resolved = [find_chunk(d, a, chunks) for d, a in anchors]
        items.append({"id": qid, "type": "对比", "difficulty": diff, "question": question,
                      "reference_docs": [c["doc_title"] for _, c in resolved],
                      "reference_chunk_ids": [i for i, _ in resolved],
                      "review_status": "待审核"})
        md.append(f"**Q{qid}** [对比/{diff}] {question}\n- 参考: {'; '.join(c['article'] for _, c in resolved)}")

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    md.append(f"\n\n共 {len(items)} 题（检索 {len(SPECS)} + 拒答 {len(REFUSAL)} + 对比 {len(COMPARE)}）")
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    from collections import Counter
    types = Counter(it["type"] for it in items)
    docs = Counter(it.get("target_doc") if isinstance(it.get("target_doc"), str) else it["target_doc"][0] for it in items if it["type"] in {"direct", "paraphrase", "numeric", "combo"})
    print(f"已生成 {len(items)} 题 -> {OUT_JSON.name} / {OUT_MD.name}")
    print("题型分布:", dict(types))
    print(f"检索题文档覆盖: {len(docs)}/12 份")
    for d, n in docs.most_common():
        print(f"  {n} 题  {d}")


if __name__ == "__main__":
    main()
