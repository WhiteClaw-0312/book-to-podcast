"""图书解析模块 - 支持 PDF/EPUB 格式"""

from .pdf_parser import PDFParser
from .epub_parser import EPUBParser
from .pdf_ocr import PDFOCRParser, OCROptions, parse_pdf_with_ocr

__all__ = [
    "PDFParser", 
    "EPUBParser",
    "PDFOCRParser", 
    "OCROptions", 
    "parse_pdf_with_ocr"
]