"""
PDF 转 Skill 模块
使用 skill-seekers 库实现 PDF 到 Skill 的转换

安装: pip install skill-seekers
文档: https://github.com/yusufkaraaslan/Skill_Seekers
"""

import os
import json
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, List
from pydantic import BaseModel
from dataclasses import dataclass


class PDFSkillConfig(BaseModel):
    """PDF 转 Skill 配置"""
    # skill-seekers 配置
    use_skill_seekers: bool = True  # 是否使用 skill-seekers 库
    enhance_with_ai: bool = True    # 是否 AI 增强
    
    # Qwen API 配置（用于 OCR 和增强）
    qwen_api_key: str = ""
    qwen_model: str = "qwen3.5-plus"
    
    # 输出配置
    output_dir: str = "data/skills"
    skill_name: str = ""  # 输出 skill 名称


@dataclass
class Chapter:
    """章节"""
    number: int
    title: str
    content: str
    word_count: int = 0


@dataclass
class SkillOutput:
    """Skill 输出"""
    metadata: Dict
    chapters: List[Chapter]
    themes: List[str]
    key_points: List[str]
    skill_md_path: str
    skill_json_path: str


class PDFSkillExtractor:
    """
    PDF 转 Skill 提取器
    
    核心流程（参考 Skill_Seekers）：
    Ingest → Analyze → Structure → Enhance → Export
    """
    
    def __init__(self, config: Optional[PDFSkillConfig] = None):
        self.config = config or PDFSkillConfig()
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def extract(self, pdf_path: str, skill_name: str = None) -> SkillOutput:
        """
        从 PDF 提取 Skill
        
        Args:
            pdf_path: PDF 文件路径
            skill_name: 输出 skill 名称
        
        Returns:
            SkillOutput 对象
        """
        if not skill_name:
            skill_name = Path(pdf_path).stem
        
        print(f"📚 开始提取 Skill: {skill_name}")
        
        # 尝试使用 skill-seekers 库
        if self.config.use_skill_seekers and self._check_skill_seekers():
            return self._extract_with_skill_seekers(pdf_path, skill_name)
        else:
            # 保底方案：使用 PyMuPDF + Qwen OCR
            return self._extract_with_pymupdf(pdf_path, skill_name)
    
    def _check_skill_seekers(self) -> bool:
        """检查 skill-seekers 是否可用"""
        try:
            import skill_seekers
            return True
        except ImportError:
            print("⚠️ skill-seekers 未安装，使用内置方法")
            return False
    
    def _extract_with_skill_seekers(self, pdf_path: str, skill_name: str) -> SkillOutput:
        """
        使用 skill-seekers 库提取
        
        skill-seekers 命令:
        skill-seekers create <source> --output <output_dir>
        skill-seekers package <output_dir> --target claude
        """
        from skill_seekers import create_skill, SkillConfig
        
        # 创建临时输出目录
        temp_output = self.output_dir / f"temp_{skill_name}"
        temp_output.mkdir(exist_ok=True)
        
        # 使用 skill-seekers 创建 skill
        config = SkillConfig(
            source=pdf_path,
            output_dir=str(temp_output),
            enhance=True,
            model="claude"  # 或使用 qwen
        )
        
        result = create_skill(config)
        
        # 读取生成的 skill
        skill_md_path = temp_output / "SKILL.md"
        skill_json_path = temp_output / "skill.json"
        
        # 移动到最终位置
        final_md = self.output_dir / f"{skill_name}_skill.md"
        final_json = self.output_dir / f"{skill_name}_skill.json"
        
        if skill_md_path.exists():
            shutil.move(str(skill_md_path), str(final_md))
        if skill_json_path.exists():
            shutil.move(str(skill_json_path), str(final_json))
        
        # 解析结果
        return self._parse_skill_output(final_json, final_md, skill_name)
    
    def _extract_with_pymupdf(self, pdf_path: str, skill_name: str) -> SkillOutput:
        """
        使用 PyMuPDF + Qwen 提取（保底方案）
        
        流程：
        1. PyMuPDF 读取 PDF
        2. Qwen OCR 识别（如需要）
        3. Qwen 提取结构和主题
        """
        import fitz  # PyMuPDF
        
        print(f"📄 使用 PyMuPDF 读取: {pdf_path}")
        
        # 读取 PDF
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        # 提取文本
        full_text = ""
        for page_num, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                full_text += text + "\n"
            if (page_num + 1) % 50 == 0:
                print(f"  📖 已读取 {page_num + 1}/{total_pages} 页")
        
        doc.close()
        
        print(f"✅ 读取完成: {total_pages} 页, {len(full_text)} 字")
        
        # 使用 Qwen 分析结构
        chapters = self._analyze_structure_with_qwen(full_text, skill_name)
        
        # 生成 Skill 文件
        return self._generate_skill_files(skill_name, full_text, chapters)
    
    def _analyze_structure_with_qwen(self, text: str, book_name: str) -> List[Chapter]:
        """
        使用 Qwen 分析文档结构
        
        提取章节、主题、关键观点
        """
        import openai
        
        # 截取文本（避免太长）
        max_chars = 50000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n... (文本过长，已截断)"
        
        prompt = f"""分析以下图书内容，提取章节结构。

请输出 JSON 格式：
{{
  "chapters": [
    {{"number": 1, "title": "章节标题", "summary": "章节摘要（50字以内）"}},
    ...
  ],
  "themes": ["主题1", "主题2", ...],
  "key_points": ["关键观点1", "关键观点2", ...]
}}

图书名称: {book_name}

内容:
{text[:30000]}

只输出 JSON，不要其他内容。"""

        try:
            client = openai.OpenAI(
                api_key=self.config.qwen_api_key,
                base_url="https://coding.dashscope.aliyuncs.com/v1"
            )
            
            response = client.chat.completions.create(
                model=self.config.qwen_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content
            
            # 解析 JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if json_match:
                data = json.loads(json_match.group())
                
                chapters = [
                    Chapter(
                        number=ch["number"],
                        title=ch["title"],
                        content="",  # 稍后填充
                        word_count=0
                    )
                    for ch in data.get("chapters", [])
                ]
                
                # 保存主题和关键观点
                self._themes = data.get("themes", [])
                self._key_points = data.get("key_points", [])
                
                return chapters
                
        except Exception as e:
            print(f"⚠️ Qwen 分析失败: {e}")
        
        # 保底：简单分章
        return self._simple_chapter_split(text)
    
    def _simple_chapter_split(self, text: str) -> List[Chapter]:
        """简单的章节分割"""
        import re
        
        chapters = []
        lines = text.split("\n")
        
        current_chapter = None
        current_content = []
        chapter_num = 0
        
        chapter_patterns = [
            r'^第[一二三四五六七八九十\d]+[部章节]',
            r'^Chapter\s*\d+',
            r'^[0-9]+\s*$',
        ]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            is_chapter = any(re.match(p, line) for p in chapter_patterns)
            
            if is_chapter and len(line) < 30:
                if current_chapter:
                    current_chapter.content = "\n".join(current_content)
                    current_chapter.word_count = len(current_chapter.content)
                    chapters.append(current_chapter)
                
                chapter_num += 1
                current_chapter = Chapter(
                    number=chapter_num,
                    title=line,
                    content="",
                    word_count=0
                )
                current_content = []
            else:
                if current_chapter:
                    current_content.append(line)
                else:
                    chapter_num = 1
                    current_chapter = Chapter(
                        number=chapter_num,
                        title="正文",
                        content="",
                        word_count=0
                    )
                    current_content = [line]
        
        if current_chapter:
            current_chapter.content = "\n".join(current_content)
            current_chapter.word_count = len(current_chapter.content)
            chapters.append(current_chapter)
        
        return chapters
    
    def _generate_skill_files(
        self, 
        skill_name: str, 
        full_text: str, 
        chapters: List[Chapter]
    ) -> SkillOutput:
        """生成 Skill 文件（JSON + Markdown）"""
        
        # 生成 JSON
        skill_data = {
            "metadata": {
                "title": skill_name,
                "total_pages": len(full_text) // 500,  # 估算
                "total_chapters": len(chapters),
                "word_count": len(full_text),
                "source": "PDF"
            },
            "chapters": [
                {
                    "number": ch.number,
                    "title": ch.title,
                    "content": ch.content[:5000],  # 截断
                    "word_count": ch.word_count
                }
                for ch in chapters
            ],
            "themes": getattr(self, '_themes', []),
            "key_points": getattr(self, '_key_points', [])
        }
        
        json_path = self.output_dir / f"{skill_name}_skill.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(skill_data, f, ensure_ascii=False, indent=2)
        
        # 生成 Markdown
        md_content = self._generate_skill_md(skill_name, skill_data)
        md_path = self.output_dir / f"{skill_name}_skill.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        
        print(f"✅ Skill 生成完成: {len(chapters)} 个章节")
        
        return SkillOutput(
            metadata=skill_data["metadata"],
            chapters=chapters,
            themes=skill_data["themes"],
            key_points=skill_data["key_points"],
            skill_md_path=str(md_path),
            skill_json_path=str(json_path)
        )
    
    def _generate_skill_md(self, skill_name: str, skill_data: Dict) -> str:
        """生成 SKILL.md 内容"""
        
        md = f"""# {skill_name} - Skill

> 本 Skill 由 book-to-podcast 自动生成
> 参考 Skill_Seekers 项目格式

---

## 📖 元数据

| 属性 | 值 |
|------|-----|
| 书名 | {skill_data['metadata']['title']} |
| 章节数 | {skill_data['metadata']['total_chapters']} |
| 字数 | {skill_data['metadata']['word_count']} |

---

## 📚 章节结构

"""
        
        for ch in skill_data["chapters"]:
            md += f"""### 第 {ch['number']} 章: {ch['title']}

**字数**: {ch['word_count']}

**摘要**: 
{ch['content'][:300]}...

---

"""
        
        if skill_data.get("themes"):
            md += "## 🎯 核心主题\n\n"
            for theme in skill_data["themes"]:
                md += f"- {theme}\n"
            md += "\n---\n\n"
        
        if skill_data.get("key_points"):
            md += "## 💡 关键观点\n\n"
            for point in skill_data["key_points"]:
                md += f"- {point}\n"
            md += "\n---\n\n"
        
        md += """## 📝 使用说明

本 Skill 用于将图书内容转换为播客文案。

### 使用方法

```python
from src.skills.book_to_podcast import BookToPodcastPipeline

# 加载 Skill
pipeline = BookToPodcastPipeline()
pipeline.load_skill("无语问上帝_skill.json")

# 生成播客文稿
scripts = pipeline.generate_all_scripts()

# 合成音频
pipeline.synthesize_all_audio(scripts)
```

---

## 版本历史

- v1.0: 初始版本
"""
        
        return md
    
    def _parse_skill_output(
        self, 
        json_path: Path, 
        md_path: Path, 
        skill_name: str
    ) -> SkillOutput:
        """解析 skill-seekers 输出"""
        
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        chapters = [
            Chapter(
                number=ch.get("number", i+1),
                title=ch.get("title", f"第{i+1}章"),
                content=ch.get("content", ""),
                word_count=ch.get("word_count", 0)
            )
            for i, ch in enumerate(data.get("chapters", []))
        ]
        
        return SkillOutput(
            metadata=data.get("metadata", {}),
            chapters=chapters,
            themes=data.get("themes", []),
            key_points=data.get("key_points", []),
            skill_md_path=str(md_path),
            skill_json_path=str(json_path)
        )


# ==================== 便捷函数 ====================

def extract_skill_from_pdf(
    pdf_path: str,
    output_dir: str = "data/skills",
    qwen_api_key: str = ""
) -> SkillOutput:
    """
    从 PDF 提取 Skill
    
    Args:
        pdf_path: PDF 文件路径
        output_dir: 输出目录
        qwen_api_key: Qwen API Key
    
    Returns:
        SkillOutput 对象
    """
    config = PDFSkillConfig(
        output_dir=output_dir,
        qwen_api_key=qwen_api_key
    )
    extractor = PDFSkillExtractor(config)
    return extractor.extract(pdf_path)