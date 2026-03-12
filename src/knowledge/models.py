"""知识库数据模型"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Character(BaseModel):
    """人物模型"""
    name: str = Field(..., description="人物名称")
    aliases: List[str] = Field(default_factory=list, description="别名")
    description: str = Field("", description="人物描述")
    relationships: dict[str, str] = Field(default_factory=dict, description="与其他人物的关系")
    first_appearance: Optional[str] = Field(None, description="首次出现位置")
    importance: int = Field(1, ge=1, le=5, description="重要程度 1-5")


class Location(BaseModel):
    """地点模型"""
    name: str = Field(..., description="地点名称")
    description: str = Field("", description="地点描述")
    events: List[str] = Field(default_factory=list, description="相关事件")


class Chapter(BaseModel):
    """章节模型"""
    number: int = Field(..., description="章节编号")
    title: str = Field(..., description="章节标题")
    content: str = Field(..., description="章节内容")
    summary: str = Field("", description="章节摘要")
    characters: List[str] = Field(default_factory=list, description="出现的人物")
    locations: List[str] = Field(default_factory=list, description="出现的地点")
    key_events: List[str] = Field(default_factory=list, description="关键事件")


class BookKnowledge(BaseModel):
    """图书知识库"""
    title: str = Field(..., description="书名")
    author: str = Field("", description="作者")
    summary: str = Field("", description="全书摘要")
    themes: List[str] = Field(default_factory=list, description="主题")
    characters: List[Character] = Field(default_factory=list, description="人物列表")
    locations: List[Location] = Field(default_factory=list, description="地点列表")
    chapters: List[Chapter] = Field(default_factory=list, description="章节列表")
    timeline: List[dict] = Field(default_factory=list, description="时间线事件")
    
    def get_character(self, name: str) -> Optional[Character]:
        """获取人物"""
        for char in self.characters:
            if char.name == name or name in char.aliases:
                return char
        return None
    
    def get_chapter(self, number: int) -> Optional[Chapter]:
        """获取章节"""
        for chapter in self.chapters:
            if chapter.number == number:
                return chapter
        return None