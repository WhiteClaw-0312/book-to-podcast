#!/usr/bin/env python
"""
处理扫描版 PDF：PDF → 图片 → OCR → Skill → 播客文稿 → 音频
"""
import os
import sys
import json
import fitz  # PyMuPDF
import openai
from pathlib import Path
from typing import List, Dict
import base64
from io import BytesIO

# 配置
QWEN_API_KEY = "sk-sp-24c19ee00acc4bae93d0983c74fa2854"
QWEN_TTS_KEY = "sk-62a401c7f96448c4981f5f8aa937f7eb"
PDF_PATH = "data/books/无语问上帝.pdf"
OUTPUT_DIR = Path("data")

def pdf_to_images(pdf_path: str, output_dir: Path, dpi: int = 150, max_pages: int = None) -> List[str]:
    """将 PDF 转换为图片"""
    print(f"📄 转换 PDF 为图片: {pdf_path}", flush=True)
    
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    if max_pages:
        total_pages = min(total_pages, max_pages)
    
    image_paths = []
    
    for page_num in range(total_pages):
        page = doc[page_num]
        
        # 设置分辨率
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        
        # 保存图片
        image_path = images_dir / f"page_{page_num + 1:04d}.png"
        pix.save(str(image_path))
        image_paths.append(str(image_path))
        
        if (page_num + 1) % 20 == 0:
            print(f"  📷 已转换 {page_num + 1}/{total_pages} 页", flush=True)
    
    doc.close()
    print(f"✅ 图片转换完成: {len(image_paths)} 张")
    return image_paths

def ocr_images(image_paths: List[str], batch_size: int = 5) -> str:
    """使用 Qwen3.5-plus 视觉模型进行 OCR"""
    print(f"🔍 开始 OCR 识别...")
    
    client = openai.OpenAI(
        api_key=QWEN_API_KEY,
        base_url="https://coding.dashscope.aliyuncs.com/v1"
    )
    
    all_text = []
    total = len(image_paths)
    
    for i in range(0, total, batch_size):
        batch = image_paths[i:i+batch_size]
        
        # 读取图片并编码
        images_content = []
        for img_path in batch:
            with open(img_path, "rb") as f:
                img_base64 = base64.b64encode(f.read()).decode()
                images_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                })
        
        # 调用 Qwen 视觉模型
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "请识别这些图片中的所有中文文字，保持原文格式，不要添加任何解释。"},
                    *images_content
                ]
            }
        ]
        
        try:
            response = client.chat.completions.create(
                model="qwen3.5-plus",
                messages=messages,
                max_tokens=4000
            )
            
            text = response.choices[0].message.content
            all_text.append(text)
            
            print(f"  ✅ 已处理 {min(i + batch_size, total)}/{total} 页")
            
        except Exception as e:
            print(f"  ⚠️ 批次 {i//batch_size + 1} 失败: {e}")
    
    full_text = "\n\n".join(all_text)
    print(f"✅ OCR 完成: {len(full_text)} 字")
    return full_text

def extract_chapters(text: str) -> List[Dict]:
    """从文本中提取章节"""
    import re
    
    print("📖 分析章节结构...")
    
    chapters = []
    lines = text.split("\n")
    
    # 章节识别模式
    chapter_patterns = [
        r'^第[一二三四五六七八九十\d]+[部章]',
        r'^[0-9]+\s*$',
        r'^[一二三四五六七八九十]+[、.．]',
    ]
    
    current_chapter = None
    current_content = []
    chapter_num = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        is_chapter = any(re.match(p, line) for p in chapter_patterns)
        
        if is_chapter and len(line) < 30:
            if current_chapter and current_content:
                current_chapter["content"] = "\n".join(current_content)
                chapters.append(current_chapter)
            
            chapter_num += 1
            current_chapter = {
                "number": chapter_num,
                "title": line,
                "content": ""
            }
            current_content = []
        else:
            if current_chapter:
                current_content.append(line)
            elif len(current_content) < 10:
                current_content.append(line)
    
    if current_chapter and current_content:
        current_chapter["content"] = "\n".join(current_content)
        chapters.append(current_chapter)
    elif not chapters and current_content:
        chapters.append({
            "number": 1,
            "title": "正文",
            "content": "\n".join(current_content)
        })
    
    print(f"✅ 识别到 {len(chapters)} 个章节")
    return chapters

