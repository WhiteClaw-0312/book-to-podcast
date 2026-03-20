"""
Skill Seeker 服务 v5.0
将文本转换为结构化的 SKILL.md

核心流程：
1. 分块处理长文本
2. 提取核心观点、关键细节
3. 生成结构化 SKILL
"""
import json
import re
import asyncio
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from openai import OpenAI
from ..config import settings


@dataclass
class SkillResult:
    """SKILL 结果"""
    summary: str
    key_points: List[str]
    themes: List[str]
    examples: List[str]
    insights: List[str]
    important_details: List[str]
    full_skill_md: str
    content_length: int
    skill_length: int
    processing_time: float


class SkillSeekerService:
    """Skill Seeker 服务 - 文本转结构化 SKILL"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL
        )
        
        # 分析 Prompt
        self.ANALYZE_PROMPT = """你是一位专业的文档分析师。请分析以下文本，提取关键信息并组织成结构化格式。

文本内容：
{content}

请提取：
1. 摘要（100-200字）
2. 核心观点（最重要的3-8个观点）
3. 主题（2-5个）
4. 重要示例（2-4个最有说服力的例子）
5. 见解与思考（2-4个）
6. 重要细节（不能遗漏的关键信息）

输出 JSON 格式：
{{
  "summary": "...",
  "key_points": ["观点1", "观点2", ...],
  "themes": ["主题1", "主题2", ...],
  "examples": ["示例1", "示例2", ...],
  "insights": ["见解1", "见解2", ...],
  "important_details": ["细节1", "细节2", ...]
}}

规则：
1. 必须提取所有重要的观点和细节
2. 摘要要概括全文核心内容
3. 示例要具体、有说服力
4. 只输出 JSON，不要其他内容"""

        # 合成 Prompt
        self.SYNTHESIZE_PROMPT = """基于以下分析结果，生成完整的 SKILL.md 格式文档。

分析结果：
{analysis}

请生成 Markdown 格式的 SKILL.md，包含：
1. 概述
2. 核心内容（观点、主题）
3. 重要细节
4. 示例与见解

输出格式要求：
- 使用 Markdown 格式
- 层次清晰
- 保留所有重要信息"""
    
    async def generate_skill(
        self,
        book_title: str,
        chapter_title: str,
        chapter_number: int,
        content: str
    ) -> SkillResult:
        """
        生成 SKILL
        
        策略：
        - 内容 < 6000字：直接处理
        - 内容 > 6000字：分块处理 + 合并
        """
        start_time = time.time()
        content_length = len(content)
        
        try:
            if content_length <= 6000:
                # 短文本：直接处理
                result = await self._process_single(content)
            else:
                # 长文本：分块处理
                result = await self._process_chunked(content)
            
            # 生成完整 SKILL.md
            full_skill_md = self._generate_skill_md(
                book_title, chapter_title, chapter_number, result
            )
            
            processing_time = time.time() - start_time
            
            return SkillResult(
                summary=result.get("summary", ""),
                key_points=result.get("key_points", []),
                themes=result.get("themes", []),
                examples=result.get("examples", []),
                insights=result.get("insights", []),
                important_details=result.get("important_details", []),
                full_skill_md=full_skill_md,
                content_length=content_length,
                skill_length=len(full_skill_md),
                processing_time=processing_time
            )
            
        except Exception as e:
            print(f"Skill 生成失败: {e}")
            # 返回默认结果
            return self._create_default_skill(content, chapter_number, chapter_title, str(e))
    
    async def _process_single(self, content: str) -> dict:
        """处理单个短文本"""
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.client.chat.completions.create(
                model=settings.QWEN_MODEL,
                messages=[
                    {"role": "system", "content": "你是专业的文档分析师。只输出 JSON。"},
                    {"role": "user", "content": self.ANALYZE_PROMPT.format(content=content)}
                ],
                temperature=0.3,
                max_tokens=3000
            )
        )
        
        result = response.choices[0].message.content
        return self._parse_json(result)
    
    async def _process_chunked(self, content: str) -> dict:
        """分块处理长文本"""
        # 1. 分块
        chunks = self._split_into_chunks(content, chunk_size=5000, overlap=200)
        
        print(f"长文本分块处理: {len(content)}字 -> {len(chunks)}块")
        
        # 2. 并行分析每个块
        tasks = [self._analyze_chunk(chunk, i) for i, chunk in enumerate(chunks)]
        chunk_results = await asyncio.gather(*tasks)
        
        # 3. 合并结果
        merged = self._merge_results(chunk_results)
        
        # 4. 综合生成最终结果
        final = await self._synthesize_final(merged)
        
        return final
    
    def _split_into_chunks(self, content: str, chunk_size: int = 5000, overlap: int = 200) -> List[str]:
        """将长文本分成多个块"""
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            
            # 尝试在段落或句子边界截断
            if end < len(content):
                # 向后找段落边界
                para_break = content.find('\n\n', end - 200, end + 200)
                if para_break != -1:
                    end = para_break + 2
                else:
                    # 向后找句号
                    for punct in ['。', '！', '？', '.', '!', '?']:
                        idx = content.rfind(punct, end - 200, end + 200)
                        if idx != -1:
                            end = idx + 1
                            break
            
            chunks.append(content[start:end])
            start = end - overlap if end < len(content) else len(content)
        
        return chunks
    
    async def _analyze_chunk(self, chunk: str, index: int) -> dict:
        """分析单个块"""
        prompt = f"""分析以下文本片段（第{index + 1}部分），提取关键信息：

