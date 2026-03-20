"""书籍 API"""
import json
import asyncio
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks, Header
from fastapi.responses import FileResponse, StreamingResponse
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
        
        # 使用新的 extract_text 方法（返回页面列表）
        text, used_ocr, pages = await ocr_service.extract_text(book.file_path)
        
        # 保存页面数据到书籍记录（用于后续重新分章和前端展示）
        # 每页保存前5000字符，足够覆盖大部分内容
        book.raw_text = text[:100000]  # 保存前100000字符
        book.pages_json = json.dumps([p[:5000] for p in pages], ensure_ascii=False)
        
        # 智能章节提取
        chapters_data = await ocr_service.extract_chapters_smart(text, pages)
        
        book.total_chapters = len(chapters_data)
        book.status = "ready"
        book.ocr_progress = 100
        
        # 保存章节
        for ch in chapters_data:
            # 内容限制放宽到 15000 字符（约 5000 字）
            content = ch.get("content", "")
            if len(content) > 15000:
                content = content[:15000] + "\n\n... (内容已截断)"
            
            chapter = Chapter(
                book_id=book_id,
                number=ch["number"],
                title=ch["title"][:100],  # 标题限制100字符
                content=content,
                page_range=ch.get("page_range", ""),
                status="pending"
            )
            db.add(chapter)
        
        db.commit()
        
        print(f"✅ 书籍处理完成: {book.title}, {len(chapters_data)} 章")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        book = db.query(Book).filter(Book.id == book_id).first()
        if book:
            book.status = "failed"
            book.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.get("/my-books")
async def get_my_books(
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
):
    """获取用户的所有书籍（历史记录）"""
    
    if not user:
        raise HTTPException(401, "请先登录")
    
    # 自动清理7天前的任务
    from datetime import datetime, timedelta
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    old_books = db.query(Book).filter(
        Book.api_key == user.api_key,
        Book.created_at < seven_days_ago
    ).all()
    
    for old_book in old_books:
        # 删除相关章节
        db.query(Chapter).filter(Chapter.book_id == old_book.id).delete()
        # 删除书籍记录
        db.delete(old_book)
    
    if old_books:
        db.commit()
        print(f"已清理 {len(old_books)} 个超过7天的任务")
    
    # 查询用户的书籍
    books = db.query(Book).filter(
        Book.api_key == user.api_key
    ).order_by(Book.created_at.desc()).all()
    
    result = []
    for book in books:
        chapters = db.query(Chapter).filter(
            Chapter.book_id == book.id
        ).order_by(Chapter.number).all()
        
        # 计算剩余天数
        days_remaining = 7
        if book.created_at:
            age = datetime.utcnow() - book.created_at
            days_remaining = max(0, 7 - age.days)
        
        result.append({
            "id": book.id,
            "title": book.title,
            "status": book.status,
            "total_chapters": book.total_chapters,
            "completed_chapters": book.completed_chapters,
            "created_at": book.created_at.isoformat() + "Z" if book.created_at else None,
            "expires_at": book.expires_at.isoformat() + "Z" if book.expires_at else None,
            "days_remaining": days_remaining,
            "chapters": [
                {
                    "id": ch.id,
                    "number": ch.number,
                    "title": ch.title,
                    "status": ch.status,
                    "word_count": len(ch.content) if ch.content else 0,
                    "has_script": bool(ch.script),
                    "has_audio": bool(ch.audio_path),
                    "duration": ch.duration
                } for ch in chapters
            ]
        })
    
    return result


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
                "content": ch.content[:500] if ch.content else "",  # 返回前500字符用于预览
                "word_count": len(ch.content) if ch.content else 0,  # 实际字数
                "page_range": ch.page_range,
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
            run_task_in_background(task.id, "audio", book_id, chapter_num, voice_mapping=request.voice_mapping)
    
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
async def get_audio(
    book_id: str, 
    chapter_num: int, 
    db: Session = Depends(get_db),
    range: Optional[str] = Header(None)
):
    """获取音频文件 - 支持 Range 请求实现跳转"""
    
    chapter = db.query(Chapter).filter(
        Chapter.book_id == book_id,
        Chapter.number == chapter_num
    ).first()
    
    if not chapter:
        raise HTTPException(404, "章节不存在")
    
    if not chapter.audio_path or not Path(chapter.audio_path).exists():
        raise HTTPException(404, "音频文件不存在")
    
    file_path = Path(chapter.audio_path)
    file_size = file_path.stat().st_size
    
    # 处理 Range 请求
    if range:
        # 解析 Range 头 (格式: bytes=start-end)
        start, end = 0, file_size - 1
        
        try:
            range_match = range.replace("bytes=", "").split("-")
            start = int(range_match[0]) if range_match[0] else 0
            end = int(range_match[1]) if range_match[1] else file_size - 1
        except:
            start, end = 0, file_size - 1
        
        # 确保范围有效
        start = max(0, start)
        end = min(file_size - 1, end)
        content_length = end - start + 1
        
        # 读取指定范围的文件内容
        async def iterfile():
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                chunk_size = 64 * 1024  # 64KB chunks
                while remaining > 0:
                    read_size = min(chunk_size, remaining)
                    data = f.read(read_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data
        
        return StreamingResponse(
            iterfile(),
            media_type="audio/mpeg",
            status_code=206,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
            }
        )
    
    # 无 Range 请求，返回完整文件
    return FileResponse(
        file_path,
        media_type="audio/mpeg",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
        }
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
    
    # 获取现有文稿结构
    existing_script = {}
    if chapter.script:
        try:
            existing_script = json.loads(chapter.script)
        except:
            pass
    
    # 更新 dialogues，保持完整结构
    dialogues = data.get("dialogues", [])
    existing_script["dialogues"] = dialogues
    existing_script["chapter_number"] = chapter_num
    existing_script["chapter_title"] = chapter.title
    
    chapter.script = json.dumps(existing_script, ensure_ascii=False)
    chapter.script_edited = chapter.script  # 标记为用户编辑过
    db.commit()
    
    return {"message": "文稿已保存"}


