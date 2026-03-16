"""书籍 API"""
import json
import asyncio
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import APIKey, Book, Chapter, UsageLog, User, TaskQueue, PromptTemplate
from ..schemas import (
    BookResponse, BookStatusResponse, ChapterResponse,
    GenerateRequest, GenerateResponse, MessageResponse
)
from ..services import OCRService, LLMService, TTSService
from ..config import settings
from .auth import get_current_user, get_optional_user, active_tokens
from ..queue_service import queue_service, run_task_in_background

router = APIRouter(prefix="/api/books", tags=["books"])

# 服务实例
ocr_service = OCRService()
llm_service = LLMService()
tts_service = TTSService()


def verify_api_key(api_key: str, db: Session) -> APIKey:
    """验证 API Key"""
    key = db.query(APIKey).filter(APIKey.key == api_key).first()
    if not key:
        raise HTTPException(401, "无效的 API Key")
    if not key.is_active:
        raise HTTPException(403, "API Key 已禁用")
    return key


@router.post("", response_model=BookResponse)
async def upload_book(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
):
    """上传书籍（支持 token 认证）"""
    
    # 验证登录
    if not user:
        raise HTTPException(401, "请先登录")
    
    # 获取用户的 API Key
    api_key = user.api_key
    key = verify_api_key(api_key, db)
    
    # 支持多种文件格式
    allowed_extensions = ['.pdf', '.txt', '.md']
    file_ext = '.' + file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    
    if file_ext not in allowed_extensions:
        raise HTTPException(400, f"只支持 {'/'.join(allowed_extensions)} 文件")
    
    if file.size and file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(400, "文件大小超过限制（100MB）")
    
    # 生成 ID
    import uuid
    book_id = uuid.uuid4().hex[:8]
    
    # 保存文件
    file_path = settings.UPLOADS_DIR / f"{book_id}_{file.filename}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # 创建记录
    book = Book(
        id=book_id,
        api_key=api_key,  # 使用用户的 api_key
        title=file.filename.rsplit('.', 1)[0],  # 去掉扩展名
        filename=file.filename,
        file_path=str(file_path),
        status="pending"
    )
    db.add(book)
    db.commit()
    
    # 直接启动后台线程
    run_process_book(book_id)
    
    return BookResponse(
        id=book.id,
        title=book.title,
        author=book.author,
        status=book.status,
        total_chapters=0,
        completed_chapters=0,
        created_at=book.created_at,
        expires_at=book.expires_at
    )


def run_process_book(book_id: str):
    """同步包装函数，在新线程中运行"""
    import threading
    import asyncio
    
    def run_in_thread():
        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(process_book(book_id))
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()


async def process_book(book_id: str):
    """处理书籍（后台任务）"""
    from ..database import SessionLocal
    
    db = SessionLocal()
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            return
        
        # OCR
        book.status = "ocr"
        db.commit()
        
        text, used_ocr = await ocr_service.extract_text(book.file_path)
        
        # 提取章节
        chapters_data = ocr_service.extract_chapters(text)
        
        book.total_chapters = len(chapters_data)
        book.status = "ready"
        book.ocr_progress = 100
        
        # 保存章节
        for ch in chapters_data:
            chapter = Chapter(
                book_id=book_id,
                number=ch["number"],
                title=ch["title"],
                content=ch["content"][:8000],  # 限制长度
                status="pending"
            )
            db.add(chapter)
        
        db.commit()
        
    except Exception as e:
        book = db.query(Book).filter(Book.id == book_id).first()
        if book:
            book.status = "failed"
            book.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.get("/{book_id}", response_model=BookStatusResponse)
