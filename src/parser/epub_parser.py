"""EPUB 图书解析器"""

from pathlib import Path
from typing import List, Dict, Any
from ebooklib import epub


class EPUBParser:
    """EPUB 图书解析器"""
    
    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self.book = None
        
    def load(self) -> None:
        """加载 EPUB 文件"""
        self.book = epub.read_epub(str(self.file_path))
        
    def extract_text(self) -> str:
        """提取全部文本"""
        if not self.book:
            self.load()
        text = ""
        for item in self.book.get_items():
            if item.get_type() == 9:  # ITEM_DOCUMENT
                content = item.get_content()
                # TODO: 解析 HTML 提取纯文本
                text += content.decode('utf-8', errors='ignore')
        return text
    
    def extract_metadata(self) -> Dict[str, Any]:
        """提取元数据"""
        if not self.book:
            self.load()
        return {
            "title": self.book.get_metadata('DC', 'title')[0][0] if self.book.get_metadata('DC', 'title') else "",
            "author": self.book.get_metadata('DC', 'creator')[0][0] if self.book.get_metadata('DC', 'creator') else "",
            "language": self.book.get_metadata('DC', 'language')[0][0] if self.book.get_metadata('DC', 'language') else "",
        }
    
    def get_chapters(self) -> List[Dict[str, Any]]:
        """获取章节"""
        chapters = []
        for item in self.book.get_items():
            if item.get_type() == 9:  # ITEM_DOCUMENT
                chapters.append({
                    "id": item.get_id(),
                    "name": item.get_name(),
                })
        return chapters


def parse_epub(file_path: str | Path) -> Dict[str, Any]:
    """解析 EPUB 文件"""
    parser = EPUBParser(file_path)
    return {
        "metadata": parser.extract_metadata(),
        "text": parser.extract_text(),
        "chapters": parser.get_chapters(),
    }