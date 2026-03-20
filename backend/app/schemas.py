"""Pydantic 模型"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# ==================== API Key ====================

class APIKeyCreate(BaseModel):
    name: Optional[str] = None
    balance: int = 0


class APIKeyResponse(BaseModel):
    key: str
    name: Optional[str]
    balance: int
    total_used: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class BalanceResponse(BaseModel):
    key: str
    balance: int
    total_used: int


# ==================== Book ====================

class BookCreate(BaseModel):
    title: str
    api_key: str


class BookResponse(BaseModel):
    id: str
    title: str
    author: str
    status: str
    total_chapters: int
    completed_chapters: int
    created_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True


class BookStatusResponse(BaseModel):
    id: str
    title: str
    author: Optional[str] = None
    status: str
    total_chapters: int
    completed_chapters: int
    ocr_progress: int
    script_progress: int
    audio_progress: int
    error_message: Optional[str] = None
    prompt_id: Optional[str] = None
    queue: Optional[dict] = None
    tasks: Optional[List[dict]] = None
    chapters: List["ChapterResponse"] = []


# ==================== Chapter ====================

class ChapterResponse(BaseModel):
    id: str
    number: int
    title: str
    content: Optional[str] = None
    word_count: int = 0
    page_range: Optional[str] = None
    status: str
    duration: float
    has_script: bool = False
    has_audio: bool = False

    class Config:
        from_attributes = True


class ChapterDetailResponse(BaseModel):
    id: str
    number: int
    title: str
    content: Optional[str]
    script: Optional[dict]
    audio_url: Optional[str]
    duration: float
    status: str


# ==================== Generate ====================

class GenerateRequest(BaseModel):
    chapters: List[int]
    api_key: str = ""  # 可选，token 认证时不需要
    voice_mapping: Optional[dict] = None  # 角色到音色的映射 {"小北": "zh-CN-XiaoxiaoNeural"}
    prompt_config: Optional[dict] = None  # 🆕 Prompt 配置


class GenerateResponse(BaseModel):
    message: str
    cost: int
    estimated_time: int  # 秒


# ==================== Usage ====================

class UsageLogResponse(BaseModel):
    id: int
    action: str
    cost: int
    details: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Common ====================

class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


# 更新 forward references
BookStatusResponse.model_rebuild()