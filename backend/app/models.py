"""数据模型 v4.0"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import uuid
from datetime import datetime, timedelta
import hashlib


def generate_key():
    return f"pk_{uuid.uuid4().hex[:24]}"


def generate_id():
    return uuid.uuid4().hex[:8]


def hash_password(password: str) -> str:
    """密码hash"""
    return hashlib.sha256(password.encode()).hexdigest()


class TaskQueue(Base):
    """任务队列"""
    __tablename__ = "task_queue"
    
    id = Column(String(16), primary_key=True, default=generate_id)
    book_id = Column(String(16), ForeignKey("books.id"), index=True)
    chapter_number = Column(Integer)
    task_type = Column(String(20))  # script, audio
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    progress = Column(Integer, default=0)  # 0-100
    message = Column(Text, nullable=True)
    result = Column(Text, nullable=True)  # JSON结果
    created_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # 关系
    book = relationship("Book", back_populates="tasks")


class User(Base):
    """用户"""
    __tablename__ = "users"
    
    id = Column(String(16), primary_key=True, default=generate_id)
    email = Column(String(255), unique=True, index=True)
    password_hash = Column(String(64))
    api_key = Column(String(32), ForeignKey("api_keys.key"), unique=True)
    nickname = Column(String(100), nullable=True)
    free_quota = Column(Integer, default=3)  # 免费额度
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    # 关系
    api_key_rel = relationship("APIKey", back_populates="user")
    prompts = relationship("PromptTemplate", back_populates="user")
    scripts = relationship("ScriptHistory", back_populates="user")


class APIKey(Base):
    """API Key（按次计费）"""
    __tablename__ = "api_keys"
    
    key = Column(String(32), primary_key=True, default=generate_key)
    name = Column(String(100), nullable=True)
    balance = Column(Integer, default=0)  # 余额（次数）
    total_used = Column(Integer, default=0)  # 累计使用次数
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    # 关系
    books = relationship("Book", back_populates="api_key_rel")
    user = relationship("User", back_populates="api_key_rel", uselist=False)


class Book(Base):
    """书籍"""
    __tablename__ = "books"
    
    id = Column(String(16), primary_key=True, default=generate_id)
    api_key = Column(String(32), ForeignKey("api_keys.key"), index=True)
    title = Column(String(255))
    author = Column(String(100), default="未知")
    filename = Column(String(255))
    file_path = Column(String(500))
    source_type = Column(String(20), default="pdf")  # pdf, text
    prompt_id = Column(String(16), ForeignKey("prompt_templates.id"), nullable=True)
    status = Column(String(20), default="pending")
    total_chapters = Column(Integer, default=0)
    completed_chapters = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, default=lambda: datetime.now() + timedelta(days=7))
    
    # 进度
    ocr_progress = Column(Integer, default=0)
    script_progress = Column(Integer, default=0)
    audio_progress = Column(Integer, default=0)
    
    # 新增：用于章节管理
    raw_text = Column(Text, nullable=True)  # 原始 OCR 文本
    pages_json = Column(Text, nullable=True)  # JSON 格式的页面数据
    
    # 关系
    chapters = relationship("Chapter", back_populates="book", cascade="all, delete-orphan")
    tasks = relationship("TaskQueue", back_populates="book", cascade="all, delete-orphan")
    api_key_rel = relationship("APIKey", back_populates="books")
    prompt = relationship("PromptTemplate", back_populates="books")


class Chapter(Base):
    """章节"""
    __tablename__ = "chapters"
    
    id = Column(String(16), primary_key=True, default=generate_id)
    book_id = Column(String(16), ForeignKey("books.id"), index=True)
    number = Column(Integer)
    title = Column(String(255))
    content = Column(Text, nullable=True)  # OCR/用户输入的文本
    page_range = Column(String(50), nullable=True)  # 页码范围，如 "1-15"
    script = Column(Text, nullable=True)  # 生成的文稿 JSON
    script_edited = Column(Text, nullable=True)  # 用户编辑后的文稿
    voice_mapping = Column(JSON, nullable=True)  # {"小北": "zh-CN-XiaoxiaoNeural", "阿南": "zh-CN-YunxiNeural"}
    audio_path = Column(String(500), nullable=True)
    duration = Column(Float, default=0)
    status = Column(String(20), default="pending")  # pending, script_ready, processing, completed, failed
    error_message = Column(Text, nullable=True)
    
    # 关系
    book = relationship("Book", back_populates="chapters")


class PromptTemplate(Base):
    """Prompt模版"""
    __tablename__ = "prompt_templates"
    
    id = Column(String(16), primary_key=True, default=generate_id)
    user_id = Column(String(16), ForeignKey("users.id"), nullable=True)  # null表示系统模版
    name = Column(String(255))
    description = Column(Text, nullable=True)
    content = Column(Text)  # prompt内容
    is_public = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False)  # 系统内置模版
    use_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系
    user = relationship("User", back_populates="prompts")
    books = relationship("Book", back_populates="prompt")


class ScriptHistory(Base):
    """文稿历史"""
    __tablename__ = "script_histories"
    
    id = Column(String(16), primary_key=True, default=generate_id)
    user_id = Column(String(16), ForeignKey("users.id"), index=True)
    book_id = Column(String(16), ForeignKey("books.id"), nullable=True)
    chapter_id = Column(String(16), ForeignKey("chapters.id"), nullable=True)
    content = Column(Text)  # 文稿JSON
    version = Column(Integer, default=1)
    note = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # 关系
    user = relationship("User", back_populates="scripts")


class VoiceConfig(Base):
    """音色配置"""
    __tablename__ = "voice_configs"
    
    id = Column(String(16), primary_key=True, default=generate_id)
    speaker_name = Column(String(50))  # 角色名（小北、阿南等）
    voice_id = Column(String(100))  # edge-tts音色ID
    voice_name = Column(String(100))  # 显示名称
    gender = Column(String(10))  # male, female
    language = Column(String(20), default="zh-CN")
    description = Column(String(255), nullable=True)
    preview_text = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())


class UsageLog(Base):
    """用量日志"""
    __tablename__ = "usage_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    api_key = Column(String(32), index=True)
    user_id = Column(String(16), nullable=True)
    book_id = Column(String(16), nullable=True)
    chapter_id = Column(String(16), nullable=True)
    action = Column(String(50))
    cost = Column(Integer, default=0)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())