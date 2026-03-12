"""
PDF 转 Skill 完整流程
1. PDF → 图片序列
2. 图片 → Qwen3.5-plus OCR
3. OCR结果 → Skill结构
"""

import base64
import io
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from PIL import Image
import fitz  # PyMuPDF
from openai import OpenAI
from pydantic import BaseModel, Field


class PDFOptions(BaseModel):
    """PDF处理选项"""
    dpi: int = 200
    image_format: str = "JPEG"
    quality: int = 85


class OCROptions(BaseModel):
    """OCR选项"""
    api_key: str
    base_url: str = "https://coding.dashscope.aliyuncs.com/v1"
    model: str = "qwen3.5-plus"


class SkillChapter(BaseModel):
    """Skill章节"""
    number: int
    title: str
    content: str
    key_points: List[str] = Field(default_factory=list)


class SkillMetadata(BaseModel):
    """Skill元数据"""
    title: str
    author: str
    total_pages: int
    total_chapters: int
    created_at: str


class BookSkill(BaseModel):
    """图书Skill"""
    metadata: SkillMetadata
    chapters: List[SkillChapter]
    themes: List[str] = Field(default_factory=list)
    characters: List[Dict[str, str]] = Field(default_factory=list)
    
    def to_markdown(self) -> str:
        """转换为Markdown格式"""
        lines = [
            f"# {self.metadata.title}",
            "",
            f"**作者:** {self.metadata.author}",
            f"**页数:** {self.metadata.total_pages}",
            f"**章节数:** {self.metadata.total_chapters}",
            "",
            "---",
            ""
        ]
        
        for chapter in self.chapters:
            lines.extend([
                f"## 第{chapter.number}章: {chapter.title}",
                "",
                chapter.content,
                ""
            ])
            
            if chapter.key_points:
                lines.append("**要点:**")
                for point in chapter.key_points:
                    lines.append(f"- {point}")
                lines.append("")
        
        if self.themes:
            lines.extend([
                "---",
                "",
                "## 核心主题",
                ""
            ])
            for theme in self.themes:
                lines.append(f"- {theme}")
            lines.append("")
        
        return "\n".join(lines)


