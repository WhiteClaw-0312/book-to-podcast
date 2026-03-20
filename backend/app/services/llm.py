"""
LLM 服务 v5.0
基于 SKILL 和 Prompt 配置生成播客文稿
"""
import json
import re
import asyncio
from typing import Dict, List, Optional
from openai import OpenAI
from ..config import settings
from .skill_seeker import SkillSeekerService, SkillResult
from .prompt_builder import PromptBuilder, PromptConfig, build_prompt_from_model


class LLMService:
    """LLM 服务 - 播客文稿生成"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL
        )
        self.skill_seeker = SkillSeekerService()
        self.prompt_builder = PromptBuilder()
    
    async def generate_script_with_skill(
        self,
        book_title: str,
        author: str,
        chapter_number: int,
        chapter_title: str,
        content: str,
        prompt_config: Optional[Dict] = None
    ) -> Dict:
        """
        完整流程：内容 -> SKILL -> 文稿
        
        这是 v5.0 的核心方法
        """
        # 1. 生成 SKILL
        print(f"第 {chapter_number} 章：正在生成 SKILL...")
        skill = await self.skill_seeker.generate_skill(
            book_title=book_title,
            chapter_title=chapter_title,
            chapter_number=chapter_number,
            content=content
        )
        
        # 2. 构建 Prompt
        print(f"第 {chapter_number} 章：正在构建 Prompt...")
        config = PromptConfig(**prompt_config) if prompt_config else PromptConfig()
        
        chapter_info = {
            "book_title": book_title,
            "author": author,
            "number": chapter_number,
            "title": chapter_title
        }
        
        prompt = self.prompt_builder.build(config, {
            "summary": skill.summary,
            "key_points": skill.key_points,
            "important_details": skill.important_details,
            "examples": skill.examples
        }, chapter_info)
        
        # 3. 生成文稿
        print(f"第 {chapter_number} 章：正在生成文稿...")
        script = await self._generate_script_from_prompt(prompt)
        
        # 4. 添加元数据
        script["skill"] = {
            "summary": skill.summary,
            "key_points_count": len(skill.key_points),
            "details_count": len(skill.important_details),
            "processing_time": skill.processing_time
        }
        
        return {
            "script": script,
            "skill": {
                "summary": skill.summary,
                "key_points": skill.key_points,
                "themes": skill.themes,
                "examples": skill.examples,
                "insights": skill.insights,
                "important_details": skill.important_details,
                "full_skill_md": skill.full_skill_md,
                "content_length": skill.content_length,
                "skill_length": skill.skill_length,
                "processing_time": skill.processing_time
            }
        }
    
    async def generate_script_from_skill_model(
        self,
        book_title: str,
        author: str,
        chapter_number: int,
        chapter_title: str,
        skill: SkillResult,
        prompt_model
    ) -> Dict:
        """
        从已有的 SKILL 模型生成文稿
        
        用于 SKILL 已生成的情况（如重新生成文稿）
        """
        chapter_info = {
            "book_title": book_title,
            "author": author,
            "number": chapter_number,
            "title": chapter_title
        }
        
        # 从模型构建 Prompt
        prompt = build_prompt_from_model(
            prompt_model,
            {
                "summary": skill.summary,
                "key_points": skill.key_points,
                "important_details": skill.important_details,
                "examples": skill.examples
            },
            chapter_info
        )
        
        script = await self._generate_script_from_prompt(prompt)
        
        return script
    
    async def _generate_script_from_prompt(self, prompt: str) -> Dict:
        """从 Prompt 生成文稿"""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=settings.QWEN_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一位专业的播客编剧。只输出 JSON 格式，不要其他内容。"
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=8000
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
            return self._create_default_script(1, "生成失败", str(e))
    
    # ===== 保留旧方法以兼容 =====
    
    async def generate_script(
        self,
        book_title: str,
        author: str,
        chapter_number: int,
        chapter_title: str,
        content: str,
        custom_prompt: Optional[str] = None
    ) -> Dict:
        """
        旧版方法（兼容）
        
        直接从内容生成文稿（不使用 SKILL）
        """
        # 限制内容长度
        content = content[:6000]
        
        # 使用默认配置
        result = await self.generate_script_with_skill(
            book_title=book_title,
            author=author,
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            content=content,
            prompt_config=None
        )
        
        return result.get("script", {})
    
    def _create_default_script(self, chapter_number: int, chapter_title: str, error: str) -> Dict:
        """创建默认文稿"""
        return {
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "word_count": 0,
            "error": error,
            "dialogues": [
                {"speaker": "小北", "content": "大家好，欢迎来到今天的节目。"},
                {"speaker": "阿南", "content": f"今天我们来看第{chapter_number}章，「{chapter_title}」。"},
                {"speaker": "小北", "content": "这章的内容非常精彩，让我们一起来听听吧。"},
                {"speaker": "阿南", "content": "由于技术原因，这部分内容暂时无法生成详细对话，敬请谅解。"}
            ]
        }