"""
播客文案生成器 - 基于Skill生成双人对话播客
"""

import json
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
from openai import OpenAI

from src.parser.pdf_to_skill import BookSkill, SkillChapter


class DialogueLine(BaseModel):
    """单行对话"""
    speaker: str  # 小北/阿南
    content: str


class PodcastScript(BaseModel):
    """播客文稿"""
    chapter_number: int
    chapter_title: str
    dialogues: List[DialogueLine]
    duration_estimate: int  # 秒


class PodcastGenerator:
    """播客文稿生成器"""
    
    HOST_A = "小北"  # 活泼幽默
    HOST_B = "阿南"  # 沉稳严谨
    
    SYSTEM_PROMPT = """你是一个专业的播客文案撰写专家。你需要将书籍内容转化为双人对话式的播客文稿。

## 主持人风格
- 小北：活泼幽默，喜欢用比喻和段子，让内容生动有趣，会提问、会吐槽
- 阿南：沉稳严谨，负责讲解核心内容，总结归纳，确保信息准确

## 要求
1. **内容丰富**：完整呈现原文核心内容，不遗漏重要信息
2. **风格幽默**：适当加入幽默元素、比喻、互动
3. **自然对话**：有问有答，有吐槽有总结，像真实聊天
4. **结构清晰**：开场引入 → 内容讲解 → 互动讨论 → 总结收尾
5. **忠实原文**：不编造内容，所有信息来自原文

## 输出格式
[小北]: 内容...
[阿南]: 内容...

## 篇幅要求
每章约20-40轮对话（约3-6分钟）
"""

    def __init__(self, api_key: str):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://coding.dashscope.aliyuncs.com/v1"
        )
    
    def generate_chapter_script(
        self,
        chapter: SkillChapter,
        book_context: str = ""
    ) -> PodcastScript:
        """
        为单个章节生成播客文稿
        """
        user_prompt = f"""
## 书籍背景
{book_context[:500] if book_context else "无"}

## 章节信息
第{chapter.number}章: {chapter.title}

## 章节内容
{chapter.content}

---

请生成这个章节的播客文稿。要求：
1. 内容丰富，完整呈现原文核心观点和故事
2. 风格幽默风趣，有小北的吐槽和阿南的总结
3. 自然对话，像两个朋友在聊天推荐这本书
4. 开场要有吸引力，结尾要留悬念

开始生成：
"""
        
        response = self.client.chat.completions.create(
            model="qwen3.5-plus",
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=8192,
            temperature=0.8  # 更有创意
        )
        
        script_text = response.choices[0].message.content
        dialogues = self._parse_dialogues(script_text)
        
        return PodcastScript(
            chapter_number=chapter.number,
            chapter_title=chapter.title,
            dialogues=dialogues,
            duration_estimate=len(dialogues) * 5
        )
    
    def _parse_dialogues(self, text: str) -> List[DialogueLine]:
        """解析对话文本"""
        import re
        
        dialogues = []
        pattern = r'\[(小北|阿南)\]:\s*(.+)'
        
        for match in re.finditer(pattern, text, re.MULTILINE):
            speaker = match.group(1)
            content = match.group(2).strip()
            if content:
                dialogues.append(DialogueLine(speaker=speaker, content=content))
        
        return dialogues
    
    def generate_all_scripts(
        self,
        skill: BookSkill,
        output_dir: str | Path
    ) -> List[PodcastScript]:
        """
        为整本书生成播客文稿
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 构建书籍背景
        book_context = f"""
书名：《{skill.metadata.title}》
作者：{skill.metadata.author}
页数：{skill.metadata.total_pages}
章节数：{skill.metadata.total_chapters}
"""
        
        scripts = []
        
        for chapter in skill.chapters:
            print(f"📝 生成第{chapter.number}章文稿: {chapter.title}")
            
            script = self.generate_chapter_script(chapter, book_context)
            
            # 保存
            script_path = output_dir / f"chapter_{chapter.number:02d}.json"
            with open(script_path, "w", encoding="utf-8") as f:
                json.dump(script.model_dump(), f, ensure_ascii=False, indent=2)
            
            # 也保存纯文本
            txt_path = script_path.with_suffix(".txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                for d in script.dialogues:
                    f.write(f"[{d.speaker}]: {d.content}\n\n")
            
            print(f"   ✅ {len(script.dialogues)}轮对话, 约{script.duration_estimate}秒")
            scripts.append(script)
        
        return scripts


def generate_podcast_from_skill(
    skill_path: str,
    api_key: str,
    output_dir: str = "data/output/scripts"
) -> List[PodcastScript]:
    """
    从Skill生成播客文稿
    
    使用示例:
        scripts = generate_podcast_from_skill(
            skill_path="data/skills/无语问上帝_skill.json",
            api_key="your_api_key",
            output_dir="data/output/scripts"
        )
    """
    # 加载Skill
    with open(skill_path, "r", encoding="utf-8") as f:
        skill_data = json.load(f)
    
    skill = BookSkill(**skill_data)
    
    # 生成文稿
    generator = PodcastGenerator(api_key=api_key)
    return generator.generate_all_scripts(skill, output_dir)