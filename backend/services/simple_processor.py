"""简化版处理器
支持：
1. OCR 文字识别
2. 章节提取
3. 选择性生成文稿和音频
"""
import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path
from typing import List, Dict
import fitz  # PyMuPDF

sys.path.insert(0, str(Path(__file__).parent.parent))
from models.task import TaskStatus
from services.task_manager import task_manager


class SimpleProcessor:
    """简化版处理器"""
    
    def __init__(self, task_id: str, qwen_api_key: str):
        self.task_id = task_id
        self.qwen_api_key = qwen_api_key
        self.task_dir = Path("data") / task_id
        self.task_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (self.task_dir / "audio").mkdir(exist_ok=True)
        (self.task_dir / "scripts").mkdir(exist_ok=True)
    
    async def process(self, pdf_content: bytes, filename: str) -> List[Dict]:
        """处理 PDF：OCR + 章节提取"""
        
        # 更新状态
        task_manager.update_progress(
            self.task_id,
            TaskStatus.OCR_PROCESSING,
            5,
            "保存 PDF 文件..."
        )
        
        # 保存 PDF
        pdf_path = self.task_dir / filename
        with open(pdf_path, "wb") as f:
            f.write(pdf_content)
        
        # PDF 转图片
        task_manager.update_progress(
            self.task_id,
            TaskStatus.OCR_PROCESSING,
            10,
            "转换 PDF 为图片..."
        )
        
        images = self._pdf_to_images(pdf_path)
        
        # OCR 识别
        task_manager.update_progress(
            self.task_id,
            TaskStatus.OCR_PROCESSING,
            20,
            "OCR 文字识别..."
        )
        
        all_text = []
        for i, img_path in enumerate(images):
            progress = 20 + int((i / len(images)) * 30)
            task_manager.update_progress(
                self.task_id,
                TaskStatus.OCR_PROCESSING,
                progress,
                f"OCR 处理 {i+1}/{len(images)} 页"
            )
            
            text = await self._ocr_image(img_path)
            all_text.append(text)
            await asyncio.sleep(0.3)
        
        # 合并文本
        full_text = "\n\n--- PAGE ---\n\n".join(all_text)
        
        # 保存全文
        with open(self.task_dir / "full_text.txt", "w", encoding="utf-8") as f:
            f.write(full_text)
        
        # 提取章节
        task_manager.update_progress(
            self.task_id,
            TaskStatus.SCRIPT_GENERATING,
            50,
            "分析章节结构..."
        )
        
        chapters = self._extract_chapters(full_text)
        
        # 保存章节
        with open(self.task_dir / "chapters.json", "w", encoding="utf-8") as f:
            json.dump(chapters, f, ensure_ascii=False, indent=2)
        
        return chapters
    
    def _pdf_to_images(self, pdf_path: Path, dpi: int = 150) -> List[str]:
        """PDF 转图片"""
        doc = fitz.open(str(pdf_path))
        images_dir = self.task_dir / "images"
        images_dir.mkdir(exist_ok=True)
        
        images = []
        for i, page in enumerate(doc):
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            img_path = images_dir / f"page_{i+1:04d}.png"
            pix.save(str(img_path))
            images.append(str(img_path))
        
        doc.close()
        return images
    
    async def _ocr_image(self, img_path: str) -> str:
        """OCR 单张图片"""
        import base64
        import openai
        
        with open(img_path, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode()
        
        client = openai.OpenAI(
            api_key=self.qwen_api_key,
            base_url="https://coding.dashscope.aliyuncs.com/v1"
        )
        
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": "请识别这张图片中的所有中文文字，保持原文格式。"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
            ]
        }]
        
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model="qwen3.5-plus",
                messages=messages,
                max_tokens=2000
            )
        )
        
        return response.choices[0].message.content
    
    def _extract_chapters(self, text: str) -> List[Dict]:
        """提取章节"""
        import re
        
        chapters = []
        lines = text.split("\n")
        
        patterns = [
            r'^第[一二三四五六七八九十\d]+[部章节]',
            r'^[0-9]+\s*$',
            r'^[一二三四五六七八九十]+[、.．]',
        ]
        
        current_chapter = None
        current_content = []
        chapter_num = 0
        
        for line in lines:
            line = line.strip()
            if not line or line == "--- PAGE ---":
                continue
            
            is_chapter = any(re.match(p, line) for p in patterns)
            
            if is_chapter and len(line) < 30:
                if current_chapter and current_content:
                    current_chapter["content"] = "\n".join(current_content)
                    chapters.append(current_chapter)
                
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
                elif len(current_content) < 20:
                    current_content.append(line)
        
        if current_chapter and current_content:
            current_chapter["content"] = "\n".join(current_content)
            chapters.append(current_chapter)
        
        return chapters if chapters else [{"number": 1, "title": "正文", "content": text[:10000]}]
    
    async def generate_script(self, chapter: Dict) -> Dict:
        """生成播客文稿"""
        import openai
        
        prompt = f"""将以下图书章节转换为双人对话式播客文案。

章节: 第 {chapter['number']} 章 - {chapter['title']}

内容:
{chapter['content'][:5000]}

要求:
1. 主持人: 小北（活泼好奇）和阿南（沉稳博学）
2. 格式: JSON
3. 约 40 句对话

输出 JSON 格式:
{{"chapter_number": {chapter['number']}, "chapter_title": "{chapter['title']}", "dialogues": [{{"speaker": "小北", "content": "..."}}, ...]}}"""
        
        client = openai.OpenAI(
            api_key=self.qwen_api_key,
            base_url="https://coding.dashscope.aliyuncs.com/v1"
        )
        
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model="qwen3.5-plus",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=3000
            )
        )
        
        result = response.choices[0].message.content
        
        # 解析 JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            return json.loads(json_match.group())
        
        return {
            "chapter_number": chapter["number"],
            "chapter_title": chapter["title"],
            "dialogues": [
                {"speaker": "小北", "content": f"大家好，今天我们来看第{chapter['number']}章。"},
                {"speaker": "阿南", "content": f"这章的标题是「{chapter['title']}」"}
            ]
        }
    
    async def synthesize_audio(self, dialogues: List[Dict], output_path: str) -> float:
        """合成音频（使用 edge-tts）"""
        temp_files = []
        
        for i, d in enumerate(dialogues):
            speaker = d["speaker"]
            content = d["content"]
            voice = "zh-CN-XiaoxiaoNeural" if speaker == "小北" else "zh-CN-YunxiNeural"
            temp_path = str(self.task_dir / "audio" / f"temp_{i}.mp3")
            
            cmd = ["edge-tts", "--voice", voice, "--text", content, "--write-media", temp_path]
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            
            if Path(temp_path).exists() and Path(temp_path).stat().st_size > 0:
                temp_files.append(temp_path)
        
        if not temp_files:
            return 0
        
        # 合并
        list_file = self.task_dir / "audio" / "merge_list.txt"
        with open(list_file, "w") as f:
            for af in temp_files:
                f.write(f"file '{Path(af).absolute()}'\n")
        
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_file), "-c", "copy", output_path
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        
        # 清理
        for f in temp_files:
            Path(f).unlink(missing_ok=True)
        list_file.unlink(missing_ok=True)
        
        # 获取时长
        if Path(output_path).exists():
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries",
                 "format=duration", "-of", "csv=p=0", output_path],
                capture_output=True, text=True
            )
            try:
                return float(result.stdout.strip())
            except:
                return 0
        return 0