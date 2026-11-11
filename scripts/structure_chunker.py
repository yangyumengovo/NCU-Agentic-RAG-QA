import os
import re
import json

# 针对各规章制度的专属 Scope Metadata 映射配置
DOC_METADATA_CONFIG = {
    "南昌大学本科生学籍管理办法": {
        "student_type": "undergraduate",  # 本科生
        "degree_level": "bachelor",
        "category": "学籍管理"
    },
    "南昌大学本科毕业生学士学位授予实施细则": {
        "student_type": "undergraduate",
        "degree_level": "bachelor",
        "category": "学位授予"
    },
    "南昌大学本科优秀学生奖学金评定办法": {
        "student_type": "undergraduate",
        "degree_level": "bachelor",
        "category": "奖学金评定"
    },
    "南昌大学学生违纪处分办法": {
        "student_type": "all",            # 全员（包含本科生与研究生）
        "degree_level": "all",
        "category": "违纪处分"
    },
    "南昌大学推荐优秀应届本科毕业生免试攻读硕士学位研究生工作实施办法": {
        "student_type": "undergraduate",
        "degree_level": "bachelor",
        "category": "推免保研"
    },
    "南昌大学本科学生转专业实施办法": {
        "student_type": "undergraduate",
        "degree_level": "bachelor",
        "category": "转专业"
    },
    "南昌大学本科生课程考核与成绩管理办法": {
        "student_type": "undergraduate",
        "degree_level": "bachelor",
        "category": "课程考核"
    },
    "南昌大学学生宿舍管理规定": {
        "student_type": "all",
        "degree_level": "all",
        "category": "宿舍管理"
    },
    "南昌大学本科生学术不端行为处理办法": {
        "student_type": "undergraduate",
        "degree_level": "bachelor",
        "category": "学术规范"
    },
    "南昌大学学生请假与考勤管理办法": {
        "student_type": "all",
        "degree_level": "all",
        "category": "考勤请假"
    },
    "南昌大学国家奖学金及国家励志奖学金评选办法": {
        "student_type": "undergraduate",
        "degree_level": "bachelor",
        "category": "奖学金评定"
    },
    "南昌大学学生申诉处理办法": {
        "student_type": "all",
        "degree_level": "all",
        "category": "学生申诉"
    }
}

def parse_markdown_regulation(filepath):
    """
    丰富 Metadata 的“结构感知解析器”
    自动提取：doc_title, chapter, article, student_type, degree_level, category
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    doc_title = os.path.basename(filepath).replace('.md', '')
    scope_meta = DOC_METADATA_CONFIG.get(doc_title, {
        "student_type": "all",
        "degree_level": "all",
        "category": "通用规章"
    })

    current_chapter = "总则"
    current_article_title = ""
    current_article_content = []
    
    chunks = []
    
    chapter_pattern = re.compile(r'^##\s+(第[一二三四五六七八九十0-9]+章\s*.*)')
    article_pattern = re.compile(r'^###\s+(第[一二三四五六七八九十0-9]+条\s*.*)')
    
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
            
        chap_match = chapter_pattern.match(line_str)
        if chap_match:
            current_chapter = chap_match.group(1)
            continue
            
        art_match = article_pattern.match(line_str)
        if art_match:
            if current_article_content:
                text_block = "\n".join(current_article_content)
                chunk_text = f"【制度名称】{doc_title}\n【适用对象】{scope_meta['student_type']}\n【分类】{scope_meta['category']}\n【章节】{current_chapter}\n【条目】{current_article_title}\n【规定内容】\n{text_block}"
                chunks.append({
                    "doc_title": doc_title,
                    "chapter": current_chapter,
                    "article": current_article_title,
                    "student_type": scope_meta["student_type"],
                    "degree_level": scope_meta["degree_level"],
                    "category": scope_meta["category"],
                    "content": text_block,
                    "full_chunk_text": chunk_text
                })
                current_article_content = []
                
            current_article_title = art_match.group(1)
            continue
            
        if current_article_title:
            current_article_content.append(line_str)
            
    if current_article_content:
        text_block = "\n".join(current_article_content)
        chunk_text = f"【制度名称】{doc_title}\n【适用对象】{scope_meta['student_type']}\n【分类】{scope_meta['category']}\n【章节】{current_chapter}\n【条目】{current_article_title}\n【规定内容】\n{text_block}"
        chunks.append({
            "doc_title": doc_title,
            "chapter": current_chapter,
            "article": current_article_title,
            "student_type": scope_meta["student_type"],
            "degree_level": scope_meta["degree_level"],
            "category": scope_meta["category"],
            "content": text_block,
            "full_chunk_text": chunk_text
        })
        
    return chunks

def process_all_documents(input_dir, output_file):
    all_chunks = []
    for filename in os.listdir(input_dir):
        if filename.endswith('.md'):
            filepath = os.path.join(input_dir, filename)
            doc_chunks = parse_markdown_regulation(filepath)
            all_chunks.extend(doc_chunks)
            print(f"解析文档 [{filename}] 成功，生成 {len(doc_chunks)} 个富含 Metadata 的结构化切片。")
            
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
        
    print(f"\n处理完成！共生成 {len(all_chunks)} 个带作用域标签的 Chunk，已保存至 {output_file}")

if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    raw_dir = os.path.join(base_dir, "data", "raw_documents")
    output_json = os.path.join(base_dir, "data", "processed_chunks", "ncu_regulations_chunks.json")
    process_all_documents(raw_dir, output_json)