@router.delete("/{book_id}")
async def delete_book(
    book_id: str, 
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
):
    """删除书籍及其相关数据"""
    
    if not user:
        raise HTTPException(401, "请先登录")
    
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(404, "书籍不存在")
    
    # 验证用户权限
    if book.api_key != user.api_key:
        raise HTTPException(403, "无权删除此书籍")
    
    # 删除章节关联的文件
    chapters = db.query(Chapter).filter(Chapter.book_id == book_id).all()
    for ch in chapters:
        # 删除音频文件
        if ch.audio_path and Path(ch.audio_path).exists():
            try:
                Path(ch.audio_path).unlink()
            except:
                pass
    
    # 删除章节记录
    db.query(Chapter).filter(Chapter.book_id == book_id).delete()
    
    # 删除任务队列
    db.query(TaskQueue).filter(TaskQueue.book_id == book_id).delete()
    
    # 删除原文件
    if book.file_path and Path(book.file_path).exists():
        try:
            Path(book.file_path).unlink()
        except:
            pass
    
    # 删除书籍记录
    db.delete(book)
    db.commit()
    
    return {"message": "书籍已删除"}


# ==================== 章节管理 API ====================

@router.get("/{book_id}/chapters/{chapter_num}/content")
async def get_chapter_content(
    book_id: str, 
    chapter_num: int, 
    format: str = "md",
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
):
    """获取章节内容（支持 Markdown 格式）"""
    
    chapter = db.query(Chapter).filter(
        Chapter.book_id == book_id,
        Chapter.number == chapter_num
    ).first()
    
    if not chapter:
        raise HTTPException(404, "章节不存在")
    
    content = chapter.content or ""
    
    if format == "md":
        # 转换为 Markdown 格式
        md_content = f"# 第{chapter.number}章 {chapter.title}\n\n"
        if chapter.page_range:
            md_content += f"> 📄 页码范围：{chapter.page_range}\n\n"
        md_content += "---\n\n"
        md_content += content
        
        return {
            "number": chapter.number,
            "title": chapter.title,
            "content": md_content,
            "raw_content": content,
            "page_range": chapter.page_range,
            "word_count": len(content)
        }
    
    return {
        "number": chapter.number,
        "title": chapter.title,
        "content": content,
        "page_range": chapter.page_range,
        "word_count": len(content)
    }