class PDFToSkillConverter:
    """PDF转Skill转换器"""
    
    OCR_PROMPT = """你是一个专业的OCR文本提取专家。请仔细识别图片中的所有文字内容。

要求：
1. 完整提取所有文字，不要遗漏
2. 保持原文的段落格式
3. 如果有标题，用 ## 标记
4. 识别页码（如果有）
5. 如果图片中没有文字，返回 [空白页]

直接输出识别的文字，不要添加任何解释。"""

    CHAPTER_PROMPT = """你是一个专业的图书内容分析专家。请分析以下文本，提取章节信息。

输入文本：
{text}

请输出JSON格式：
{{
    "chapter_number": 章节编号（数字）,
    "chapter_title": "章节标题",
    "content": "章节主要内容（精简版）",
    "key_points": ["要点1", "要点2", ...]
}}
"""

    SKILL_PROMPT = """你是一个专业的知识库构建专家。请基于以下书籍内容生成一个结构化的Skill。

书籍内容：
{content}

请输出JSON格式：
{{
    "title": "书名",
    "author": "作者",
    "themes": ["主题1", "主题2", ...],
    "characters": [
        {{"name": "人物名", "description": "描述"}},
        ...
    ],
    "summary": "全书摘要"
}}
"""

    def __init__(
        self,
        pdf_path: str | Path,
        api_key: str,
        output_dir: str | Path = "data/skills"
    ):
        self.pdf_path = Path(pdf_path)
        self.api_key = api_key
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.pdf_options = PDFOptions()
        self.ocr_options = OCROptions(api_key=api_key)
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=self.ocr_options.base_url
        )
        
        self.doc = None
        self.images_dir = self.output_dir / "images"
        self.images_dir.mkdir(exist_ok=True)
    
    def load_pdf(self) -> None:
        """加载PDF文件"""
        self.doc = fitz.open(self.pdf_path)
        print(f"✅ PDF加载成功: {len(self.doc)} 页")
    
    def close_pdf(self) -> None:
        """关闭PDF文件"""
        if self.doc:
            self.doc.close()
    
    def page_to_image(self, page_num: int) -> str:
        """
        将PDF页面转换为图片并保存
        
        Returns:
            图片路径
        """
        if not self.doc:
            self.load_pdf()
        
        page = self.doc[page_num]
        mat = fitz.Matrix(self.pdf_options.dpi / 72, self.pdf_options.dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        
        # 转换为PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # 保存图片
        img_path = self.images_dir / f"page_{page_num + 1:04d}.jpg"
        img.save(img_path, format="JPEG", quality=self.pdf_options.quality)
        
        return str(img_path)
    
    def image_to_base64(self, img_path: str) -> str:
        """将图片转换为base64"""
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def ocr_page(self, page_num: int) -> str:
        """
        使用Qwen3.5-plus OCR单页
        
        Returns:
            识别的文本
        """
        # 转换为图片
        img_path = self.page_to_image(page_num)
        img_base64 = self.image_to_base64(img_path)
        
        # 调用API
        response = self.client.chat.completions.create(
            model=self.ocr_options.model,
            messages=[
                {"role": "system", "content": self.OCR_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "请识别这张图片中的所有中文文字内容："
                        }
                    ]
                }
            ],
            max_tokens=4096
        )
        
        return response.choices[0].message.content
    
    def extract_all_pages(self, start: int = 0, end: Optional[int] = None) -> Dict[int, str]:
        """
        提取所有页面的文本
        
        Args:
            start: 起始页码（0-indexed）
            end: 结束页码（不包含）
        
        Returns:
            页码到文本的映射
        """
        if not self.doc:
            self.load_pdf()
        
        total = len(self.doc)
        end = min(end or total, total)
        
        results = {}
        
        for page_num in range(start, end):
            print(f"📄 处理第 {page_num + 1}/{total} 页...", end=" ")
            
            text = self.ocr_page(page_num)
            results[page_num + 1] = text
            
            # 显示字数
            char_count = len(text)
            print(f"✅ {char_count} 字符")
        
        return results
    
    def detect_chapters(self, pages_text: Dict[int, str]) -> List[Dict[str, Any]]:
        """
        检测章节边界
        
        Returns:
            章节列表
        """
        chapters = []
        current_chapter = None
        current_content = []
        
        # 章节标题模式
        import re
        chapter_patterns = [
            r'^第[一二三四五六七八九十百]+[章部节]',
            r'^Chapter\s*\d+',
            r'^\d+\.\s+.+',
            r'^[一二三四五六七八九十]+[、.．]\s*.+',
        ]
        
        for page_num in sorted(pages_text.keys()):
            text = pages_text[page_num]
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 检查是否是章节标题
                is_chapter = False
                for pattern in chapter_patterns:
                    if re.match(pattern, line):
                        # 保存上一章节
                        if current_chapter:
                            chapters.append({
                                "title": current_chapter,
                                "content": "\n".join(current_content),
                                "pages": []
                            })
                        
                        current_chapter = line
                        current_content = []
                        is_chapter = True
                        break
                
                if not is_chapter and current_chapter:
                    current_content.append(line)
        
        # 保存最后一章
        if current_chapter:
            chapters.append({
                "title": current_chapter,
                "content": "\n".join(current_content),
                "pages": []
            })
        
        return chapters
    
    def generate_skill(
        self,
        pages_text: Dict[int, str],
        book_title: str = "未知书名",
        author: str = "未知作者"
    ) -> BookSkill:
        """
        生成完整的Skill
        """
        from datetime import datetime
        
        # 检测章节
        chapters_data = self.detect_chapters(pages_text)
        
        # 如果没有检测到章节，创建一个默认章节
        if not chapters_data:
            all_text = "\n".join(pages_text.values())
            chapters_data = [{
                "title": "正文",
                "content": all_text
            }]
        
        # 构建章节
        chapters = []
        for i, ch_data in enumerate(chapters_data):
            chapter = SkillChapter(
                number=i + 1,
                title=ch_data["title"],
                content=ch_data["content"],
                key_points=[]
            )
            chapters.append(chapter)
        
        # 创建元数据
        metadata = SkillMetadata(
            title=book_title,
            author=author,
            total_pages=len(pages_text),
            total_chapters=len(chapters),
            created_at=datetime.now().isoformat()
        )
        
        return BookSkill(
            metadata=metadata,
            chapters=chapters
        )
    
    def save_skill(self, skill: BookSkill, filename: str = None) -> Path:
        """
        保存Skill到文件
        """
        if not filename:
            filename = f"{skill.metadata.title}_skill.json"
        
        # 保存JSON
        json_path = self.output_dir / filename
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(skill.model_dump(), f, ensure_ascii=False, indent=2)
        
        # 保存Markdown
        md_path = json_path.with_suffix(".md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(skill.to_markdown())
        
        print(f"✅ Skill已保存:")
        print(f"   JSON: {json_path}")
        print(f"   Markdown: {md_path}")
        
        return json_path
    
    def convert(
        self,
        start_page: int = 0,
        end_page: Optional[int] = None,
        book_title: str = None,
        author: str = None
    ) -> BookSkill:
        """
        完整转换流程
        """
        print(f"\n{'='*50}")
        print(f"PDF转Skill转换器")
        print(f"{'='*50}")
        print(f"输入文件: {self.pdf_path.name}")
        print(f"{'='*50}\n")
        
        # 步骤1: 提取所有页面
        print("📋 步骤1: OCR提取页面内容")
        pages_text = self.extract_all_pages(start_page, end_page)
        
        total_chars = sum(len(t) for t in pages_text.values())
        print(f"\n✅ OCR完成: {len(pages_text)}页, 共{total_chars}字符\n")
        
        # 步骤2: 生成Skill
        print("🔧 步骤2: 生成Skill结构")
        skill = self.generate_skill(
            pages_text,
            book_title=book_title or self.pdf_path.stem,
            author=author or "未知"
        )
        
        print(f"✅ Skill生成完成: {skill.metadata.total_chapters}个章节\n")
        
        # 步骤3: 保存
        print("💾 步骤3: 保存Skill")
        self.save_skill(skill)
        
        return skill
    
    def __enter__(self):
        self.load_pdf()
        return self
    
    def __exit__(self, *args):
        self.close_pdf()


def convert_pdf_to_skill(
    pdf_path: str,
    api_key: str,
    output_dir: str = "data/skills",
    start_page: int = 0,
    end_page: Optional[int] = None,
    book_title: str = None,
    author: str = None
) -> BookSkill:
    """
    将PDF转换为Skill
    
    使用示例:
        skill = convert_pdf_to_skill(
            pdf_path="data/books/无语问上帝.pdf",
            api_key="your_api_key",
            output_dir="data/skills",
            start_page=14,  # 从第15页开始（正文）
            end_page=20,   # 测试前5页
            book_title="无语问上帝",
            author="菲利普·杨西"
        )
    """
    with PDFToSkillConverter(pdf_path, api_key, output_dir) as converter:
        return converter.convert(start_page, end_page, book_title, author)