def generate_podcast_script(chapter: Dict, book_title: str, author: str) -> Dict:
    """生成单章播客文稿"""
    print(f"📝 生成第 {chapter['number']} 章文稿...")
    
    client = openai.OpenAI(
        api_key=QWEN_API_KEY,
        base_url="https://coding.dashscope.aliyuncs.com/v1"
    )
    
    prompt = f"""将以下图书章节转换为双人对话式播客文案。

书名: {book_title}
章节: 第 {chapter['number']} 章 - {chapter['title']}

内容:
{chapter['content'][:6000]}

要求:
1. 主持人: 小北（活泼好奇）和阿南（沉稳博学）
2. 格式: JSON，包含 dialogues 数组
3. 每句 30-50 字，总共约 50 句对话
4. 开场介绍主题，结尾总结要点

输出格式:
{{"chapter_number": {chapter['number']}, "chapter_title": "{chapter['title']}", "dialogues": [{{"speaker": "小北", "content": "..."}}, ...], "duration_estimate": 300}}

只输出 JSON:"""

    try:
        response = client.chat.completions.create(
            model="qwen3.5-plus",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4000
        )
        
        result = response.choices[0].message.content
        
        # 解析 JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            script = json.loads(json_match.group())
            print(f"  ✅ 完成: {len(script.get('dialogues', []))} 句对话")
            return script
    except Exception as e:
        print(f"  ⚠️ 失败: {e}")
    
    # 保底
    return {
        "chapter_number": chapter["number"],
        "chapter_title": chapter["title"],
        "dialogues": [
            {"speaker": "小北", "content": f"大家好，今天我们来读《{book_title}》的第{chapter['number']}章。"},
            {"speaker": "阿南", "content": f"这章的标题是「{chapter['title']}」"}
        ],
        "duration_estimate": 120
    }

def main():
    print("=" * 60)
    print("📚 图书转播客 - 无语问上帝")
    print("=" * 60)
    
    # Step 1: PDF → 图片 (先处理前 20 页测试)
    print("\nStep 1: PDF → 图片")
    image_paths = pdf_to_images(PDF_PATH, OUTPUT_DIR, dpi=150, max_pages=20)
    
    # Step 2: OCR 识别
    print("\nStep 2: 图片 → 文字 (OCR)")
    full_text = ocr_images(image_paths)
    
    # 保存全文
    text_path = OUTPUT_DIR / "无语问上帝_全文_ocr.txt"
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(full_text)
    print(f"📄 全文已保存: {text_path}")
    
    # Step 3: 提取章节
    print("\nStep 3: 提取章节")
    chapters = extract_chapters(full_text)
    
    # 保存 Skill
    skill_data = {
        "metadata": {
            "title": "无语问上帝",
            "author": "菲利普·杨西",
            "total_pages": len(image_paths),
            "total_chapters": len(chapters)
        },
        "chapters": chapters
    }
    
    skill_path = OUTPUT_DIR / "skills" / "无语问上帝_skill_full.json"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    with open(skill_path, "w", encoding="utf-8") as f:
        json.dump(skill_data, f, ensure_ascii=False, indent=2)
    print(f"📄 Skill 已保存: {skill_path}")
    
    # Step 4: 生成播客文稿（只生成第一章作为演示）
    print("\nStep 4: 生成播客文稿")
    scripts_dir = OUTPUT_DIR / "output" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    
    # 只处理前 3 章作为演示
    for chapter in chapters[:3]:
        script = generate_podcast_script(chapter, "无语问上帝", "菲利普·杨西")
        
        # 保存
        script_path = scripts_dir / f"chapter_{chapter['number']:02d}.json"
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(script, f, ensure_ascii=False, indent=2)
        
        # 保存 TXT
        txt_path = scripts_dir / f"chapter_{chapter['number']:02d}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            for d in script.get("dialogues", []):
                f.write(f"[{d['speaker']}]: {d['content']}\n\n")
    
    print("\n" + "=" * 60)
    print("✅ 处理完成!")
    print(f"章节: {len(chapters)}")
    print(f"文稿: 前 3 章已生成")
    print("=" * 60)

if __name__ == "__main__":
    main()