@router.put("/{book_id}/chapters/{chapter_num}/content")
async def update_chapter_content(
    book_id: str, 
    chapter_num: int, 
    data: dict,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
):
    """更新章节内容"""
    
    if not user:
        raise HTTPException(401, "请先登录")
    
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(404, "书籍不存在")
    
    if book.api_key != user.api_key:
        raise HTTPException(403, "无权操作此书籍")
    
    chapter = db.query(Chapter).filter(
        Chapter.book_id == book_id,
        Chapter.number == chapter_num
    ).first()
    
    if not chapter:
        raise HTTPException(404, "章节不存在")
    
    # 更新内容
    if "content" in data:
        chapter.content = data["content"][:10000]  # 限制长度
    
    if "title" in data:
        chapter.title = data["title"][:255]
    
    db.commit()
    
    return {"message": "章节内容已更新", "chapter_number": chapter_num}


@router.post("/{book_id}/chapters/merge")
async def merge_chapters(
    book_id: str,
    data: dict,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
):
    """合并多个章节"""
    
    if not user:
        raise HTTPException(401, "请先登录")
    
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(404, "书籍不存在")
    
    if book.api_key != user.api_key:
        raise HTTPException(403, "无权操作此书籍")
    
    chapter_numbers = data.get("chapters", [])
    new_title = data.get("title", "")
    
    if len(chapter_numbers) < 2:
        raise HTTPException(400, "至少需要选择2个章节进行合并")
    
    # 获取要合并的章节
    chapters = db.query(Chapter).filter(
        Chapter.book_id == book_id,
        Chapter.number.in_(chapter_numbers)
    ).order_by(Chapter.number).all()
    
    if len(chapters) != len(chapter_numbers):
        raise HTTPException(400, "部分章节不存在")
    
    # 合并内容
    merged_content = "\n\n".join([ch.content or "" for ch in chapters])
    merged_title = new_title or f"第{chapters[0].number}-{chapters[-1].number}章"
    
    # 计算合并后的页码范围
    def parse_page_range(page_range: str) -> tuple:
        """解析页码范围，返回 (min_page, max_page)"""
        if not page_range:
            return (None, None)
        import re
        numbers = re.findall(r'\d+', page_range)
        if not numbers:
            return (None, None)
        nums = [int(n) for n in numbers]
        return (min(nums), max(nums))
    
    all_pages = []
    for ch in chapters:
        min_p, max_p = parse_page_range(ch.page_range)
        if min_p:
            all_pages.extend([min_p, max_p] if max_p else [min_p])
    
    if all_pages:
        merged_page_range = f"{min(all_pages)}-{max(all_pages)}"
    else:
        merged_page_range = ""
    
    # 删除旧章节
    for ch in chapters:
        db.delete(ch)
    
    # 创建新章节
    new_chapter = Chapter(
        book_id=book_id,
        number=chapters[0].number,
        title=merged_title,
        content=merged_content[:15000],
        page_range=merged_page_range,
        status="pending"
    )
    db.add(new_chapter)
    
    # 重新编号后续章节
    remaining_chapters = db.query(Chapter).filter(
        Chapter.book_id == book_id,
        Chapter.number > chapters[-1].number
    ).order_by(Chapter.number).all()
    
    offset = len(chapters) - 1
    for ch in remaining_chapters:
        ch.number -= offset
    
    # 更新书籍章节数
    book.total_chapters = db.query(Chapter).filter(Chapter.book_id == book_id).count()
    db.commit()
    
    # 返回更新后的章节列表
    updated_chapters = db.query(Chapter).filter(
        Chapter.book_id == book_id
    ).order_by(Chapter.number).all()
    
    return {
        "message": f"已合并 {len(chapters)} 个章节",
        "new_chapter_number": chapters[0].number,
        "total_chapters": book.total_chapters,
        "chapters": [
            {
                "id": ch.id,
                "number": ch.number,
                "title": ch.title,
                "content": ch.content[:500] if ch.content else "",
                "word_count": len(ch.content) if ch.content else 0,
                "page_range": ch.page_range,
                "status": ch.status,
                "has_script": bool(ch.script),
                "has_audio": bool(ch.audio_path)
            } for ch in updated_chapters
        ]
    }


