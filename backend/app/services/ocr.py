"""OCR 服务 - 智能识别 PDF"""
import asyncio
import base64
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
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
    
    # ==================== PDF 文本提取 ====================
    
    async def extract_text(self, pdf_path: str) -> Tuple[str, bool, List[str]]:
        """
        提取 PDF 文本
        返回: (文本内容, 是否使用了OCR, 页面列表)
        """
        # 先尝试直接提取（原生 PDF）
        text, pages = self._extract_native(pdf_path)
        
        # 如果提取到的文字太少，说明是扫描版
        if len(text.strip()) < 500:
            text, pages = await self._ocr_scan(pdf_path)
            return text, True, pages
        
        return text, False, pages
    
    def _extract_native(self, pdf_path: str) -> Tuple[str, List[str]]:
        """原生 PDF 直接提取文字"""
        doc = fitz.open(pdf_path)
        text_parts = []
        pages = []
        
        for page_num, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                pages.append(text)
                text_parts.append(f"--- PAGE {page_num + 1} ---\n{text}")
        
        doc.close()
        return "\n\n".join(text_parts), pages
    
    async def _ocr_scan(self, pdf_path: str) -> Tuple[str, List[str]]:
        """扫描版 PDF 调用 OCR API"""
        doc = fitz.open(pdf_path)
        results = []
        pages = []
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
                pages.append(page_text)
                results.append(f"--- PAGE {page_num + 1} ---\n{page_text}")
                
            except Exception as e:
                pages.append(f"[OCR 识别失败: {str(e)}]")
                results.append(f"--- PAGE {page_num + 1} ---\n[OCR 识别失败: {str(e)}]")
            
            # 避免 API 限流
            await asyncio.sleep(0.3)
        
        doc.close()
        return "\n\n".join(results), pages
    
    # ==================== 章节提取 ====================
    
    def extract_chapters_by_rules(self, text: str, pages: List[str]) -> Tuple[List[Dict], float]:
        """
        规则匹配章节（增强版）
        返回: (章节列表, 置信度 0-1)
        """
        chapters = []
        lines = text.split("\n")
        
        # 增强的章节模式（模式, 置信度）
        patterns = [
            # 标准中文章节
            (r'^第[一二三四五六七八九十百零\d]+[部章节篇回集]', 1.0),
            (r'^第[一二三四五六七八九十百零\d]+[部章节篇回集][：:\s]', 1.0),
            # 数字编号章节
            (r'^[第]\d{1,3}[章节篇]', 0.95),
            (r'^\d{1,3}[\.、]\s*.{2,30}$', 0.8),  # "1. 标题" 格式
            # 英文章节
            (r'^Chapter\s*\d+', 1.0),
            (r'^CHAPTER\s*\d+', 1.0),
            (r'^Part\s*[IVX\d]+', 0.95),
            (r'^Section\s*\d+', 0.85),
            # 特殊章节
            (r'^(引言|序言|前言|楔子|尾声|后记|附录|结语|摘要|Abstract)', 0.9),
            (r'^(目录|目　录|Contents)', 0.95),
            # 带标点的章节
            (r'^[一二三四五六七八九十]+[、\.．]\s*.+', 0.85),
        ]
        
        current_chapter = None
        current_content = []
        current_page_start = 1
        chapter_num = 0
        confidence_scores = []
        current_line_in_page = 0
        page_index = 0
        
        for line in lines:
            line_stripped = line.strip()
            
            # 检测页码
            if line_stripped.startswith("--- PAGE"):
                match = re.match(r'--- PAGE (\d+) ---', line_stripped)
                if match:
                    page_index = int(match.group(1))
                continue
            
            if not line_stripped:
                continue
            
            # 检查是否是章节标题
            is_chapter = False
            chapter_title = None
            best_confidence = 0
            
            for pattern, confidence in patterns:
                match = re.match(pattern, line_stripped)
                if match and len(line_stripped) < 80:  # 标题不超过80字符
                    is_chapter = True
                    chapter_title = line_stripped
                    best_confidence = confidence
                    break
            
            if is_chapter:
                # 保存上一章
                if current_chapter and current_content:
                    current_chapter["content"] = "\n".join(current_content)
                    current_chapter["page_range"] = f"{current_page_start}-{page_index}"
                    chapters.append(current_chapter)
                    confidence_scores.append(current_chapter.get("confidence", 0.5))
                
                # 开始新章节
                chapter_num += 1
                current_page_start = page_index
                current_chapter = {
                    "number": chapter_num,
                    "title": chapter_title,
                    "content": "",
                    "page_range": "",
                    "confidence": best_confidence
                }
                current_content = []
            else:
                if current_chapter:
                    current_content.append(line_stripped)
                elif not chapters:
                    # 还没遇到章节标题，可能是前言
                    current_content.append(line_stripped)
        
        # 保存最后一章
        if current_chapter and current_content:
            current_chapter["content"] = "\n".join(current_content)
            current_chapter["page_range"] = f"{current_page_start}-{page_index}"
            chapters.append(current_chapter)
            confidence_scores.append(current_chapter.get("confidence", 0.5))
        
        # 计算置信度
        if not chapters:
            return [], 0.0
        
        # 综合置信度
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
        
        num_chapters = len(chapters)
        if num_chapters == 1:
            # 单章节时，检查内容是否合理
            content_len = len(chapters[0].get("content", ""))
            if content_len > 500:
                chapter_count_score = 0.8  # 有内容，可能是正确的
            else:
                chapter_count_score = 0.3
        elif num_chapters < 3:
            chapter_count_score = 0.6
        else:
            chapter_count_score = 0.9
        
        overall_confidence = avg_confidence * 0.6 + chapter_count_score * 0.4
        
        # 清理置信度字段
        for ch in chapters:
            ch.pop("confidence", None)
        
        return chapters, overall_confidence
    
    async def analyze_with_llm(self, text: str, pages: List[str]) -> Tuple[bool, List[Dict]]:
        """
        使用 LLM 分析文档结构
        
        返回: (是否需要分章, 章节列表)
        """
        # 采样文本
        sample_text = self._sample_text_for_llm(pages)
        
        prompt = f"""你是一位专业的图书编辑。请分析以下文档，判断是否需要分章，以及如何分章。

文档内容片段（共{len(pages)}页）：
{sample_text}

请输出 JSON 格式：
{{
  "need_chapters": true/false,
  "reason": "判断理由",
  "chapters": [
    {{"number": 1, "title": "章节标题", "start_page": 1, "end_page": 10}},
    {{"number": 2, "title": "章节标题", "start_page": 11, "end_page": 25}}
  ]
}}

重要规则：
1. 如果是学术论文、短文、单篇文章，设置 need_chapters: false，chapters 返回空数组
2. 如果是书籍、长篇报告，设置 need_chapters: true 并划分章节
3. start_page 和 end_page 从1开始，必须覆盖所有页面
4. 章节标题要简洁，如果看不出标题就用"第N章" """

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=settings.QWEN_MODEL,
                    messages=[
                        {"role": "system", "content": "你是专业的图书编辑。只输出 JSON，不要其他内容。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=1500
                )
            )
            
            result = response.choices[0].message.content
            print(f"LLM 分析结果: {result[:500]}...")
            
            # 解析 JSON
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                data = json.loads(json_match.group())
                need_chapters = data.get("need_chapters", True)
                
                chapters = []
                for ch in data.get("chapters", []):
                    start = max(0, ch.get("start_page", 1) - 1)
                    end = min(len(pages), ch.get("end_page", len(pages)))
                    
                    content = "\n\n".join(pages[start:end])
                    
                    chapters.append({
                        "number": ch.get("number", len(chapters) + 1),
                        "title": ch.get("title", f"第{ch.get('number', len(chapters) + 1)}章"),
                        "content": content,
                        "page_range": f"{start + 1}-{end}"
                    })
                
                return need_chapters, chapters
            
        except Exception as e:
            print(f"LLM 分析失败: {e}")
        
        # 失败时返回不分章
        return False, []
    
    def _sample_text_for_llm(self, pages: List[str]) -> str:
        """采样文本供 LLM 分析"""
        samples = []
        
        # 前2页
        for i in range(min(2, len(pages))):
            samples.append(f"【第{i+1}页】\n{pages[i][:1000]}")
        
        # 中间1页
        mid = len(pages) // 2
        if mid < len(pages):
            samples.append(f"【第{mid+1}页】\n{pages[mid][:800]}")
        
        # 最后1页
        if len(pages) > 2:
            samples.append(f"【第{len(pages)}页】\n{pages[-1][:800]}")
        
        return "\n\n".join(samples)[:5000]
    
    async def extract_chapters_smart(self, text: str, pages: List[str], force_llm: bool = False) -> List[Dict]:
        """
        智能章节提取
        
        策略：
        1. 先用规则匹配
        2. 如果置信度高，直接返回
        3. 如果置信度低或只有1章，用 LLM 分析
        4. 如果 LLM 认为不需要分章，作为单一章节处理
        """
        total_pages = len(pages)
        
        # 如果页数很少（<5页），直接作为一整章
        if total_pages <= 5:
            print(f"文档只有 {total_pages} 页，作为单一章节处理")
            return [{
                "number": 1,
                "title": "正文",
                "content": "\n\n".join(pages),
                "page_range": f"1-{total_pages}"
            }]
        
        # 先尝试规则匹配
        chapters, confidence = self.extract_chapters_by_rules(text, pages)
        
        print(f"规则匹配结果: {len(chapters)} 章, 置信度 {confidence:.2f}")
        
        # 如果置信度高且章节数合理，直接返回
        if confidence >= 0.7 and 2 <= len(chapters) <= 30:
            print("规则匹配置信度高，直接使用")
            return chapters
        
        # 如果只识别到1章，检查是否合理
        if len(chapters) == 1:
            content_len = len(chapters[0].get("content", ""))
            # 如果内容足够长（>10000字），可能确实是单章节文档
            if content_len > 10000 and confidence >= 0.5:
                print(f"识别为单章节文档（{content_len} 字），直接返回")
                return chapters
            # 否则用 LLM 分析
            print("只识别到1章且内容较短，启用 LLM 分析")
        elif confidence < 0.5:
            print(f"置信度过低 ({confidence:.2f})，启用 LLM 分析")
        else:
            # 置信度中等，检查章节是否合理
            short_chapters = sum(1 for ch in chapters if len(ch.get("content", "")) < 300)
            if short_chapters > len(chapters) * 0.4:
                print(f"有 {short_chapters} 个章节内容过短，启用 LLM 分析")
            else:
                return chapters
        
        # 使用 LLM 分析
        need_chapters, llm_chapters = await self.analyze_with_llm(text, pages)
        
        if not need_chapters:
            # LLM 认为不需要分章
            print("LLM 判断为单章节文档")
            return [{
                "number": 1,
                "title": "正文",
                "content": "\n\n".join(pages),
                "page_range": f"1-{total_pages}"
            }]
        
        if llm_chapters and len(llm_chapters) > 1:
            print(f"LLM 分章成功: {len(llm_chapters)} 章")
            return llm_chapters
        
        # LLM 也失败，返回单一章节（不再强制拆分）
        print("LLM 分章失败，作为单一章节处理")
        return [{
            "number": 1,
            "title": "正文",
            "content": "\n\n".join(pages),
            "page_range": f"1-{total_pages}"
        }]