async def get_book_status(book_id: str, db: Session = Depends(get_db)):
    """获取书籍状态"""
    
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(404, "书籍不存在")
    
    chapters = db.query(Chapter).filter(Chapter.book_id == book_id).order_by(Chapter.number).all()
    
    # 获取队列进度
    queue_progress = queue_service.get_book_progress(db, book_id)
    
    # 获取任务列表
    tasks = queue_service.get_book_tasks(db, book_id)
    
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "status": book.status,
        "total_chapters": book.total_chapters,
        "completed_chapters": book.completed_chapters,
        "ocr_progress": book.ocr_progress,
        "script_progress": book.script_progress,
        "audio_progress": book.audio_progress,
        "error_message": book.error_message,
        "prompt_id": book.prompt_id,
        "queue": queue_progress,
        "tasks": tasks,
        "chapters": [
            {
                "id": ch.id,
                "number": ch.number,
                "title": ch.title,
                "status": ch.status,
                "duration": ch.duration,
                "has_script": bool(ch.script),
                "has_audio": bool(ch.audio_path)
            } for ch in chapters
        ]
    }


@router.patch("/{book_id}")
async def update_book(
    book_id: str,
    data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """更新书籍设置（如 prompt_id）"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(404, "书籍不存在")
    
    # 验证权限
    if book.api_key != user.api_key:
        raise HTTPException(403, "无权修改此书籍")
    
    # 更新允许的字段
    if "prompt_id" in data:
        book.prompt_id = data["prompt_id"]
    
    db.commit()
    db.refresh(book)
    
    return {"message": "更新成功", "book_id": book_id, "prompt_id": book.prompt_id}


@router.get("/{book_id}/progress")
async def get_book_progress(book_id: str, db: Session = Depends(get_db)):
    """获取生成进度（用于轮询）"""
    
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(404, "书籍不存在")
    
    # 获取队列进度
    queue_progress = queue_service.get_book_progress(db, book_id)
    
    # 获取任务列表
    tasks = queue_service.get_book_tasks(db, book_id)
    
    # 计算整体进度
    total_progress = queue_progress["progress"]
    
    return {
        "book_id": book_id,
        "book_status": book.status,
        "queue": queue_progress,
        "tasks": tasks,
        "overall_progress": total_progress,
        "message": queue_progress.get("message", "")
    }


@router.post("/{book_id}/generate-script", response_model=GenerateResponse)
async def generate_script_only(
    book_id: str,
    request: GenerateRequest,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
):
    """生成文稿（加入队列，异步处理）"""
    
    if not user:
        raise HTTPException(401, "请先登录")
    
    api_key = user.api_key
    key = verify_api_key(api_key, db)
    
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(404, "书籍不存在")
    
    if book.api_key != api_key:
        raise HTTPException(403, "无权操作此书籍")
    
    # 创建任务队列
    for chapter_num in request.chapters:
        queue_service.create_task(db, book_id, chapter_num, "script")
    
    # 更新书籍状态
    book.status = "generating_script"
    db.commit()
    
    # 启动后台任务
    for chapter_num in request.chapters:
        task = db.query(TaskQueue).filter(
            TaskQueue.book_id == book_id,
            TaskQueue.chapter_number == chapter_num,
            TaskQueue.task_type == "script",
            TaskQueue.status == "pending"
        ).order_by(TaskQueue.created_at.desc()).first()
        
        if task:
            run_task_in_background(task.id, "script", book_id, chapter_num)
    
    return GenerateResponse(
        message=f"已加入队列，开始生成 {len(request.chapters)} 章文稿",
        cost=0,
        estimated_time=len(request.chapters) * 60
    )


@router.post("/{book_id}/generate-audio", response_model=GenerateResponse)
async def generate_audio_only(
    book_id: str,
    request: GenerateRequest,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
):
    """生成音频（加入队列，异步处理）"""
    
    if not user:
        raise HTTPException(401, "请先登录")
    
    api_key = user.api_key
    key = verify_api_key(api_key, db)
    
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(404, "书籍不存在")
    
    # 检查余额
    total_balance = user.free_quota + key.balance
    cost = len(request.chapters)
    if total_balance < cost:
        raise HTTPException(400, f"余额不足，需要 {cost} 次，当前余额 {total_balance} 次")
    
    # 扣费
    if user.free_quota >= cost:
        user.free_quota -= cost
    else:
        remaining = cost - user.free_quota
        user.free_quota = 0
        key.balance -= remaining
    key.total_used += cost
    db.commit()
    
    # 创建任务队列
    from ..models import TaskQueue
    for chapter_num in request.chapters:
        queue_service.create_task(db, book_id, chapter_num, "audio")
    
    # 更新书籍状态
    book.status = "generating_audio"
    db.commit()
    
    # 启动后台任务
    for chapter_num in request.chapters:
        task = db.query(TaskQueue).filter(
            TaskQueue.book_id == book_id,
            TaskQueue.chapter_number == chapter_num,
            TaskQueue.task_type == "audio",
            TaskQueue.status == "pending"
        ).order_by(TaskQueue.created_at.desc()).first()
        
        if task:
            run_task_in_background(task.id, "audio", book_id, chapter_num, voice_mapping=request.voice_mapping if hasattr(request, 'voice_mapping') else None)
    
    return GenerateResponse(
        message=f"已加入队列，开始生成 {cost} 章音频",
        cost=cost,
        estimated_time=cost * 120
    )


@router.post("/{book_id}/generate", response_model=GenerateResponse)
async def generate_podcast(
    book_id: str,
    request: GenerateRequest,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
):
    """生成播客（支持 token 认证）"""
    
    # 验证登录
    if not user:
        raise HTTPException(401, "请先登录")
    
    # 获取用户的 API Key
    api_key = user.api_key
    key = verify_api_key(api_key, db)
    
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(404, "书籍不存在")
    
    if book.api_key != api_key:
        raise HTTPException(403, "无权操作此书籍")
    
    if book.status not in ["ready", "partial", "completed"]:
        raise HTTPException(400, f"书籍状态不正确: {book.status}")
    
    # 检查余额（免费额度 + 付费余额）
    total_balance = user.free_quota + key.balance
    cost = len(request.chapters)
    if total_balance < cost:
        raise HTTPException(400, f"余额不足，需要 {cost} 次，当前余额 {total_balance} 次")
    
    # 扣费（优先使用免费额度）
    if user.free_quota >= cost:
        user.free_quota -= cost
    else:
        remaining = cost - user.free_quota
        user.free_quota = 0
        key.balance -= remaining
    key.total_used += cost
    db.commit()
    
    # 启动生成任务
    run_generate_chapters(book_id, request.chapters, api_key)
    
    return GenerateResponse(
        message=f"开始生成 {cost} 章",
        cost=cost,
        estimated_time=cost * 180  # 约3分钟/章
    )


def run_generate_chapters(book_id: str, chapter_numbers: List[int], api_key: str):
    """同步包装函数，在新线程中运行（文稿+音频）"""
    import threading
    import asyncio
    
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(generate_chapters(book_id, chapter_numbers, api_key))
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()


def run_generate_script_only(book_id: str, chapter_numbers: List[int]):
    """只生成文稿"""
    import threading
    import asyncio
    
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(generate_script_only(book_id, chapter_numbers))
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()


def run_generate_audio_only(book_id: str, chapter_numbers: List[int], api_key: str):
    """只生成音频（文稿已存在）"""
    import threading
    import asyncio
    
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(generate_audio_only(book_id, chapter_numbers, api_key))
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()


async def generate_script_only(book_id: str, chapter_numbers: List[int]):
    """只生成文稿，不生成音频"""
    from ..database import SessionLocal
    
    db = SessionLocal()
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        
        for i, num in enumerate(chapter_numbers):
            chapter = db.query(Chapter).filter(
                Chapter.book_id == book_id,
                Chapter.number == num
            ).first()
            
            if not chapter:
                continue
            
            try:
                # 更新状态
                chapter.status = "generating_script"
                book.status = "generating_script"
                book.script_progress = int((i / len(chapter_numbers)) * 100)
                db.commit()
                
                # 生成文稿
                script = await llm_service.generate_script(
                    book_title=book.title,
                    author=book.author,
                    chapter_number=chapter.number,
                    chapter_title=chapter.title,
                    content=chapter.content or ""
                )
                
                chapter.script = json.dumps(script, ensure_ascii=False)
                chapter.status = "script_ready"  # 文稿就绪，等待用户编辑
                book.script_progress = int(((i + 1) / len(chapter_numbers)) * 100)
                db.commit()
                
            except Exception as e:
                chapter.status = "failed"
                chapter.error_message = str(e)
                db.commit()
        
        # 更新书籍状态
        ready_count = db.query(Chapter).filter(
            Chapter.book_id == book_id,
            Chapter.status == "script_ready"
        ).count()
        
        book.status = "script_ready" if ready_count == book.total_chapters else "partial"
        db.commit()
        
    finally:
        db.close()


async def generate_audio_only(book_id: str, chapter_numbers: List[int], api_key: str):
    """只生成音频（文稿已存在）"""
    from ..database import SessionLocal
    
    db = SessionLocal()
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        
        for i, num in enumerate(chapter_numbers):
            chapter = db.query(Chapter).filter(
                Chapter.book_id == book_id,
                Chapter.number == num
            ).first()
            
            if not chapter or not chapter.script:
                continue
            
            try:
                # 更新状态
                chapter.status = "generating_audio"
                book.status = "generating_audio"
                book.audio_progress = int((i / len(chapter_numbers)) * 100)
                db.commit()
                
                # 获取文稿
                script = json.loads(chapter.script)
                
                # 合成音频
                audio_dir = settings.PODCASTS_DIR / book_id
                audio_dir.mkdir(exist_ok=True)
                audio_path = str(audio_dir / f"chapter_{num:02d}.mp3")
                
                duration = await tts_service.synthesize_chapter(
                    script.get("dialogues", []),
                    audio_path
                )
                
                # 更新完成
                chapter.audio_path = audio_path
                chapter.duration = duration
                chapter.status = "completed"
                db.commit()
                
                # 记录用量
                log = UsageLog(
                    api_key=api_key,
                    book_id=book_id,
                    chapter_id=chapter.id,
                    action="generate_audio",
                    cost=1,
                    details=json.dumps({"chapter": num, "duration": duration})
                )
                db.add(log)
                db.commit()
                
            except Exception as e:
                chapter.status = "failed"
                chapter.error_message = str(e)
                db.commit()
        
        # 更新书籍状态
        completed = db.query(Chapter).filter(
            Chapter.book_id == book_id,
            Chapter.status == "completed"
        ).count()
        
        book.completed_chapters = completed
        book.status = "completed" if completed == book.total_chapters else "partial"
        book.audio_progress = 100
        db.commit()
        
    finally:
        db.close()


async def generate_chapters(book_id: str, chapter_numbers: List[int], api_key: str):
    """生成章节播客"""
    from ..database import SessionLocal
    
    db = SessionLocal()
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        
        for i, num in enumerate(chapter_numbers):
            chapter = db.query(Chapter).filter(
                Chapter.book_id == book_id,
                Chapter.number == num
            ).first()
            
            if not chapter:
                continue
            
            try:
                # 更新状态
                chapter.status = "processing"
                book.status = "processing"
                book.script_progress = int((i / len(chapter_numbers)) * 50)
                db.commit()
                
                # 生成文稿
                script = await llm_service.generate_script(
                    book_title=book.title,
                    author=book.author,
                    chapter_number=chapter.number,
                    chapter_title=chapter.title,
                    content=chapter.content or ""
                )
                
                chapter.script = json.dumps(script, ensure_ascii=False)
                book.script_progress = int(((i + 0.5) / len(chapter_numbers)) * 50)
                db.commit()
                
                # 合成音频
                audio_dir = settings.PODCASTS_DIR / book_id
                audio_dir.mkdir(exist_ok=True)
                audio_path = str(audio_dir / f"chapter_{num:02d}.mp3")
                
                async def progress_callback(current, total):
                    book.audio_progress = int(((i + current/total) / len(chapter_numbers)) * 50)
                    db.commit()
                
                duration = await tts_service.synthesize_chapter(
                    script.get("dialogues", []),
                    audio_path,
                    progress_callback
                )
                
                # 更新完成
                chapter.audio_path = audio_path
                chapter.duration = duration
                chapter.status = "completed"
                db.commit()
                
                # 记录用量
                log = UsageLog(
                    api_key=api_key,
                    book_id=book_id,
                    chapter_id=chapter.id,
                    action="generate",
                    cost=1,
                    details=json.dumps({"chapter": num, "duration": duration})
                )
                db.add(log)
                db.commit()
                
            except Exception as e:
                chapter.status = "failed"
                chapter.error_message = str(e)
                db.commit()
        
        # 更新书籍状态
        completed = db.query(Chapter).filter(
            Chapter.book_id == book_id,
            Chapter.status == "completed"
        ).count()
        
        book.completed_chapters = completed
        book.status = "completed" if completed == book.total_chapters else "partial"
        book.script_progress = 50
        book.audio_progress = 50
        db.commit()
        
    finally:
        db.close()


@router.get("/{book_id}/chapters/{chapter_num}/audio")
async def get_audio(book_id: str, chapter_num: int, db: Session = Depends(get_db)):
    """获取音频文件"""
    
    chapter = db.query(Chapter).filter(
        Chapter.book_id == book_id,
        Chapter.number == chapter_num
    ).first()
    
    if not chapter:
        raise HTTPException(404, "章节不存在")
    
    if not chapter.audio_path or not Path(chapter.audio_path).exists():
        raise HTTPException(404, "音频文件不存在")
    
    return FileResponse(
        chapter.audio_path,
        media_type="audio/mpeg",
        filename=f"chapter_{chapter_num:02d}.mp3"
    )


@router.get("/{book_id}/chapters/{chapter_num}/script")
async def get_script(book_id: str, chapter_num: int, db: Session = Depends(get_db)):
    """获取文稿"""
    
    chapter = db.query(Chapter).filter(
        Chapter.book_id == book_id,
        Chapter.number == chapter_num
    ).first()
    
    if not chapter:
        raise HTTPException(404, "章节不存在")
    
    if not chapter.script:
        raise HTTPException(404, "文稿不存在")
    
    return json.loads(chapter.script)


@router.put("/{book_id}/chapters/{chapter_num}/script")
async def update_script(
    book_id: str, 
    chapter_num: int, 
    data: dict,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
):
    """更新文稿（用户编辑后保存）"""
    
    if not user:
        raise HTTPException(401, "请先登录")
    
    chapter = db.query(Chapter).filter(
        Chapter.book_id == book_id,
        Chapter.number == chapter_num
    ).first()
    
    if not chapter:
        raise HTTPException(404, "章节不存在")
    
    # 保存用户编辑的文稿
    chapter.script = json.dumps(data.get("dialogues", []), ensure_ascii=False)
    chapter.script_edited = chapter.script  # 标记为用户编辑过
    db.commit()
    
    return {"message": "文稿已保存"}


@router.get("/my-books")
async def get_my_books(
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
):
    """获取用户的所有书籍（历史记录）"""
    
    if not user:
        raise HTTPException(401, "请先登录")
    
    # 查询用户的书籍
    books = db.query(Book).filter(
        Book.api_key == user.api_key
    ).order_by(Book.created_at.desc()).all()
    
    result = []
    for book in books:
        chapters = db.query(Chapter).filter(
            Chapter.book_id == book.id
        ).order_by(Chapter.number).all()
        
        result.append({
            "id": book.id,
            "title": book.title,
            "status": book.status,
            "total_chapters": book.total_chapters,
            "completed_chapters": book.completed_chapters,
            "created_at": book.created_at.isoformat() if book.created_at else None,
            "expires_at": book.expires_at.isoformat() if book.expires_at else None,
            "chapters": [
                {
                    "id": ch.id,
                    "number": ch.number,
                    "title": ch.title,
                    "status": ch.status,
                    "has_script": bool(ch.script),
                    "has_audio": bool(ch.audio_path),
                    "duration": ch.duration
                } for ch in chapters
            ]
        })
    
    return result