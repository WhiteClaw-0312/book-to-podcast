"""书籍 API"""
import json
import asyncio
from pathlib import Path
from typing import List
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import APIKey, Book, Chapter, UsageLog
from ..schemas import (
    BookResponse, BookStatusResponse, ChapterResponse,
    GenerateRequest, GenerateResponse, MessageResponse
)
from ..services import OCRService, LLMService, TTSService
from ..config import settings

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
    api_key: str = Form(...),
    db: Session = Depends(get_db)
):
    """上传书籍"""
    
    # 验证
    key = verify_api_key(api_key, db)
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "只支持 PDF 文件")
    
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
        api_key=api_key,
        title=file.filename.replace(".pdf", ""),
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
    
    return BookStatusResponse(
        id=book.id,
        title=book.title,
        status=book.status,
        total_chapters=book.total_chapters,
        completed_chapters=book.completed_chapters,
        ocr_progress=book.ocr_progress,
        script_progress=book.script_progress,
        audio_progress=book.audio_progress,
        error_message=book.error_message,
        chapters=[
            ChapterResponse(
                id=ch.id,
                number=ch.number,
                title=ch.title,
                status=ch.status,
                duration=ch.duration,
                has_audio=bool(ch.audio_path)
            ) for ch in chapters
        ]
    )


@router.post("/{book_id}/generate", response_model=GenerateResponse)
async def generate_podcast(
    book_id: str,
    request: GenerateRequest,
    db: Session = Depends(get_db)
):
    """生成播客"""
    
    # 验证
    key = verify_api_key(request.api_key, db)
    
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(404, "书籍不存在")
    
    if book.api_key != request.api_key:
        raise HTTPException(403, "无权操作此书籍")
    
    if book.status not in ["ready", "partial", "completed"]:
        raise HTTPException(400, f"书籍状态不正确: {book.status}")
    
    # 检查余额
    cost = len(request.chapters)
    if key.balance < cost:
        raise HTTPException(400, f"余额不足，需要 {cost} 次，当前余额 {key.balance} 次")
    
    # 扣费
    key.balance -= cost
    key.total_used += cost
    db.commit()
    
    # 启动生成任务
    run_generate_chapters(book_id, request.chapters, request.api_key)
    
    return GenerateResponse(
        message=f"开始生成 {cost} 章",
        cost=cost,
        estimated_time=cost * 180  # 约3分钟/章
    )


def run_generate_chapters(book_id: str, chapter_numbers: List[int], api_key: str):
    """同步包装函数，在新线程中运行"""
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