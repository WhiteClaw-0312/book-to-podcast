"""FastAPI 主入口"""
import os
import sys
import json
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from models.task import TaskStatus, ChapterInfo
from services.task_manager import task_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    print("🚀 Book to Podcast API 启动...")
    Path("data/tasks").mkdir(parents=True, exist_ok=True)
    Path("data/uploads").mkdir(parents=True, exist_ok=True)
    yield
    print("👋 Book to Podcast API 关闭...")


app = FastAPI(
    title="Book to Podcast API",
    description="将图书转换为播客音频的 API 服务",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 数据模型 ====================

class UploadResponse(BaseModel):
    task_id: str
    message: str
    chapter_count: int = 0


class GenerateRequest(BaseModel):
    chapters: List[int]  # 要生成的章节编号列表


class ChapterData(BaseModel):
    number: int
    title: str
    selected: bool = True


# ==================== API 路由 ====================

@app.get("/")
async def root():
    """根路径"""
    return {"message": "Book to Podcast API", "version": "2.0.0"}


@app.post("/api/upload", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    qwen_api_key: str = ""
):
    """
    上传 PDF 文件
    
    流程：
    1. 保存 PDF
    2. OCR 识别文字
    3. 提取章节结构
    4. 返回章节列表供用户选择
    """
    # 验证文件
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只支持 PDF 文件")
    
    if not qwen_api_key:
        raise HTTPException(status_code=400, detail="请提供 Qwen API Key")
    
    # 创建任务
    task = task_manager.create_task(file.filename)
    task_manager.update_task(
        task.id,
        qwen_api_key=qwen_api_key
    )
    
    # 读取文件内容
    content = await file.read()
    
    # 异步处理 OCR 和章节提取
    asyncio.create_task(process_ocr(task.id, content, file.filename, qwen_api_key))
    
    return UploadResponse(
        task_id=task.id,
        message="上传成功，正在识别文字...",
        chapter_count=0
    )


async def process_ocr(task_id: str, pdf_content: bytes, filename: str, api_key: str):
    """处理 OCR 和章节提取"""
    try:
        from services.simple_processor import SimpleProcessor
        
        processor = SimpleProcessor(task_id, api_key)
        chapters = await processor.process(pdf_content, filename)
        
        # 更新任务状态为"章节已准备好"
        task_manager.update_task(
            task_id,
            status="chapters_ready",
            chapters=[{
                "number": ch["number"],
                "title": ch["title"],
                "content": ch.get("content", "")[:200] + "...",
                "selected": True
            } for ch in chapters]
        )
        
        # 保存完整章节内容
        task_dir = Path("data") / task_id
        with open(task_dir / "chapters.json", "w", encoding="utf-8") as f:
            json.dump(chapters, f, ensure_ascii=False, indent=2)
        
    except Exception as e:
        task_manager.update_task(
            task_id,
            status=TaskStatus.FAILED,
            error=str(e)
        )


@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    """获取任务状态"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return {
        "id": task.id,
        "filename": task.filename,
        "book_title": task.book_title,
        "status": task.status.value if isinstance(task.status, TaskStatus) else task.status,
        "progress": task.progress.model_dump() if hasattr(task, 'progress') else {"progress": 0, "message": ""},
        "chapters": task.chapters if isinstance(task.chapters, list) else [],
        "total_duration": task.total_duration,
        "created_at": task.created_at.isoformat() if hasattr(task, 'created_at') else "",
    }


@app.post("/api/generate/{task_id}")
async def generate_chapters(task_id: str, request: GenerateRequest):
    """
    生成选中的章节
    
    Args:
        task_id: 任务 ID
        request.chapters: 要生成的章节编号列表
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status != "chapters_ready":
        raise HTTPException(status_code=400, detail="任务状态不正确")
    
    # 更新状态
    task_manager.update_task(
        task_id,
        status=TaskStatus.SCRIPT_GENERATING
    )
    
    # 异步生成
    asyncio.create_task(process_generation(task_id, request.chapters))
    
    return {"message": f"开始生成 {len(request.chapters)} 个章节"}


async def process_generation(task_id: str, chapter_numbers: List[int]):
    """处理文稿生成和音频合成"""
    try:
        from services.simple_processor import SimpleProcessor
        
        task = task_manager.get_task(task_id)
        api_key = task.qwen_api_key if hasattr(task, 'qwen_api_key') else ""
        
        processor = SimpleProcessor(task_id, api_key)
        
        # 加载章节
        task_dir = Path("data") / task_id
        with open(task_dir / "chapters.json", "r", encoding="utf-8") as f:
            all_chapters = json.load(f)
        
        # 只处理选中的章节
        chapters_to_process = [ch for ch in all_chapters if ch["number"] in chapter_numbers]
        
        # 更新进度
        total = len(chapters_to_process)
        
        for i, chapter in enumerate(chapters_to_process):
            progress = int((i / total) * 100)
            task_manager.update_progress(
                task_id,
                TaskStatus.AUDIO_SYNTHESIZING,
                progress,
                f"处理第 {i+1}/{total} 章: {chapter['title']}"
            )
            
            # 生成文稿
            script = await processor.generate_script(chapter)
            
            # 保存文稿
            script_dir = task_dir / "scripts"
            script_dir.mkdir(exist_ok=True)
            with open(script_dir / f"chapter_{chapter['number']:02d}.json", "w", encoding="utf-8") as f:
                json.dump(script, f, ensure_ascii=False, indent=2)
            
            # 生成音频
            audio_path = str(task_dir / "audio" / f"chapter_{chapter['number']:02d}.mp3")
            duration = await processor.synthesize_audio(script["dialogues"], audio_path)
            
            # 记录完成
            chapter_info = ChapterInfo(
                number=chapter["number"],
                title=chapter["title"],
                duration=duration,
                audio_url=f"/api/audio/{task_id}/{chapter['number']:02d}",
                script_url=f"/api/script/{task_id}/{chapter['number']:02d}"
            )
            task_manager.complete_chapter(task_id, chapter_info)
        
        task_manager.update_progress(
            task_id,
            TaskStatus.COMPLETED,
            100,
            "处理完成！"
        )
        
    except Exception as e:
        task_manager.update_task(
            task_id,
            status=TaskStatus.FAILED,
            error=str(e)
        )


@app.get("/api/audio/{task_id}/{chapter_num}")
async def get_audio(task_id: str, chapter_num: str):
    """获取音频文件"""
    audio_path = Path("data") / task_id / "audio" / f"chapter_{chapter_num}.mp3"
    
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="音频文件不存在")
    
    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        filename=f"chapter_{chapter_num}.mp3"
    )


@app.get("/api/script/{task_id}/{chapter_num}")
async def get_script(task_id: str, chapter_num: str):
    """获取文稿内容"""
    script_path = Path("data") / task_id / "scripts" / f"chapter_{chapter_num}.json"
    
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="文稿不存在")
    
    with open(script_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/tasks")
async def list_tasks(limit: int = 20):
    """获取任务列表"""
    tasks = task_manager.list_tasks(limit)
    return [
        {
            "id": t.id,
            "filename": t.filename,
            "book_title": t.book_title,
            "status": t.status.value if isinstance(t.status, TaskStatus) else t.status,
            "total_duration": t.total_duration,
            "chapter_count": len(t.chapters) if isinstance(t.chapters, list) else 0,
            "created_at": t.created_at.isoformat() if hasattr(t, 'created_at') else ""
        }
        for t in tasks
    ]


@app.delete("/api/task/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    import shutil
    task_dir = Path("data") / task_id
    if task_dir.exists():
        shutil.rmtree(task_dir)
    
    task_manager.delete_task(task_id)
    return {"message": "删除成功"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)