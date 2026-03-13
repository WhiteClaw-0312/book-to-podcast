#!/usr/bin/env python
"""
批量 OCR 处理脚本
"""
import os
import sys
import json
import base64
import openai
from pathlib import Path
from typing import List
import time

# 配置
QWEN_API_KEY = "sk-sp-24c19ee00acc4bae93d0983c74fa2854"
IMAGES_DIR = Path("data/images")
OUTPUT_FILE = Path("data/无语问上帝_全文_ocr.txt")

def get_existing_images() -> List[str]:
    """获取已有图片列表"""
    if not IMAGES_DIR.exists():
        return []
    return sorted([str(p) for p in IMAGES_DIR.glob("page_*.png")])

def ocr_single_image(image_path: str, client: openai.OpenAI) -> str:
    """OCR 单张图片"""
    with open(image_path, 'rb') as f:
        img_base64 = base64.b64encode(f.read()).decode()
    
    messages = [{
        'role': 'user',
        'content': [
            {'type': 'text', 'text': '请识别这张图片中的所有中文文字，保持原文格式，不要添加任何解释。'},
            {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{img_base64}'}}
        ]
    }]
    
    try:
        response = client.chat.completions.create(
            model='qwen3.5-plus',
            messages=messages,
            max_tokens=3000
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"  ❌ OCR 失败: {e}")
        return ""

def main():
    print("="*60, flush=True)
    print("📚 批量 OCR 处理", flush=True)
    print("="*60, flush=True)
    
    client = openai.OpenAI(
        api_key=QWEN_API_KEY,
        base_url="https://coding.dashscope.aliyuncs.com/v1"
    )
    
    # 获取图片列表
    images = get_existing_images()
    print(f"📷 找到 {len(images)} 张图片", flush=True)
    
    if not images:
        print("❌ 没有找到图片", flush=True)
        return
    
    # 检查已处理的进度
    progress_file = Path("data/ocr_progress.json")
    if progress_file.exists():
        with open(progress_file, 'r') as f:
            progress = json.load(f)
        processed = progress.get("processed", 0)
    else:
        processed = 0
    
    print(f"📝 从第 {processed + 1} 页开始处理", flush=True)
    
    # 批量处理
    all_results = []
    start_time = time.time()
    
    for i, img_path in enumerate(images[processed:], start=processed):
        print(f"  [{i+1}/{len(images)}] 处理: {Path(img_path).name}", flush=True)
        
        text = ocr_single_image(img_path, client)
        all_results.append(text)
        
        # 每 10 页保存一次进度
        if (i + 1) % 10 == 0:
            # 保存进度
            with open(progress_file, 'w') as f:
                json.dump({"processed": i + 1, "total": len(images)}, f)
            
            # 保存中间结果
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                f.write("\n\n--- PAGE BREAK ---\n\n".join(all_results))
            
            elapsed = time.time() - start_time
            avg_time = elapsed / (i + 1 - processed)
            remaining = (len(images) - i - 1) * avg_time
            print(f"  💾 已保存进度，预计剩余 {remaining/60:.1f} 分钟", flush=True)
        
        # 避免请求过快
        time.sleep(0.5)
    
    # 保存最终结果
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("\n\n--- PAGE BREAK ---\n\n".join(all_results))
    
    # 清理进度文件
    if progress_file.exists():
        progress_file.unlink()
    
    total_time = time.time() - start_time
    print(f"\n✅ 处理完成!", flush=True)
    print(f"📄 总页数: {len(images)}", flush=True)
    print(f"⏱️ 总耗时: {total_time/60:.1f} 分钟", flush=True)
    print(f"📝 输出文件: {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    main()