{chunk}

输出 JSON 格式：
{{
  "key_points": ["观点1", "观点2", ...],
  "examples": ["示例1", ...],
  "important_details": ["细节1", ...],
  "insights": ["见解1", ...]
}}"""
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=settings.QWEN_MODEL,
                    messages=[
                        {"role": "system", "content": "你是文档分析专家。只输出 JSON。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000
                )
            )
            
            result = response.choices[0].message.content
            return self._parse_json(result)
            
        except Exception as e:
            print(f"块 {index + 1} 分析失败: {e}")
            return {"key_points": [], "examples": [], "important_details": [], "insights": []}
    
    def _merge_results(self, results: List[dict]) -> dict:
        """合并多个块的分析结果"""
        merged = {
            "key_points": [],
            "examples": [],
            "important_details": [],
            "insights": []
        }
        
        for r in results:
            for key in merged:
                items = r.get(key, [])
                merged[key].extend(items)
        
        # 去重（相似度判断）
        for key in merged:
            merged[key] = self._deduplicate(merged[key])
        
        return merged
    
    def _deduplicate(self, items: List[str]) -> List[str]:
        """去重"""
        unique = []
        for item in items:
            if not any(self._similar(item, u) for u in unique):
                unique.append(item)
        return unique
    
    def _similar(self, s1: str, s2: str, threshold: float = 0.7) -> bool:
        """判断两个字符串是否相似"""
        if not s1 or not s2:
            return False
        # 简单的相似度判断
        words1 = set(s1)
        words2 = set(s2)
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return union > 0 and intersection / union > threshold
    
    async def _synthesize_final(self, merged: dict) -> dict:
        """综合生成最终结果"""
        prompt = f"""基于以下分块分析结果，综合生成完整的章节分析：

分析结果：
{json.dumps(merged, ensure_ascii=False, indent=2)}

请综合整理，输出 JSON 格式：
{{
  "summary": "章节摘要（100-200字）",
  "key_points": ["最重要的3-8个观点"],
  "themes": ["2-5个主题"],
  "examples": ["2-4个最典型的示例"],
  "insights": ["2-4个见解"],
  "important_details": ["不能遗漏的关键细节"]
}}"""
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=settings.QWEN_MODEL,
                    messages=[
                        {"role": "system", "content": "你是文档分析专家。只输出 JSON。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000
                )
            )
            
            result = response.choices[0].message.content
            return self._parse_json(result)
            
        except Exception as e:
            print(f"综合分析失败: {e}")
            return merged
    
    def _parse_json(self, text: str) -> dict:
        """解析 JSON"""
        try:
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        return {}
    
    def _generate_skill_md(
        self,
        book_title: str,
        chapter_title: str,
        chapter_number: int,
        result: dict
    ) -> str:
        """生成 SKILL.md 格式文档"""
        md = f"""# 第 {chapter_number} 章：{chapter_title}

## 📖 书籍信息
- 书名：《{book_title}》
- 章节：第 {chapter_number} 章

---

## 📌 摘要

{result.get('summary', '暂无摘要')}

---

## 💡 核心观点

"""
        for i, point in enumerate(result.get('key_points', []), 1):
            md += f"{i}. {point}\n"
        
        md += "\n---\n\n## 🎯 重要细节\n\n"
        for detail in result.get('important_details', []):
            md += f"- {detail}\n"
        
        md += "\n---\n\n## 📝 典型示例\n\n"
        for example in result.get('examples', []):
            md += f"- {example}\n"
        
        md += "\n---\n\n## 🔍 见解与思考\n\n"
        for insight in result.get('insights', []):
            md += f"- {insight}\n"
        
        md += f"""
---

## 📊 信息概览

- 核心观点数：{len(result.get('key_points', []))}
- 重要细节数：{len(result.get('important_details', []))}
- 典型示例数：{len(result.get('examples', []))}
- 见解数：{len(result.get('insights', []))}

---

*此 SKILL.md 由 Skill Seekers 自动生成*
"""
        return md
    
    def _create_default_skill(
        self,
        content: str,
        chapter_number: int,
        chapter_title: str,
        error: str
    ) -> SkillResult:
        """创建默认 SKILL"""
        return SkillResult(
            summary=f"第{chapter_number}章：{chapter_title}",
            key_points=["内容分析失败，请重试"],
            themes=[],
            examples=[],
            insights=[],
            important_details=[f"错误信息：{error}"],
            full_skill_md=f"# 第 {chapter_number} 章：{chapter_title}\n\n内容分析失败，请重试。",
            content_length=len(content),
            skill_length=0,
            processing_time=0
        )