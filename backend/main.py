"""Book to Podcast API - v3.0
完整流程：OCR → 章节选择 → 生成选中章节
"""
import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

# 配置
API_KEY = "sk-sp-24c19ee00acc4bae93d0983c74fa2854"

app = FastAPI(title="Book to Podcast API", version="3.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 存储目录
DATA_DIR = Path("data/tasks")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 任务存储
tasks = {}


class GenerateRequest(BaseModel):
    chapters: List[int]


# ==================== 静态文件 ====================

@app.get("/", response_class=HTMLResponse)
async def index():
    """返回前端页面"""
    index_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Frontend not found</h1>"


# ==================== API ====================

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...), qwen_api_key: str = ""):
    """上传 PDF，进行 OCR 和章节提取"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "只支持 PDF 文件")
    
    if not qwen_api_key:
        qwen_api_key = API_KEY
    
    # 创建任务
    import uuid
    task_id = str(uuid.uuid4())[:8]
    task_dir = DATA_DIR / task_id
    task_dir.mkdir(parents=True)
    
    # 保存文件
    pdf_path = task_dir / file.filename
    with open(pdf_path, "wb") as f:
        f.write(await file.read())
    
    # 初始化任务状态
    tasks[task_id] = {
        "id": task_id,
        "status": "ocr",
        "progress": {"ocr": 0, "script": 0, "audio": 0, "messages": {"ocr": "开始OCR识别...", "script": "等待中", "audio": "等待中"}},
        "chapters": [],
        "created_at": datetime.now().isoformat()
    }
    
    # 异步处理
    asyncio.create_task(process_ocr(task_id, str(pdf_path), qwen_api_key))
    
    return {"task_id": task_id, "message": "上传成功"}


async def process_ocr(task_id: str, pdf_path: str, api_key: str):
    """OCR 处理"""
    task = tasks.get(task_id)
    if not task:
        return
    
    task_dir = DATA_DIR / task_id
    
    try:
        # PDF 转图片
        import fitz
        doc = fitz.open(pdf_path)
        total = len(doc)
        
        for i, page in enumerate(doc):
            progress = int((i + 1) / total * 100)
            task["progress"]["ocr"] = progress
            task["progress"]["messages"]["ocr"] = f"OCR 识别中... {i+1}/{total} 页"
            
            # TODO: 调用 OCR API
            await asyncio.sleep(0.1)
        
        doc.close()
        
        # 模拟章节提取（实际应调用 OCR API）
        chapters = extract_chapters_from_pdf(pdf_path)
        
        # 保存章节
        with open(task_dir / "chapters.json", "w", encoding="utf-8") as f:
            json.dump(chapters, f, ensure_ascii=False, indent=2)
        
        task["chapters"] = chapters
        task["status"] = "chapters_ready"
        task["progress"]["ocr"] = 100
        task["progress"]["messages"]["ocr"] = f"OCR 完成，识别到 {len(chapters)} 个章节"
        
    except Exception as e:
        task["status"] = "failed"
        task["error"] = str(e)


def extract_chapters_from_pdf(pdf_path: str) -> List[dict]:
    """从 PDF 提取章节（模拟）"""
    import fitz
    
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    doc.close()
    
    # 简单的章节识别
    import re
    chapters = []
    lines = text.split("\n")
    
    current_chapter = None
    current_content = []
    chapter_num = 0
    
    patterns = [
        r'^第[一二三四五六七八九十\d]+[部章节]',
        r'^[0-9]+\s*$',
    ]
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        is_chapter = any(re.match(p, line) for p in patterns) and len(line) < 30
        
        if is_chapter:
            if current_chapter:
                current_chapter["content"] = "\n".join(current_content)
                chapters.append(current_chapter)
            
            chapter_num += 1
            current_chapter = {"number": chapter_num, "title": line, "content": "", "selected": True}
            current_content = []
        else:
            if current_chapter:
                current_content.append(line)
    
    if current_chapter:
        current_chapter["content"] = "\n".join(current_content)
        chapters.append(current_chapter)
    
    return chapters if chapters else [{"number": 1, "title": "正文", "content": text[:5000], "selected": True}]


@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    """获取任务状态"""
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    return task


@app.post("/api/generate/{task_id}")
async def generate_chapters(task_id: str, request: GenerateRequest):
    """生成选中的章节"""
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    
    if task["status"] != "chapters_ready":
        raise HTTPException(400, "任务状态不正确")
    
    # 更新状态
    task["status"] = "script"
    task["selected_chapters"] = request.chapters
    task["progress"]["messages"]["script"] = "准备生成文稿..."
    
    # 异步生成
    asyncio.create_task(process_generation(task_id, request.chapters))
    
    return {"message": f"开始生成 {len(request.chapters)} 个章节"}


async def process_generation(task_id: str, chapter_numbers: List[int]):
    """生成文稿和音频"""
    task = tasks.get(task_id)
    if not task:
        return
    
    task_dir = DATA_DIR / task_id
    
    try:
        # 加载章节
        with open(task_dir / "chapters.json", "r", encoding="utf-8") as f:
            all_chapters = json.load(f)
        
        selected = [ch for ch in all_chapters if ch["number"] in chapter_numbers]
        total = len(selected)
        
        results = []
        
        for i, chapter in enumerate(selected):
            # 更新进度
            progress = int((i + 1) / total * 100)
            task["progress"]["script"] = progress
            task["progress"]["audio"] = 0
            task["progress"]["messages"]["script"] = f"生成文稿 {i+1}/{total}: {chapter['title']}"
            
            # 生成文稿
            script = await generate_script(chapter)
            
            # 保存文稿
            (task_dir / "scripts").mkdir(exist_ok=True)
            script_path = task_dir / "scripts" / f"chapter_{chapter['number']:02d}.json"
            with open(script_path, "w", encoding="utf-8") as f:
                json.dump(script, f, ensure_ascii=False, indent=2)
            
            # 更新音频进度
            task["progress"]["audio"] = 50
            task["progress"]["messages"]["audio"] = f"合成音频 {i+1}/{total}"
            
            # 合成音频
            (task_dir / "audio").mkdir(exist_ok=True)
            audio_path = task_dir / "audio" / f"chapter_{chapter['number']:02d}.mp3"
            duration = await synthesize_audio(script.get("dialogues", []), str(audio_path))
            
            results.append({
                "number": chapter["number"],
                "title": chapter["title"],
                "duration": duration
            })
        
        task["chapters"] = results
        task["status"] = "completed"
        task["progress"]["script"] = 100
        task["progress"]["audio"] = 100
        task["progress"]["messages"]["script"] = "文稿生成完成"
        task["progress"]["messages"]["audio"] = "音频合成完成"
        
    except Exception as e:
        task["status"] = "failed"
        task["error"] = str(e)


async def generate_script(chapter: dict) -> dict:
    """生成播客文稿"""
    import openai
    
    client = openai.OpenAI(
        api_key=API_KEY,
        base_url="https://coding.dashscope.aliyuncs.com/v1"
    )
    
    prompt = f"""将以下图书章节转换为双人对话式播客文案。

