"""
PDF 转 Skill 转换器
参考 Skill_Seekers 项目实现
核心流程: Ingest → Analyze → Structure → Enhance → Export
"""

import os
import json
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel
from dataclasses import dataclass, field


class SkillConfig(BaseModel):
    """Skill 配置"""
    # 输入输出
    input_path: str = ""
    output_dir: str = "data/skills"
    
    # PDF 处理
    dpi: int = 200
    ocr_engine: str = "qwen3.5-plus"  # OCR 引擎
    
    # Skill 生成
    max_content_length: int = 50000   # 最大内容长度
    include_images: bool = False       # 是否包含图片
    
    # AI 增强
    enhance_skill: bool = True         # 是否 AI 增强
    enhance_model: str = "qwen3.5-plus"


@dataclass
class Chapter:
    """章节"""
    number: int
    title: str
    content: str
    start_page: int = 0
    end_page: int = 0


@dataclass
class SkillMetadata:
    """Skill 元数据"""
    title: str = ""
    author: str = ""
    total_pages: int = 0
    total_chapters: int = 0
    word_count: int = 0
    created_at: str = ""


class PDFToSkillConverter:
    """
    PDF 转 Skill 转换器
    
    参考 Skill_Seekers 项目：
    - 核心流程: Ingest → Analyze → Structure → Enhance → Export
    - 生成 500+ 行的完整 SKILL.md
    """
    
    def __init__(self, config: Optional[SkillConfig] = None):
        self.config = config or SkillConfig()
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 存储解析结果
        self.metadata: Optional[SkillMetadata] = None
        self.chapters: List[Chapter] = []
        self.full_text: str = ""
    
    # ==================== Step 1: Ingest ====================
    
    def ingest_pdf(self, pdf_path: str) -> bool:
        """
        Step 1: 读取 PDF
        
        Args:
            pdf_path: PDF 文件路径
        
        Returns:
            是否成功
        """
        try:
            doc = fitz.open(pdf_path)
            
            # 提取元数据
            self.metadata = SkillMetadata(
                title=Path(pdf_path).stem,
                total_pages=len(doc),
                created_at=self._get_current_time()
            )
            
            # 提取文本
            self.full_text = ""
            for page_num, page in enumerate(doc):
                text = page.get_text()
                self.full_text += text + "\n"
            
            self.metadata.word_count = len(self.full_text)
            doc.close()
            
            print(f"✅ 读取完成: {self.metadata.total_pages} 页, {self.metadata.word_count} 字")
            return True
            
        except Exception as e:
            print(f"❌ 读取 PDF 失败: {e}")
            return False
    
    def ingest_text(self, text: str, title: str = "未知文档") -> bool:
        """
        Step 1: 读取文本内容
        
        Args:
            text: 文本内容
            title: 文档标题
        """
        self.metadata = SkillMetadata(
            title=title,
            word_count=len(text),
            created_at=self._get_current_time()
        )
        self.full_text = text
        return True
    
    # ==================== Step 2: Analyze ====================
    
    def analyze_structure(self) -> List[Chapter]:
        """
        Step 2: 分析文档结构
        
        识别章节、标题层级等
        """
        if not self.full_text:
            return []
        
        chapters = []
        lines = self.full_text.split("\n")
        
        # 章节识别模式
        chapter_patterns = [
            r'^第[一二三四五六七八九十\d]+[部章]',  # 第一章、第一部
            r'^[0-9]+\s*$',                          # 纯数字（章节号）
            r'^Chapter\s*\d+',                       # Chapter 1
            r'^[一二三四五六七八九十]+[、.．]',      # 一、二、三、
        ]
        
        import re
        
        current_chapter = None
        current_content = []
        chapter_num = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检查是否是章节标题
            is_chapter_title = False
            for pattern in chapter_patterns:
                if re.match(pattern, line):
                    is_chapter_title = True
                    break
            
            # 检查是否是短行（可能是标题）
            if len(line) < 30 and not is_chapter_title:
                # 如果前一行是空行，这一行可能是标题
                is_chapter_title = True
            
            if is_chapter_title and len(line) < 50:
                # 保存当前章节
                if current_chapter and current_content:
                    current_chapter.content = "\n".join(current_content)
                    chapters.append(current_chapter)
                
                # 开始新章节
                chapter_num += 1
                current_chapter = Chapter(
                    number=chapter_num,
                    title=line
                )
                current_content = []
            else:
                # 添加到当前章节内容
                if current_chapter:
                    current_content.append(line)
                else:
                    # 还没有章节，创建默认章节
                    chapter_num = 1
                    current_chapter = Chapter(
                        number=chapter_num,
                        title="正文",
                        content=""
                    )
                    current_content = [line]
        
        # 保存最后一个章节
        if current_chapter and current_content:
            current_chapter.content = "\n".join(current_content)
            chapters.append(current_chapter)
        
        self.chapters = chapters
        self.metadata.total_chapters = len(chapters)
        
        print(f"✅ 结构分析完成: {len(chapters)} 个章节")
        return chapters
    
    # ==================== Step 3: Structure ====================
    
    def structure_skill(self) -> Dict:
        """
        Step 3: 结构化为 Skill 格式
        
        生成结构化的 Skill 数据
        """
        if not self.chapters:
            self.analyze_structure()
        
        skill_data = {
            "metadata": {
                "title": self.metadata.title,
                "author": self.metadata.author,
                "total_pages": self.metadata.total_pages,
                "total_chapters": self.metadata.total_chapters,
                "word_count": self.metadata.word_count,
                "created_at": self.metadata.created_at
            },
            "chapters": [
                {
                    "number": ch.number,
                    "title": ch.title,
                    "content": ch.content,
                    "word_count": len(ch.content)
                }
                for ch in self.chapters
            ],
            "themes": [],
            "characters": [],
            "key_points": []
        }
        
        return skill_data
    
    # ==================== Step 4: Enhance ====================
    
    def enhance_skill(self, skill_data: Dict, api_key: str = "") -> Dict:
        """
        Step 4: AI 增强 Skill
        
        提取主题、人物、关键观点等
        """
        if not self.config.enhance_skill:
            return skill_data
        
        # TODO: 调用 LLM 进行增强
        # - 提取主题
        # - 提取人物
        # - 提取关键观点
        # - 生成摘要
        
        return skill_data
    
    # ==================== Step 5: Export ====================
    
    def export_json(self, skill_data: Dict, output_name: str = None) -> str:
        """
        Step 5a: 导出 JSON 格式
        """
        if not output_name:
            output_name = f"{self.metadata.title}_skill"
        
        output_path = self.output_dir / f"{output_name}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(skill_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ JSON 导出完成: {output_path}")
        return str(output_path)
    
    def export_markdown(self, skill_data: Dict, output_name: str = None) -> str:
        """
        Step 5b: 导出 Markdown 格式（SKILL.md）
        
        参考 Skill_Seekers 的 SKILL.md 格式：
        - 500+ 行
        - 包含示例、模式、指南
        """
        if not output_name:
            output_name = f"{self.metadata.title}_skill"
        
        md_content = self._generate_skill_md(skill_data)
        
        output_path = self.output_dir / f"{output_name}.md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        
        print(f"✅ Markdown 导出完成: {output_path}")
        return str(output_path)
    
    def _generate_skill_md(self, skill_data: Dict) -> str:
        """生成 SKILL.md 内容"""
        metadata = skill_data.get("metadata", {})
        chapters = skill_data.get("chapters", [])
        
        md = f"""# {metadata.get('title', '未知文档')} - Skill

## 元数据
- **书名**: {metadata.get('title', '未知')}
- **作者**: {metadata.get('author', '未知')}
- **章节数**: {metadata.get('total_chapters', 0)}
- **字数**: {metadata.get('word_count', 0)}
- **生成时间**: {metadata.get('created_at', '')}

## 概述
本书共有 {len(chapters)} 个章节，总字数约 {metadata.get('word_count', 0)} 字。

---

## 章节结构

"""
        
        for ch in chapters:
            md += f"""### 第 {ch['number']} 章: {ch['title']}

**字数**: {ch.get('word_count', 0)}

**内容摘要**:
{ch['content'][:500]}...

---

"""
        
        md += """## 核心主题

（待 AI 增强）

## 关键人物

（待 AI 增强）

## 重要观点

（待 AI 增强）

---

## 使用说明

本 Skill 用于将图书内容转换为播客文案。使用时：

1. 读取对应章节的内容
2. 调用播客文案生成 Skill
3. 转换为双人对话格式

## 版本历史

- v1.0: 初始版本
"""
        
        return md
    
    # ==================== 完整流程 ====================
    
    def convert(
        self,
        input_path: str = None,
        text: str = None,
        title: str = None,
        output_name: str = None,
        export_format: str = "both"  # json, markdown, both
    ) -> Tuple[str, str]:
        """
        完整转换流程
        
        Args:
            input_path: PDF 文件路径
            text: 直接传入的文本
            title: 文档标题
            output_name: 输出文件名
            export_format: 导出格式
        
        Returns:
            (json_path, md_path) 或 None
        """
        # Step 1: Ingest
        if input_path:
            if not self.ingest_pdf(input_path):
                return None, None
        elif text:
            self.ingest_text(text, title or "未知文档")
        else:
            print("❌ 请提供输入文件或文本")
            return None, None
        
        # Step 2: Analyze
        self.analyze_structure()
        
        # Step 3: Structure
        skill_data = self.structure_skill()
        
        # Step 4: Enhance (可选)
        # skill_data = self.enhance_skill(skill_data)
        
        # Step 5: Export
        json_path = ""
        md_path = ""
        
        if export_format in ["json", "both"]:
            json_path = self.export_json(skill_data, output_name)
        
        if export_format in ["markdown", "both"]:
            md_path = self.export_markdown(skill_data, output_name)
        
        return json_path, md_path
    
    def _get_current_time(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()


# ==================== 便捷函数 ====================

def convert_pdf_to_skill(
    pdf_path: str,
    output_dir: str = "data/skills",
    output_name: str = None
) -> Tuple[str, str]:
    """
    将 PDF 转换为 Skill
    
    Args:
        pdf_path: PDF 文件路径
        output_dir: 输出目录
        output_name: 输出文件名
    
    Returns:
        (json_path, md_path)
    """
    config = SkillConfig(output_dir=output_dir)
    converter = PDFToSkillConverter(config)
    return converter.convert(input_path=pdf_path, output_name=output_name)