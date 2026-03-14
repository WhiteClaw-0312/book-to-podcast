"""OCR 服务 - 智能识别 PDF"""
import asyncio
import base64
import re
from pathlib import Path
from typing import List, Dict, Optional
import fitz  # PyMuPDF
from openai import OpenAI
from ..config import settings


class OCRService:
    """OCR 服务 - 智能检测扫描版/原生 PDF"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL
        )
    
    async def extract_text(self, pdf_path: str) -> tuple[str, bool]:
        """
        提取 PDF 文本
        返回: (文本内容, 是否使用了OCR)
        """
        # 先尝试直接提取（原生 PDF）
        text = self._extract_native(pdf_path)
        
        # 如果提取到的文字太少，说明是扫描版
        if len(text.strip()) < 500:
            text = await self._ocr_scan(pdf_path)
            return text, True
        
        return text, False
    
    def _extract_native(self, pdf_path: str) -> str:
        """原生 PDF 直接提取文字"""
        doc = fitz.open(pdf_path)
        text_parts = []
        
        for page_num, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                text_parts.append(f"--- PAGE {page_num + 1} ---\n{text}")
        
        doc.close()
        return "\n\n".join(text_parts)
    
    async def _ocr_scan(self, pdf_path: str) -> str:
        """扫描版 PDF 调用 OCR API"""
        doc = fitz.open(pdf_path)
        results = []
        total_pages = len(doc)
        
        for page_num, page in enumerate(doc):
            # 转图片
            mat = fitz.Matrix(150 / 72, 150 / 72)  # 150 DPI
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            img_base64 = base64.b64encode(img_bytes).decode()
            
            # 调用 Qwen Vision API
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.chat.completions.create(
                        model=settings.QWEN_MODEL,
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "请识别图片中的所有中文文字，保持原文格式和段落结构。只输出识别结果，不要其他内容。"},
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
                            ]
                        }],
                        max_tokens=4000
                    )
                )
                
                page_text = response.choices[0].message.content
                results.append(f"--- PAGE {page_num + 1} ---\n{page_text}")
                
            except Exception as e:
                results.append(f"--- PAGE {page_num + 1} ---\n[OCR 识别失败: {str(e)}]")
            
            # 避免 API 限流
            await asyncio.sleep(0.3)
        
        doc.close()
        return "\n\n".join(results)
    
    def extract_chapters(self, text: str) -> List[Dict]:
        """从文本中提取章节"""
        chapters = []
        lines = text.split("\n")
        
        # 章节模式
        patterns = [
            r'^第[一二三四五六七八九十\d]+[部章节篇]',
            r'^[第]?\d+[章节篇]',
            r'^[一二三四五六七八九十]+[、.．]',
            r'^Chapter\s*\d+',
        ]
        
        current_chapter = None
        current_content = []
        chapter_num = 0
        
        for line in lines:
            line = line.strip()
            
            # 跳过分页标记
            if line.startswith("--- PAGE"):
                continue
            
            if not line:
                continue
            
            # 检查是否是章节标题
            is_chapter = False
            for pattern in patterns:
                if re.match(pattern, line) and len(line) < 50:
                    is_chapter = True
                    break
            
            if is_chapter:
                # 保存上一章
                if current_chapter and current_content:
                    current_chapter["content"] = "\n".join(current_content)
                    chapters.append(current_chapter)
                
                # 开始新章节
                chapter_num += 1
                current_chapter = {
                    "number": chapter_num,
                    "title": line,
                    "content": ""
                }
                current_content = []
            else:
                if current_chapter:
                    current_content.append(line)
                elif not chapters:
                    # 还没遇到章节标题，可能是前言
                    if len("\n".join(current_content)) < 2000:
                        current_content.append(line)
        
        # 保存最后一章
        if current_chapter and current_content:
            current_chapter["content"] = "\n".join(current_content)
            chapters.append(current_chapter)
        
        # 如果没有识别到章节，把全部内容作为一章
        if not chapters:
            chapters.append({
                "number": 1,
                "title": "正文",
                "content": text[:10000]
            })
        
        return chapters