"""服务模块"""
from .ocr import OCRService
from .llm import LLMService
from .tts import TTSService

__all__ = ["OCRService", "LLMService", "TTSService"]