@router.post("/{book_id}/chapters/{chapter_num}/split")
async def split_chapter(
    book_id: str,
    chapter_num: int,
    data: dict,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
):
    """拆分章节"""
    
    if not user:
        raise HTTPException(401, "请先登录")
    
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(404, "书籍不存在")
    
    if book.api_key != user.api_key:
        raise HTTPException(403, "无权操作此书籍")
    
    chapter = db.query(Chapter).filter(
        Chapter.book_id == book_id,
        Chapter.number == chapter_num
    ).first()
    
    if not chapter:
        raise HTTPException(404, "章节不存在")
    
    split_position = data.get("position", 0.5)  # 拆分位置（0-1）
    first_title = data.get("first_title", f"第{chapter_num}章（上）")
    second_title = data.get("second_title", f"第{chapter_num}章（下）")
    
    content = chapter.content or ""
    split_index = int(len(content) * split_position)
    
    # 尝试在段落边界拆分
    for i in range(split_index, min(split_index + 500, len(content))):
        if content[i:i+2] == "\n\n":
            split_index = i
            break
    
    first_content = content[:split_index]
    second_content = content[split_index:]
    
    # 更新原章节
    chapter.title = first_title
    chapter.content = first_content
    
    # 创建新章节（插入到后面）
    # 先移动后面的章节
    later_chapters = db.query(Chapter).filter(
        Chapter.book_id == book_id,
        Chapter.number > chapter_num
    ).order_by(Chapter.number.desc()).all()
    
    for ch in later_chapters:
        ch.number += 1
    
    new_chapter = Chapter(
        book_id=book_id,
        number=chapter_num + 1,
        title=second_title,
        content=second_content,
        status="pending"
    )
    db.add(new_chapter)
    
    # 更新书籍章节数
    book.total_chapters = db.query(Chapter).filter(Chapter.book_id == book_id).count()
    db.commit()
    
    return {
        "message": "章节已拆分",
        "first_chapter": chapter_num,
        "second_chapter": chapter_num + 1,
        "total_chapters": book.total_chapters
    }


@router.post("/{book_id}/re-chapter")
async def re_chapter_book(
    book_id: str,
    data: dict,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
):
    """重新智能分章（使用 LLM）"""
    
    if not user:
        raise HTTPException(401, "请先登录")
    
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(404, "书籍不存在")
    
    if book.api_key != user.api_key:
        raise HTTPException(403, "无权操作此书籍")
    
    # 检查是否有页面数据
    if not book.pages_json:
        raise HTTPException(400, "没有可用的页面数据，请重新上传文件")
    
    # 解析页面数据
    pages = json.loads(book.pages_json)
    
    # 获取参数
    force_llm = data.get("force_llm", True)
    max_chapters = data.get("max_chapters", 0)  # 0 表示不限制
    
    # 删除旧章节
    db.query(Chapter).filter(Chapter.book_id == book_id).delete()
    
    # 异步执行重新分章
    run_re_chapter(book_id, pages, force_llm, max_chapters)
    
    return {"message": "正在重新分章..."}


