"""数据模型"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"           # 等待处理
    UPLOADING = "uploading"       # 上传中
    OCR_PROCESSING = "ocr"        # OCR 处理中
    SCRIPT_GENERATING = "script"  # 文稿生成中
    AUDIO_SYNTHESIZING = "audio"  # 音频合成中
    COMPLETED = "completed"        # 已完成
    FAILED = "failed"             # 失败


class ChapterInfo(BaseModel):
    """章节信息"""
    number: int
    title: str
    duration: float = 0
    audio_url: Optional[str] = None
    script_url: Optional[str] = None


class TaskProgress(BaseModel):
    """任务进度"""
    status: TaskStatus
    progress: int = 0           # 0-100
    message: str = ""
    current_step: str = ""
    total_steps: int = 0
    completed_steps: int = 0


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


class UploadResponse(BaseModel):
    """上传响应"""
    task_id: str
    message: str


class APIKeyConfig(BaseModel):
    """API Key 配置"""
    qwen_api_key: str
    qwen_tts_key: str
    encrypted: bool = False