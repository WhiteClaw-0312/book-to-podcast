"""图书解析模块 - 支持 PDF/EPUB 格式"""

from .pdf_parser import PDFParser
from .epub_parser import EPUBParser

__all__ = ["PDFParser", "EPUBParser"]