章节: 第 {chapter['number']} 章 - {chapter['title']}

内容:
{chapter['content'][:5000]}

要求:
1. 主持人: 小北（活泼好奇）和阿南（沉稳博学）
2. 格式: JSON
3. 约 40 句对话

输出 JSON:
{{"chapter_number": {chapter['number']}, "chapter_title": "{chapter['title']}", "dialogues": [{{"speaker": "小北", "content": "..."}}, ...]}}"""
    
    try:
        response = client.chat.completions.create(
            model="qwen3.5-plus",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=3000
        )
        
        result = response.choices[0].message.content
        
        import re
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"生成文稿失败: {e}")
    
    return {
        "chapter_number": chapter["number"],
        "chapter_title": chapter["title"],
        "dialogues": [
            {"speaker": "小北", "content": f"大家好，今天我们来看第{chapter['number']}章。"},
            {"speaker": "阿南", "content": f"这章的标题是「{chapter['title']}」。"}
        ]
    }


async def synthesize_audio(dialogues: List[dict], output_path: str) -> float:
    """合成音频"""
    temp_files = []
    output_dir = Path(output_path).parent
    
    for i, d in enumerate(dialogues):
        speaker = d.get("speaker", "小北")
        content = d.get("content", "")
        voice = "zh-CN-XiaoxiaoNeural" if speaker == "小北" else "zh-CN-YunxiNeural"
        temp_path = str(output_dir / f"temp_{i}.mp3")
        
        cmd = ["edge-tts", "--voice", voice, "--text", content, "--write-media", temp_path]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await proc.communicate()
        
        if Path(temp_path).exists() and Path(temp_path).stat().st_size > 0:
            temp_files.append(temp_path)
    
    if not temp_files:
        return 0
    
    # 合并
    list_file = output_dir / "merge.txt"
    with open(list_file, "w") as f:
        for af in temp_files:
            f.write(f"file '{Path(af).absolute()}'\n")
    
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", output_path]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await proc.communicate()
    
    # 清理
    for f in temp_files:
        Path(f).unlink(missing_ok=True)
    list_file.unlink(missing_ok=True)
    
    # 获取时长
    if Path(output_path).exists():
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", output_path],
            capture_output=True, text=True
        )
        try:
            return float(result.stdout.strip())
        except:
            return 0
    return 0


@app.get("/api/audio/{task_id}/{chapter_num}")
async def get_audio(task_id: str, chapter_num: str):
    """获取音频文件"""
    audio_path = DATA_DIR / task_id / "audio" / f"chapter_{chapter_num}.mp3"
    if not audio_path.exists():
        raise HTTPException(404, "音频不存在")
    return FileResponse(audio_path, media_type="audio/mpeg", filename=f"chapter_{chapter_num}.mp3")


@app.get("/api/script/{task_id}/{chapter_num}")
async def get_script(task_id: str, chapter_num: str):
    """获取文稿"""
    script_path = DATA_DIR / task_id / "scripts" / f"chapter_{chapter_num}.json"
    if not script_path.exists():
        raise HTTPException(404, "文稿不存在")
    with open(script_path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)