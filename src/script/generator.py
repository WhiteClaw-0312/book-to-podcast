"""播客文稿生成模块"""

from typing import List, Dict, Any
from pydantic import BaseModel, Field


class DialogueLine(BaseModel):
    """单行对话"""
    speaker: str = Field(..., description="说话人：主持人A/B")
    content: str = Field(..., description="对话内容")


class PodcastScript(BaseModel):
    """播客文稿"""
    chapter_number: int = Field(..., description="章节编号")
    chapter_title: str = Field(..., description="章节标题")
    dialogues: List[DialogueLine] = Field(default_factory=list, description="对话列表")
    duration_estimate: int = Field(0, description="预估时长(秒)")


class ScriptGenerator:
    """播客文稿生成器"""
    
    HOST_A = "小北"  # 主持人A：活泼、幽默
    HOST_B = "阿南"  # 主持人B：沉稳、严谨
    
    SYSTEM_PROMPT = """你是一个专业的播客文稿撰写专家。你需要将图书内容转化为双人对话式的播客文稿。

要求：
1. 两位主持人风格互补：{host_a}活泼幽默，{host_b}沉稳严谨
2. 内容严谨，必须基于提供的知识库内容，不能编造
3. 对话自然流畅，有互动感
4. 适当加入幽默元素和比喻，让内容生动有趣
5. 每段对话控制在1-2句话
6. 控制总时长在3-5分钟

输出格式：
[{host_a}]: 内容...
[{host_b}]: 内容...
"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    def generate_script(
        self, 
        chapter_content: str,
        chapter_title: str,
        chapter_number: int,
        knowledge_context: str = ""
    ) -> PodcastScript:
        """生成单章节播客文稿"""
        
        prompt = f"""
{self.SYSTEM_PROMPT}

## 章节信息
标题：{chapter_title}
编号：第{chapter_number}章

## 章节内容
{chapter_content}

## 相关背景知识
{knowledge_context}

请生成播客文稿：
"""
        
        # TODO: 调用 LLM 生成文稿
        # response = self.llm_client.generate(prompt)
        # return self._parse_response(response, chapter_number, chapter_title)
        
        # 临时返回占位
        return PodcastScript(
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            dialogues=[
                DialogueLine(speaker=self.HOST_A, content=f"大家好，欢迎来到读书时间！今天我们要聊的是《{chapter_title}》这一章。"),
                DialogueLine(speaker=self.HOST_B, content=f"没错，这一章非常精彩。让我们开始吧！"),
            ]
        )
    
    def _parse_response(self, response: str, chapter_number: int, chapter_title: str) -> PodcastScript:
        """解析 LLM 响应为结构化文稿"""
        import re
        
        dialogues = []
        pattern = r'\[(小北|阿南)\]:\s*(.+)'
        
        for match in re.finditer(pattern, response):
            speaker = match.group(1)
            content = match.group(2).strip()
            dialogues.append(DialogueLine(speaker=speaker, content=content))
        
        # 估算时长（平均每句话约5秒）
        duration = len(dialogues) * 5
        
        return PodcastScript(
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            dialogues=dialogues,
            duration_estimate=duration
        )