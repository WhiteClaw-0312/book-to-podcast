"""数据模型"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import uuid
from datetime import datetime, timedelta


def generate_key():
    return f"pk_{uuid.uuid4().hex[:24]}"


def generate_id():
    return uuid.uuid4().hex[:8]


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


class Book(Base):
    """书籍"""
    __tablename__ = "books"
    
    id = Column(String(16), primary_key=True, default=generate_id)
    api_key = Column(String(32), ForeignKey("api_keys.key"), index=True)
    title = Column(String(255))
    author = Column(String(100), default="未知")
    filename = Column(String(255))
    file_path = Column(String(500))
    status = Column(String(20), default="pending")  # pending, ocr, ready, processing, completed, failed
    total_chapters = Column(Integer, default=0)
    completed_chapters = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, default=lambda: datetime.now() + timedelta(days=7))
    
    # 进度
    ocr_progress = Column(Integer, default=0)
    script_progress = Column(Integer, default=0)
    audio_progress = Column(Integer, default=0)
    
    # 关系
    chapters = relationship("Chapter", back_populates="book", cascade="all, delete-orphan")
    api_key_rel = relationship("APIKey", back_populates="books")


class Chapter(Base):
    """章节"""
    __tablename__ = "chapters"
    
    id = Column(String(16), primary_key=True, default=generate_id)
    book_id = Column(String(16), ForeignKey("books.id"), index=True)
    number = Column(Integer)
    title = Column(String(255))
    content = Column(Text, nullable=True)  # OCR 识别的文本
    script = Column(Text, nullable=True)  # 生成的文稿 JSON
    audio_path = Column(String(500), nullable=True)
    duration = Column(Float, default=0)  # 时长（秒）
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)
    
    # 关系
    book = relationship("Book", back_populates="chapters")


class UsageLog(Base):
    """用量日志"""
    __tablename__ = "usage_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    api_key = Column(String(32), index=True)
    book_id = Column(String(16), nullable=True)
    chapter_id = Column(String(16), nullable=True)
    action = Column(String(50))  # upload, ocr, generate, download
    cost = Column(Integer, default=0)  # 消耗次数
    details = Column(Text, nullable=True)  # JSON 详情
    created_at = Column(DateTime, default=func.now())