def run_re_chapter(book_id: str, pages: List[str], force_llm: bool, max_chapters: int):
    """后台执行重新分章"""
    import threading
    import asyncio
    
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(do_re_chapter(book_id, pages, force_llm, max_chapters))
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()


async def do_re_chapter(book_id: str, pages: List[str], force_llm: bool, max_chapters: int):
    """执行重新分章"""
    from ..database import SessionLocal
    
    db = SessionLocal()
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            return
        
        book.status = "re_chaptering"
        db.commit()
        
        # 合并页面文本
        text = "\n\n".join([f"--- PAGE {i+1} ---\n{p}" for i, p in enumerate(pages)])
        
        # 智能分章
        chapters_data = await ocr_service.extract_chapters_smart(text, pages, force_llm=force_llm)
        
        # 如果设置了最大章节数，合并多余章节
        if max_chapters > 0 and len(chapters_data) > max_chapters:
            # 简单合并策略：将最后几个章节合并
            chapters_to_merge = len(chapters_data) - max_chapters + 1
            merged_content = "\n\n".join([ch["content"] for ch in chapters_data[-chapters_to_merge:]])
            chapters_data = chapters_data[:-chapters_to_merge]
            chapters_data.append({
                "number": max_chapters,
                "title": f"第{max_chapters}章",
                "content": merged_content[:15000]
            })
        
        # 保存新章节
        for ch in chapters_data:
            chapter = Chapter(
                book_id=book_id,
                number=ch["number"],
                title=ch["title"],
                content=ch["content"][:8000],
                page_range=ch.get("page_range", ""),
                status="pending"
            )
            db.add(chapter)
        
        book.total_chapters = len(chapters_data)
        book.status = "ready"
        db.commit()
        
    except Exception as e:
        book = db.query(Book).filter(Book.id == book_id).first()
        if book:
            book.status = "failed"
            book.error_message = f"重新分章失败: {str(e)}"
            db.commit()
    finally:
        db.close()


@router.get("/{book_id}/pages")
async def get_book_pages(
    book_id: str,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
):
    """获取书籍所有页面（用于手动调整章节）"""
    
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(404, "书籍不存在")
    
    if not book.pages_json:
        raise HTTPException(404, "没有可用的页面数据")
    
    pages = json.loads(book.pages_json)
    
    return {
        "total_pages": len(pages),
        "pages": [
            {"number": i + 1, "content": p[:500] + ("..." if len(p) > 500 else "")}
            for i, p in enumerate(pages)
        ]
    }


@router.post("/{book_id}/chapters/manual")
async def set_chapters_manual(
    book_id: str,
    data: dict,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
):
    """手动设置章节划分"""
    
    if not user:
        raise HTTPException(401, "请先登录")
    
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(404, "书籍不存在")
    
    if book.api_key != user.api_key:
        raise HTTPException(403, "无权操作此书籍")
    
    if not book.pages_json:
        raise HTTPException(400, "没有可用的页面数据")
    
    pages = json.loads(book.pages_json)
    chapters_config = data.get("chapters", [])
    
    if not chapters_config:
        raise HTTPException(400, "请提供章节配置")
    
    # 删除旧章节
    db.query(Chapter).filter(Chapter.book_id == book_id).delete()
    
    # 根据配置创建新章节
    for i, ch_config in enumerate(chapters_config):
        start_page = ch_config.get("start_page", 1) - 1
        end_page = ch_config.get("end_page", len(pages))
        
        content = "\n\n".join(pages[start_page:end_page])
        
        chapter = Chapter(
            book_id=book_id,
            number=i + 1,
            title=ch_config.get("title", f"第{i+1}章"),
            content=content[:15000],
            page_range=f"{start_page + 1}-{end_page}",
            status="pending"
        )
        db.add(chapter)
    
    book.total_chapters = len(chapters_config)
    db.commit()
    
    return {
        "message": f"已设置 {len(chapters_config)} 个章节",
        "total_chapters": book.total_chapters
    }