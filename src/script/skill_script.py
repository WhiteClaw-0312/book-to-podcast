"""播客文稿生成器 - 基于 Skill 知识库生成双人对话播客"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from openai import OpenAI


class DialogueLine(BaseModel):
    """单行对话"""
    speaker: str = Field(..., description="说话人：小北/阿南")
    content: str = Field(..., description="对话内容")


class PodcastScript(BaseModel):
    """播客文稿"""
    chapter_number: int = Field(..., description="章节编号")
    chapter_title: str = Field(..., description="章节标题")
    dialogues: List[DialogueLine] = Field(default_factory=list, description="对话列表")
    duration_estimate: int = Field(0, description="预估时长(秒)")


class SkillKnowledge:
    """Skill 知识库加载器"""
    
    def __init__(self, skill_path: str | Path):
        self.skill_path = Path(skill_path)
        self.skill_md = None
        self.references = {}
    
    def load(self) -> None:
        """加载 Skill 内容"""
        # 加载 SKILL.md
        skill_md_path = self.skill_path / "SKILL.md"
        if skill_md_path.exists():
            with open(skill_md_path, "r", encoding="utf-8") as f:
                self.skill_md = f.read()
        
        # 加载 references/
        refs_path = self.skill_path / "references"
        if refs_path.exists():
            for ref_file in refs_path.glob("**/*.md"):
                rel_path = ref_file.relative_to(refs_path)
                with open(ref_file, "r", encoding="utf-8") as f:
                    self.references[str(rel_path)] = f.read()
    
    def get_all_content(self) -> str:
        """获取所有内容"""
        parts = []
        if self.skill_md:
            parts.append(f"# SKILL.md\n\n{self.skill_md}")
        for name, content in self.references.items():
            parts.append(f"# {name}\n\n{content}")
        return "\n\n---\n\n".join(parts)
    
    def get_chapters(self) -> List[Dict[str, Any]]:
        """提取章节列表"""
        chapters = []
        if not self.skill_md:
            return chapters
        
        # 简单的章节提取（基于标题）
        lines = self.skill_md.split("\n")
        current_chapter = None
        current_content = []
        
        for line in lines:
            if line.startswith("## "):
                if current_chapter:
                    chapters.append({
                        "title": current_chapter,
                        "content": "\n".join(current_content)
                    })
                current_chapter = line[3:].strip()
                current_content = []
            elif current_chapter:
                current_content.append(line)
        
        if current_chapter:
            chapters.append({
                "title": current_chapter,
                "content": "\n".join(current_content)
            })
        
        return chapters


class PodcastScriptGenerator:
    """播客文稿生成器"""
    
    HOST_A = "小北"  # 活泼、幽默
    HOST_B = "阿南"  # 沉稳、严谨
    
    SYSTEM_PROMPT = """你是一个专业的播客文稿撰写专家。你需要将图书内容转化为双人对话式的播客文稿。

## 主持人风格
- 小北：活泼幽默，喜欢用比喻和段子，让内容生动有趣
- 阿南：沉稳严谨，负责总结和深化，确保内容准确

## 要求
1. 内容必须严格基于提供的知识库，不能编造
2. 对话自然流畅，有互动感
3. 每段对话控制在1-3句话
4. 适当加入幽默元素和比喻
5. 总时长控制在3-5分钟（约20-30轮对话）

## 输出格式
[小北]: 内容...
[阿南]: 内容...
"""

    def __init__(self, api_key: str, base_url: str = "https://coding.dashscope.aliyuncs.com/v1"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = "qwen3.5-plus"
    
    def generate_script(
        self,
        chapter_title: str,
        chapter_content: str,
        context: str = ""
    ) -> PodcastScript:
        """生成单章节播客文稿"""
        
        user_prompt = f"""
## 章节标题
{chapter_title}

## 章节内容
{chapter_content}

## 背景知识
{context[:3000] if context else "无"}

请生成这个章节的播客文稿，要求：
1. 以开场白开始
2. 介绍章节主题
3. 讨论章节核心内容
4. 以总结和预告下期结束
"""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=4096,
            temperature=0.7
        )
        
        script_text = response.choices[0].message.content
        dialogues = self._parse_dialogues(script_text)
        
        return PodcastScript(
            chapter_number=0,
            chapter_title=chapter_title,
            dialogues=dialogues,
            duration_estimate=len(dialogues) * 5
        )
    
    def _parse_dialogues(self, text: str) -> List[DialogueLine]:
        """解析对话文本"""
        import re
        
        dialogues = []
        pattern = r'\[(小北|阿南)\]:\s*(.+)'
        
        for match in re.finditer(pattern, text):
            speaker = match.group(1)
            content = match.group(2).strip()
            dialogues.append(DialogueLine(speaker=speaker, content=content))
        
        return dialogues
    
    def generate_all_scripts(
        self,
        skill_knowledge: SkillKnowledge,
        output_dir: str | Path
    ) -> List[PodcastScript]:
        """生成所有章节的播客文稿"""
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        chapters = skill_knowledge.get_chapters()
        context = skill_knowledge.get_all_content()
        
        scripts = []
        for i, chapter in enumerate(chapters):
            print(f"生成第 {i+1}/{len(chapters)} 章: {chapter['title']}")
            
            script = self.generate_script(
                chapter_title=chapter['title'],
                chapter_content=chapter['content'],
                context=context
            )
            script.chapter_number = i + 1
            
            # 保存文稿
            script_path = output_dir / f"chapter_{i+1:02d}_{chapter['title']}.json"
            with open(script_path, "w", encoding="utf-8") as f:
                json.dump(script.model_dump(), f, ensure_ascii=False, indent=2)
            
            scripts.append(script)
        
        return scripts


def generate_podcast_from_skill(
    skill_path: str | Path,
    api_key: str,
    output_dir: str | Path
) -> List[PodcastScript]:
    """从 Skill 生成播客文稿"""
    
    # 加载 Skill
    skill = SkillKnowledge(skill_path)
    skill.load()
    
    # 生成文稿
    generator = PodcastScriptGenerator(api_key=api_key)
    scripts = generator.generate_all_scripts(skill, output_dir)
    
    return scripts