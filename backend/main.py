"""FastAPI 主入口"""
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from models.task import Task, UploadResponse, APIKeyConfig
from services.task_manager import task_manager
from services.processor import ProcessService
from utils.crypto import encrypt_api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 启动时
    print("🚀 Book to Podcast API 启动...")
    
    # 创建必要目录
    Path("data/tasks").mkdir(parents=True, exist_ok=True)
    Path("data/uploads").mkdir(parents=True, exist_ok=True)
    
    yield
    
    # 关闭时
    print("👋 Book to Podcast API 关闭...")


app = FastAPI(
    title="Book to Podcast API",
    description="将图书转换为播客音频的 API 服务",
    version="1.0.0",
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


# ==================== API 路由 ====================

@app.get("/")
async def root():
    """根路径"""
    return {"message": "Book to Podcast API", "version": "1.0.0"}


@app.post("/api/upload", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    qwen_api_key: str = "",
    qwen_tts_key: str = ""
):
    """
    上传 PDF 文件
    
    Args:
        file: PDF 文件
        qwen_api_key: Qwen API Key (用于 OCR 和文稿生成)
        qwen_tts_key: Qwen TTS API Key (用于语音合成)
    
    Returns:
        task_id: 任务 ID
    """
    # 验证文件
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只支持 PDF 文件")
    
    # 验证 API Key
    if not qwen_api_key or not qwen_tts_key:
        raise HTTPException(status_code=400, detail="请提供 API Key")
    
    # 创建任务
    task = task_manager.create_task(file.filename)
    
    # 加密存储 API Key
    task_manager.update_task(
        task.id,
        encrypted_qwen_key=encrypt_api_key(qwen_api_key),
        encrypted_tts_key=encrypt_api_key(qwen_tts_key)
    )
    
    # 读取文件内容
    content = await file.read()
    
    # 启动后台处理
    from utils.crypto import decrypt_api_key
    
    # 解密 API Key
    decrypted_qwen_key = decrypt_api_key(encrypt_api_key(qwen_api_key))
    decrypted_tts_key = decrypt_api_key(encrypt_api_key(qwen_tts_key))
    
    # 异步处理
    import asyncio
    processor = ProcessService(task.id, decrypted_qwen_key, decrypted_tts_key)
    asyncio.create_task(processor.process(content, file.filename))
    
    return UploadResponse(
        task_id=task.id,
        message="上传成功，开始处理"
    )


@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    """
    获取任务状态
    
    Args:
        task_id: 任务 ID
    
    Returns:
        任务状态和进度
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return {
        "id": task.id,
        "filename": task.filename,
        "book_title": task.book_title,
        "status": task.status.value,
        "progress": task.progress.model_dump(),
        "chapters": [ch.model_dump() for ch in task.chapters],
        "total_duration": task.total_duration,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat()
    }


@app.get("/api/tasks")
async def list_tasks(limit: int = 20):
    """
    获取任务列表
    
    Args:
        limit: 返回数量限制
    
    Returns:
        任务列表
    """
    tasks = task_manager.list_tasks(limit)
    return [
        {
            "id": t.id,
            "filename": t.filename,
            "book_title": t.book_title,
            "status": t.status.value,
            "total_duration": t.total_duration,
            "chapter_count": len(t.chapters),
            "created_at": t.created_at.isoformat()
        }
        for t in tasks
    ]


@app.get("/api/audio/{task_id}/{chapter_num}")
async def get_audio(task_id: str, chapter_num: str):
    """
    获取音频文件
    
    Args:
        task_id: 任务 ID
        chapter_num: 章节编号 (如 "01")
    
    Returns:
        音频文件
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    audio_path = Path("data") / task_id / "audio" / f"chapter_{chapter_num}.mp3"
    
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="音频文件不存在")
    
    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        filename=f"{task.book_title}_第{chapter_num}章.mp3"
    )


@app.get("/api/script/{task_id}/{chapter_num}")
async def get_script(task_id: str, chapter_num: str):
    """
    获取文稿内容
    
    Args:
        task_id: 任务 ID
        chapter_num: 章节编号
    
    Returns:
        文稿 JSON
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    script_path = Path("data") / task_id / "scripts" / f"chapter_{chapter_num}.json"
    
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="文稿不存在")
    
    import json
    with open(script_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.delete("/api/task/{task_id}")
async def delete_task(task_id: str):
    """
    删除任务
    
    Args:
        task_id: 任务 ID
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 删除文件
    import shutil
    task_dir = Path("data") / task_id
    if task_dir.exists():
        shutil.rmtree(task_dir)
    
    # 删除任务记录
    task_manager.delete_task(task_id)
    
    return {"message": "删除成功"}


# ==================== 静态文件 ====================

# 挂载前端静态文件（生产环境）
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dist)), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)