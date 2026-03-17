"""任务队列服务"""
import json
import asyncio
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from .models import TaskQueue, Book, Chapter
from .database import SessionLocal
from .services import OCRService, LLMService, TTSService
from .config import settings


class QueueService:
    """任务队列服务"""
    
    def __init__(self):
        self.ocr_service = OCRService()
        self.llm_service = LLMService()
        self.tts_service = TTSService()
        self.running = False
    
    def create_task(self, db: Session, book_id: str, chapter_number: int, task_type: str) -> TaskQueue:
        """创建任务"""
        task = TaskQueue(
            book_id=book_id,
            chapter_number=chapter_number,
            task_type=task_type,
            status="pending",
            progress=0
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task
    
    def update_task(self, db: Session, task_id: str, status: str = None, progress: int = None, message: str = None, result: str = None):
        """更新任务状态"""
        task = db.query(TaskQueue).filter(TaskQueue.id == task_id).first()
        if task:
            if status:
                task.status = status
                if status == "processing":
                    task.started_at = datetime.now()
                elif status in ["completed", "failed"]:
                    task.completed_at = datetime.now()
            if progress is not None:
                task.progress = progress
            if message:
                task.message = message
            if result:
                task.result = result
            db.commit()
    
    def get_book_tasks(self, db: Session, book_id: str) -> List[dict]:
        """获取书籍的所有任务"""
        tasks = db.query(TaskQueue).filter(TaskQueue.book_id == book_id).order_by(TaskQueue.created_at).all()
        return [
            {
                "id": t.id,
                "chapter_number": t.chapter_number,
                "task_type": t.task_type,
                "status": t.status,
                "progress": t.progress,
                "message": t.message,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "started_at": t.started_at.isoformat() if t.started_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None
            }
            for t in tasks
        ]
    
    def get_book_progress(self, db: Session, book_id: str) -> dict:
        """获取书籍整体进度"""
        tasks = db.query(TaskQueue).filter(TaskQueue.book_id == book_id).all()
        
        if not tasks:
            return {"total": 0, "completed": 0, "progress": 0, "status": "idle"}
        
        total = len(tasks)
        completed = len([t for t in tasks if t.status == "completed"])
        processing = len([t for t in tasks if t.status == "processing"])
        failed = len([t for t in tasks if t.status == "failed"])
        
        # 计算平均进度
        avg_progress = sum(t.progress for t in tasks) / total if total > 0 else 0
        
        # 确定状态
        if processing > 0:
            status = "processing"
        elif completed == total:
            status = "completed"
        elif failed == total:
            status = "failed"
        else:
            status = "pending"
        
        return {
            "total": total,
            "completed": completed,
            "processing": processing,
            "failed": failed,
            "progress": int(avg_progress),
            "status": status
        }
    
    def update_book_status(self, db: Session, book_id: str):
        """检查并更新书籍状态"""
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            return
        
        chapters = db.query(Chapter).filter(Chapter.book_id == book_id).all()
        if not chapters:
            return
        
        all_have_script = all(c.script for c in chapters)
        all_have_audio = all(c.audio_path for c in chapters)
        some_have_audio = any(c.audio_path for c in chapters)
        
        # 确定新状态
        new_status = book.status
        
        if all_have_audio:
            new_status = "completed"
        elif some_have_audio and all_have_script:
            new_status = "partial"
        elif all_have_script:
            new_status = "script_ready"
        elif book.status in ["script_ready", "completed", "partial"]:
            # 状态已经是最终状态，不回退
            pass
        
        if new_status != book.status:
            book.status = new_status
            db.commit()
    
    async def process_script_task(self, task_id: str, book_id: str, chapter_number: int):
        """处理文稿生成任务"""
        db = SessionLocal()
        try:
            self.update_task(db, task_id, status="processing", progress=0, message="开始生成文稿...")
            
            book = db.query(Book).filter(Book.id == book_id).first()
            chapter = db.query(Chapter).filter(
                Chapter.book_id == book_id,
                Chapter.number == chapter_number
            ).first()
            
            if not book or not chapter:
                self.update_task(db, task_id, status="failed", message="章节不存在")
                return
            
            self.update_task(db, task_id, progress=20, message="正在分析内容...")
            
            # 生成文稿
            script = await self.llm_service.generate_script(
                book_title=book.title,
                author=book.author,
                chapter_number=chapter.number,
                chapter_title=chapter.title,
                content=chapter.content or ""
            )
            
            self.update_task(db, task_id, progress=80, message="正在保存文稿...")
            
            # 保存文稿
            chapter.script = json.dumps(script, ensure_ascii=False)
            chapter.status = "script_ready"
            db.commit()
            
            # 更新书籍状态
            self.update_book_status(db, book_id)
            
            self.update_task(db, task_id, status="completed", progress=100, message="文稿生成完成", result=json.dumps({"chapter": chapter_number}))
            
        except Exception as e:
            self.update_task(db, task_id, status="failed", message=str(e))
        finally:
            db.close()
    
    async def process_audio_task(self, task_id: str, book_id: str, chapter_number: int, voice_mapping: dict = None):
        """处理音频生成任务"""
        db = SessionLocal()
        try:
            self.update_task(db, task_id, status="processing", progress=0, message="开始生成音频...")
            
            book = db.query(Book).filter(Book.id == book_id).first()
            chapter = db.query(Chapter).filter(
                Chapter.book_id == book_id,
                Chapter.number == chapter_number
            ).first()
            
            if not book or not chapter or not chapter.script:
                self.update_task(db, task_id, status="failed", message="文稿不存在")
                return
            
            self.update_task(db, task_id, progress=10, message="正在解析文稿...")
            
            # 获取文稿
            script = json.loads(chapter.script)
            
            self.update_task(db, task_id, progress=20, message="正在合成音频...")
            
            # 合成音频
            audio_dir = settings.PODCASTS_DIR / book_id
            audio_dir.mkdir(exist_ok=True)
            audio_path = str(audio_dir / f"chapter_{chapter_number:02d}.mp3")
            
            duration = await self.tts_service.synthesize_chapter(
                script.get("dialogues", []),
                audio_path
            )
            
            self.update_task(db, task_id, progress=90, message="正在保存音频...")
            
            # 更新章节
            chapter.audio_path = audio_path
            chapter.duration = duration
            chapter.status = "completed"
            db.commit()
            
            # 更新书籍状态
            self.update_book_status(db, book_id)
            
            self.update_task(db, task_id, status="completed", progress=100, message="音频生成完成", result=json.dumps({"chapter": chapter_number, "duration": duration}))
            
        except Exception as e:
            self.update_task(db, task_id, status="failed", message=str(e))
        finally:
            db.close()


# 全局队列服务实例
queue_service = QueueService()


def run_task_in_background(task_id: str, task_type: str, book_id: str, chapter_number: int, **kwargs):
    """在后台运行任务"""
    import threading
    import asyncio
    
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if task_type == "script":
                loop.run_until_complete(queue_service.process_script_task(task_id, book_id, chapter_number))
            elif task_type == "audio":
                loop.run_until_complete(queue_service.process_audio_task(task_id, book_id, chapter_number, kwargs.get("voice_mapping")))
        finally:
            loop.close()
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()