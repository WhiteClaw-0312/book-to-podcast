#!/usr/bin/env python
"""
OCR 完成后自动启动并发处理
"""
import os
import sys
import json
import time
import re
from pathlib import Path

# 添加项目路径
sys.path.insert(0, '/home/admin/.openclaw/workspace/book-to-podcast')

from src.skills.book_to_podcast.concurrent_pipeline import run_concurrent_pipeline

# 配置
OCR_TEXT_FILE = Path("data/无语问上帝_全文_ocr.txt")
OCR_PROGRESS_FILE = Path("data/ocr_progress.json")
SKILL_FILE = Path("data/skills/无语问上帝_skill_full.json")

def wait_for_ocr():
    """等待 OCR 完成"""
    print("⏳ 等待 OCR 完成...", flush=True)
    
    while True:
        if OCR_PROGRESS_FILE.exists():
            with open(OCR_PROGRESS_FILE, 'r') as f:
                progress = json.load(f)
            
            processed = progress.get("processed", 0)
            total = progress.get("total", 256)
            
            print(f"  OCR 进度: {processed}/{total} ({processed*100//total}%)", flush=True)
            
            if processed >= total:
                print("✅ OCR 完成!", flush=True)
                return True
        else:
            print("  等待 OCR 开始...", flush=True)
        
        time.sleep(30)  # 每 30 秒检查一次

def extract_chapters_from_text(text: str) -> list:
    """从 OCR 文本提取章节"""
    print("📖 分析章节结构...", flush=True)
    
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
        if not line or line == "--- PAGE BREAK ---":
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
            elif len(current_content) < 20:
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
    
    print(f"✅ 识别到 {len(chapters)} 个章节", flush=True)
    return chapters

def create_skill_from_ocr():
    """从 OCR 结果创建 Skill"""
    print("\n📝 创建 Skill...", flush=True)
    
    # 读取 OCR 结果
    if not OCR_TEXT_FILE.exists():
        print(f"❌ OCR 文件不存在: {OCR_TEXT_FILE}", flush=True)
        return None
    
    with open(OCR_TEXT_FILE, 'r', encoding='utf-8') as f:
        full_text = f.read()
    
    print(f"📄 OCR 文本长度: {len(full_text)} 字", flush=True)
    
    # 提取章节
    chapters = extract_chapters_from_text(full_text)
    
    # 创建 Skill
    skill_data = {
        "metadata": {
            "title": "无语问上帝",
            "author": "菲利普·杨西",
            "total_pages": 256,
            "total_chapters": len(chapters),
            "word_count": len(full_text)
        },
        "chapters": chapters
    }
    
    # 保存
    SKILL_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SKILL_FILE, 'w', encoding='utf-8') as f:
        json.dump(skill_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Skill 已保存: {SKILL_FILE}", flush=True)
    return str(SKILL_FILE)

def main():
    print("="*60, flush=True)
    print("📚 图书转播客 - 自动处理流程", flush=True)
    print("="*60, flush=True)
    
    # Step 1: 等待 OCR 完成
    print("\nStep 1: 等待 OCR 完成", flush=True)
    wait_for_ocr()
    
    # Step 2: 创建 Skill
    print("\nStep 2: 创建 Skill", flush=True)
    skill_path = create_skill_from_ocr()
    
    if not skill_path:
        print("❌ 创建 Skill 失败", flush=True)
        return
    
    # Step 3: 并发处理（文稿生成 + 音频合成）
    print("\nStep 3: 并发处理文稿和音频", flush=True)
    results = run_concurrent_pipeline(skill_path)
    
    # Step 4: 汇总
    print("\n" + "="*60, flush=True)
    print("📊 最终结果", flush=True)
    print("="*60, flush=True)
    
    success_count = sum(1 for r in results if r.success)
    total_duration = sum(r.duration for r in results if r.success)
    
    print(f"✅ 成功: {success_count}/{len(results)} 章", flush=True)
    print(f"⏱️ 总时长: {total_duration/60:.1f} 分钟", flush=True)
    print(f"📁 文稿目录: {Path('data/output/scripts').absolute()}", flush=True)
    print(f"📁 音频目录: {Path('data/output/audio').absolute()}", flush=True)

if __name__ == "__main__":
    main()