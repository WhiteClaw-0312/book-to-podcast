"""PDF OCR 解析器 - 使用视觉模型提取扫描版 PDF 文本"""

import base64
import io
from pathlib import Path
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF
from PIL import Image
from openai import OpenAI
from pydantic import BaseModel


class OCROptions(BaseModel):
    """OCR 选项"""
    api_key: str
    base_url: str = "https://coding.dashscope.aliyuncs.com/v1"
    model: str = "qwen3.5-plus"
    dpi: int = 150  # 图片分辨率
    language: str = "chinese"  # 语言提示


class PDFOCRParser:
    """PDF OCR 解析器 - 使用视觉模型提取扫描版 PDF"""
    
    SYSTEM_PROMPT = """你是一个专业的OCR文本提取专家。请仔细识别图片中的所有文字内容，并按照原文格式输出。

要求：
1. 完整提取所有文字，不要遗漏
2. 保持原文的段落格式和换行
3. 如果是表格，保持表格结构
4. 不要添加任何解释或说明，只输出识别的文字
5. 如果图片中没有文字，输出 [空白页]"""
    
    def __init__(self, file_path: str | Path, options: OCROptions):
        self.file_path = Path(file_path)
        self.options = options
        self.doc = None
        self.client = OpenAI(
            api_key=options.api_key,
            base_url=options.base_url
        )
    
    def load(self) -> None:
        """加载 PDF 文件"""
        self.doc = fitz.open(self.file_path)
    
    def close(self) -> None:
        """关闭文档"""
        if self.doc:
            self.doc.close()
    
    def page_to_image(self, page_num: int) -> str:
        """将 PDF 页面转换为 base64 图片"""
        if not self.doc:
            self.load()
        
        page = self.doc[page_num]
        mat = fitz.Matrix(self.options.dpi / 72, self.options.dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        
        # 转换为 PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # 转换为 base64
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        return img_base64
    
    def ocr_page(self, page_num: int) -> str:
        """使用视觉模型 OCR 单页"""
        img_base64 = self.page_to_image(page_num)
        
        response = self.client.chat.completions.create(
            model=self.options.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
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
                            "text": f"请识别这张图片中的所有{self.options.language}文字内容："
                        }
                    ]
                }
            ],
            max_tokens=4096
        )
        
        return response.choices[0].message.content
    
    def extract_all(self, start_page: int = 0, end_page: Optional[int] = None) -> Dict[str, Any]:
        """提取所有页面的文本"""
        if not self.doc:
            self.load()
        
        total_pages = len(self.doc)
        end_page = end_page or total_pages
        end_page = min(end_page, total_pages)
        
        results = {
            "metadata": self._get_metadata(),
            "pages": [],
            "total_pages": total_pages,
            "processed_pages": end_page - start_page
        }
        
        for page_num in range(start_page, end_page):
            print(f"正在处理第 {page_num + 1}/{total_pages} 页...")
            text = self.ocr_page(page_num)
            results["pages"].append({
                "page_num": page_num + 1,
                "text": text
            })
        
        return results
    
    def _get_metadata(self) -> Dict[str, Any]:
        """获取 PDF 元数据"""
        if not self.doc:
            self.load()
        meta = self.doc.metadata
        return {
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "page_count": len(self.doc),
        }
    
    def __enter__(self):
        self.load()
        return self
    
    def __exit__(self, *args):
        self.close()


def parse_pdf_with_ocr(
    file_path: str | Path,
    api_key: str,
    start_page: int = 0,
    end_page: Optional[int] = None,
    dpi: int = 150
) -> Dict[str, Any]:
    """使用 OCR 解析扫描版 PDF"""
    options = OCROptions(api_key=api_key, dpi=dpi)
    
    with PDFOCRParser(file_path, options) as parser:
        return parser.extract_all(start_page, end_page)