"""数据模型"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    OCR_PROCESSING = "ocr"          # OCR 处理中
    CHAPTERS_READY = "chapters_ready" # 章节已准备好（等待用户选择）
    SCRIPT_GENERATING = "script"     # 文稿生成中
    AUDIO_SYNTHESIZING = "audio"    # 音频合成中
    COMPLETED = "completed"
    FAILED = "failed"


class ChapterInfo(BaseModel):
    """章节信息"""
    number: int
    title: str
    duration: float = 0
    audio_url: Optional[str] = None
    script_url: Optional[str] = None


class TaskProgress(BaseModel):
    """任务进度"""
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    message: str = ""


class Task(BaseModel):
    """任务"""
    id: str
    filename: str
    book_title: str
    author: str = "未知"
    status: TaskStatus = TaskStatus.PENDING
    progress: TaskProgress = TaskProgress(status=TaskStatus.PENDING)
    chapters: List[ChapterInfo] = []
    total_duration: float = 0
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    error: Optional[str] = None
    
    # API Keys
    qwen_api_key: str = ""
    
    class Config:
        use_enum_values = True