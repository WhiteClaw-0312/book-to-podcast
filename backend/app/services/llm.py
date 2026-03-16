"""LLM 服务 - 文稿生成"""
import json
import re
import asyncio
from typing import Dict, List, Optional
from openai import OpenAI
from ..config import settings


# 默认系统Prompt
DEFAULT_SYSTEM_PROMPT = """你是一位专业的播客编剧，擅长将图书内容转换为引人入胜的双人对话式播客。

主持人设定：
- 小北：活泼好奇，善于提问，用"诶~"、"哇"、"真的吗"等语气词增加互动感
- 阿南：沉稳博学，善于总结和解释，用"没错"、"其实"、"可以说"等连接词

对话风格：
1. 保持原文核心观点和精彩段落
2. 对话自然流畅，有互动感
3. 适当加入过渡和总结
4. 每章约 10-15 分钟时长（约 40-50 句对话）
5. 开头要有章节导入，结尾要有小结

输出要求：
- 只输出 JSON 格式，不要其他内容
- JSON 必须符合指定格式"""


CHAPTER_PROMPT_TEMPLATE = """将以下图书章节转换为双人对话式播客文案。

书籍信息：
- 书名：《{book_title}》
- 作者：{author}
- 章节：第 {chapter_number} 章 - {chapter_title}

章节内容：
{content}

请输出 JSON 格式：
{{
  "chapter_number": {chapter_number},
  "chapter_title": "{chapter_title}",
  "word_count": 实际字数,
  "dialogues": [
    {{"speaker": "小北", "content": "..."}},
    {{"speaker": "阿南", "content": "..."}}
  ]
}}"""


class LLMService:
    """LLM 服务 - 播客文稿生成"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL
        )
    
    async def generate_script(
        self,
        book_title: str,
        author: str,
        chapter_number: int,
        chapter_title: str,
        content: str,
        custom_prompt: Optional[str] = None
    ) -> Dict:
        """生成播客文稿"""
        
        # 限制内容长度
        content = content[:6000]
        
        # 使用自定义Prompt或默认Prompt
        system_prompt = custom_prompt or DEFAULT_SYSTEM_PROMPT
        
        prompt = CHAPTER_PROMPT_TEMPLATE.format(
            book_title=book_title,
            author=author,
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            content=content
        )
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=settings.QWEN_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=5000
                )
            )
            
            result = response.choices[0].message.content
            
            # 解析 JSON
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                script = json.loads(json_match.group())
                return script
            else:
                raise ValueError("无法从响应中提取 JSON")
                
        except Exception as e:
            # 返回默认文稿
            return self._create_default_script(chapter_number, chapter_title, str(e))
    
    def _create_default_script(self, chapter_number: int, chapter_title: str, error: str) -> Dict:
        """创建默认文稿"""
        return {
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "word_count": 0,
            "error": error,
            "dialogues": [
                {"speaker": "小北", "content": f"大家好，欢迎来到今天的节目。"},
                {"speaker": "阿南", "content": f"今天我们来看第{chapter_number}章，「{chapter_title}」。"},
                {"speaker": "小北", "content": "这章的内容非常精彩，让我们一起来听听吧。"},
                {"speaker": "阿南", "content": "由于技术原因，这部分内容暂时无法生成详细对话，敬请谅解。"}
            ]
        }