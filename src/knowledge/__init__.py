"""知识库构建模块"""

from .builder import KnowledgeBaseBuilder
from .models import BookKnowledge, Character, Chapter, Location

__all__ = [
    "KnowledgeBaseBuilder",
    "BookKnowledge", 
    "Character",
    "Chapter", 
    "Location",
]