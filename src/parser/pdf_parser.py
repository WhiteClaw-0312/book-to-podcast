"""PDF 图书解析器"""

from pathlib import Path
from typing import List, Dict, Any
import fitz  # PyMuPDF


class PDFParser:
    """PDF 图书解析器，提取文本、章节、元数据"""
    
    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self.doc = None
        
    def load(self) -> None:
        """加载 PDF 文件"""
        self.doc = fitz.open(self.file_path)
        
    def close(self) -> None:
        """关闭文档"""
        if self.doc:
            self.doc.close()
            
    def extract_text(self) -> str:
        """提取全部文本"""
        if not self.doc:
            self.load()
        text = ""
        for page in self.doc:
            text += page.get_text()
        return text
    
    def extract_by_page(self) -> List[Dict[str, Any]]:
        """按页提取文本"""
        if not self.doc:
            self.load()
        pages = []
        for i, page in enumerate(self.doc):
            pages.append({
                "page_num": i + 1,
                "text": page.get_text(),
                "metadata": {
                    "width": page.rect.width,
                    "height": page.rect.height,
                }
            })
        return pages
    
    def extract_metadata(self) -> Dict[str, Any]:
        """提取 PDF 元数据"""
        if not self.doc:
            self.load()
        meta = self.doc.metadata
        return {
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "subject": meta.get("subject", ""),
            "keywords": meta.get("keywords", ""),
            "creator": meta.get("creator", ""),
            "producer": meta.get("producer", ""),
            "page_count": len(self.doc),
        }
    
    def detect_chapters(self) -> List[Dict[str, Any]]:
        """检测章节（基于目录或文本模式）"""
        if not self.doc:
            self.load()
        
        chapters = []
        toc = self.doc.get_toc()
        
        if toc:
            # 使用 PDF 内置目录
            for item in toc:
                level, title, page = item
                chapters.append({
                    "level": level,
                    "title": title,
                    "page": page,
                })
        else:
            # 基于文本模式检测章节
            chapters = self._detect_chapters_by_pattern()
            
        return chapters
    
    def _detect_chapters_by_pattern(self) -> List[Dict[str, Any]]:
        """基于文本模式检测章节"""
        chapters = []
        chapter_patterns = [
            r"^第[一二三四五六七八九十百千]+[章节]",
            r"^Chapter\s+\d+",
            r"^\d+\.\s+.+",  # 数字编号
        ]
        # TODO: 实现章节检测逻辑
        return chapters
    
    def __enter__(self):
        self.load()
        return self
    
    def __exit__(self, *args):
        self.close()


def parse_pdf(file_path: str | Path) -> Dict[str, Any]:
    """解析 PDF 文件，返回结构化数据"""
    with PDFParser(file_path) as parser:
        return {
            "metadata": parser.extract_metadata(),
            "text": parser.extract_text(),
            "pages": parser.extract_by_page(),
            "chapters": parser.detect_chapters(),
        }