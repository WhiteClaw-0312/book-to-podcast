"""知识库构建器"""

from typing import Dict, Any, List
from pathlib import Path
import json

from .models import BookKnowledge, Character, Chapter, Location


class KnowledgeBaseBuilder:
    """图书知识库构建器"""
    
    def __init__(self, book_data: Dict[str, Any]):
        """
        初始化构建器
        
        Args:
            book_data: 解析后的图书数据（来自 parser）
        """
        self.book_data = book_data
        self.knowledge = None
        
    def build(self) -> BookKnowledge:
        """构建知识库"""
        self.knowledge = BookKnowledge(
            title=self.book_data.get("metadata", {}).get("title", "未知书名"),
            author=self.book_data.get("metadata", {}).get("author", "未知作者"),
        )
        
        # 步骤 1: 提取章节
        self._extract_chapters()
        
        # 步骤 2: 提取人物
        self._extract_characters()
        
        # 步骤 3: 提取地点
        self._extract_locations()
        
        # 步骤 4: 生成摘要
        self._generate_summary()
        
        return self.knowledge
    
    def _extract_chapters(self) -> None:
        """提取章节信息"""
        chapters_data = self.book_data.get("chapters", [])
        text = self.book_data.get("text", "")
        
        if chapters_data:
            # 使用检测到的章节
            for i, ch in enumerate(chapters_data):
                chapter = Chapter(
                    number=i + 1,
                    title=ch.get("title", f"第{i+1}章"),
                    content="",  # TODO: 提取章节内容
                )
                self.knowledge.chapters.append(chapter)
        else:
            # 自动分割章节
            self._auto_split_chapters()
    
    def _auto_split_chapters(self) -> None:
        """自动分割章节"""
        # TODO: 实现智能章节分割
        pass
    
    def _extract_characters(self) -> None:
        """提取人物信息"""
        # TODO: 使用 LLM 提取人物
        pass
    
    def _extract_locations(self) -> None:
        """提取地点信息"""
        # TODO: 使用 LLM 提取地点
        pass
    
    def _generate_summary(self) -> None:
        """生成全书摘要"""
        # TODO: 使用 LLM 生成摘要
        pass
    
    def save(self, output_path: Path) -> None:
        """保存知识库到文件"""
        if not self.knowledge:
            raise ValueError("请先调用 build() 构建知识库")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.knowledge.model_dump(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load(cls, input_path: Path) -> BookKnowledge:
        """从文件加载知识库"""
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return BookKnowledge(**data)