"""处理服务：PDF → OCR → 文稿 → 音频"""
import os
import sys
import json
import base64
import asyncio
import fitz
import openai
import aiohttp
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from models.task import TaskStatus, ChapterInfo
from services.task_manager import task_manager


class ProcessService:
    """处理服务"""
    
    def __init__(self, task_id: str, qwen_api_key: str, qwen_tts_key: str):
        self.task_id = task_id
        self.qwen_api_key = qwen_api_key
        self.qwen_tts_key = qwen_tts_key
        
        # 目录
        self.base_dir = Path("data") / task_id
        self.pdf_dir = self.base_dir / "pdf"
        self.images_dir = self.base_dir / "images"
        self.scripts_dir = self.base_dir / "scripts"
        self.audio_dir = self.base_dir / "audio"
        
        for d in [self.pdf_dir, self.images_dir, self.scripts_dir, self.audio_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # 客户端
        self.qwen_client = openai.OpenAI(
            api_key=qwen_api_key,
            base_url="https://coding.dashscope.aliyuncs.com/v1"
        )
    
    async def process(self, pdf_content: bytes, filename: str):
        """完整处理流程"""
        try:
            # Step 1: 保存 PDF
            task_manager.update_progress(
                self.task_id, TaskStatus.UPLOADING, 5, "保存 PDF 文件..."
            )
            pdf_path = self.pdf_dir / filename
            with open(pdf_path, "wb") as f:
                f.write(pdf_content)
            
            # Step 2: PDF → 图片
            task_manager.update_progress(
                self.task_id, TaskStatus.OCR_PROCESSING, 10, "转换 PDF 为图片..."
            )
            image_paths = await self._pdf_to_images(pdf_path)
            total_pages = len(image_paths)
            
            # Step 3: OCR 识别
            all_text = []
            for i, img_path in enumerate(image_paths):
                progress = 10 + int((i / total_pages) * 30)
                task_manager.update_progress(
                    self.task_id, TaskStatus.OCR_PROCESSING, progress,
                    f"OCR 识别中... ({i+1}/{total_pages})"
                )
                
                text = await self._ocr_image(img_path)
                all_text.append(text)
                
                await asyncio.sleep(0.3)  # 避免 API 限流
            
            full_text = "\n\n---PAGE---\n\n".join(all_text)
            
            # 保存全文
            with open(self.base_dir / "full_text.txt", "w", encoding="utf-8") as f:
                f.write(full_text)
            
            # Step 4: 提取章节
            task_manager.update_progress(
                self.task_id, TaskStatus.SCRIPT_GENERATING, 45, "分析章节结构..."
            )
            chapters = self._extract_chapters(full_text)
            total_chapters = len(chapters)
            
            # Step 5: 生成文稿 + 音频（并发）
            task_manager.update_progress(
                self.task_id, TaskStatus.AUDIO_SYNTHESIZING, 50, "生成播客..."
            )
            
            for i, chapter in enumerate(chapters):
                progress = 50 + int((i / total_chapters) * 45)
                task_manager.update_progress(
                    self.task_id, TaskStatus.AUDIO_SYNTHESIZING, progress,
                    f"处理第 {i+1}/{total_chapters} 章...",
                    current_step=chapter["title"],
                    completed_steps=i
                )
                
                # 生成文稿
                script = await self._generate_script(chapter)
                
                # 保存文稿
                script_path = self.scripts_dir / f"chapter_{chapter['number']:02d}.json"
                with open(script_path, "w", encoding="utf-8") as f:
                    json.dump(script, f, ensure_ascii=False, indent=2)
                
                # 合成音频
                audio_path = self.audio_dir / f"chapter_{chapter['number']:02d}.mp3"
                duration = await self._synthesize_audio(
                    script["dialogues"], 
                    str(audio_path)
                )
                
                # 记录章节完成
                chapter_info = ChapterInfo(
                    number=chapter["number"],
                    title=chapter["title"],
                    duration=duration,
                    audio_url=f"/api/audio/{self.task_id}/{chapter['number']:02d}",
                    script_url=f"/api/script/{self.task_id}/{chapter['number']:02d}"
                )
                task_manager.complete_chapter(self.task_id, chapter_info)
            
            # 完成
            task_manager.update_progress(
                self.task_id, TaskStatus.COMPLETED, 100, "处理完成！"
            )
            
            return True
            
        except Exception as e:
            task_manager.update_progress(
                self.task_id, TaskStatus.FAILED, 0, f"处理失败: {str(e)}"
            )
            return False
    
    async def _pdf_to_images(self, pdf_path: Path, dpi: int = 150) -> List[str]:
        """PDF 转图片"""
        doc = fitz.open(str(pdf_path))
        image_paths = []
        
        for i, page in enumerate(doc):
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            img_path = self.images_dir / f"page_{i+1:04d}.png"
            pix.save(str(img_path))
            image_paths.append(str(img_path))
        
        doc.close()
        return image_paths
    
    async def _ocr_image(self, img_path: str) -> str:
        """OCR 单张图片"""
        with open(img_path, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode()
        
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": "请识别这张图片中的所有中文文字，保持原文格式。"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
            ]
        }]
        
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.qwen_client.chat.completions.create(
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
            r'^第[一二三四五六七八九十\d]+[部章]',
            r'^[0-9]+\s*$',
            r'^[一二三四五六七八九十]+[、.．]',
        ]
        
        current_chapter = None
        current_content = []
        chapter_num = 0
        
        for line in lines:
            line = line.strip()
            if not line or line == "---PAGE---":
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
        
        if current_chapter and current_content:
            current_chapter["content"] = "\n".join(current_content)
            chapters.append(current_chapter)
        
        return chapters if chapters else [{"number": 1, "title": "正文", "content": text[:10000]}]
    
    async def _generate_script(self, chapter: Dict) -> Dict:
        """生成播客文稿"""
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
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.qwen_client.chat.completions.create(
                    model="qwen3.5-plus",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=3000
                )
            )
            
            result = response.choices[0].message.content
            
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"文稿生成失败: {e}")
        
        return {
            "chapter_number": chapter["number"],
            "chapter_title": chapter["title"],
            "dialogues": [
                {"speaker": "小北", "content": f"大家好，今天我们来看第{chapter['number']}章。"},
                {"speaker": "阿南", "content": f"这章的标题是「{chapter['title']}」"}
            ]
        }
    
    async def _synthesize_audio(self, dialogues: List[Dict], output_path: str) -> float:
        """合成音频"""
        temp_files = []
        
        for i, d in enumerate(dialogues):
            speaker = d["speaker"]
            content = d["content"]
            
            voice = "Cherry" if speaker == "小北" else "Zhichu"
            temp_path = str(self.audio_dir / f"temp_{i}.wav")
            
            try:
                url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
                headers = {
                    "Authorization": f"Bearer {self.qwen_tts_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "qwen3-tts-instruct-flash",
                    "input": {
                        "text": content,
                        "voice": voice,
                        "language_type": "Chinese"
                    }
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=headers, json=payload) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            audio_url = result.get("output", {}).get("audio", {}).get("url")
                            if audio_url:
                                async with session.get(audio_url) as audio_resp:
                                    if audio_resp.status == 200:
                                        audio_data = await audio_resp.read()
                                        with open(temp_path, "wb") as f:
                                            f.write(audio_data)
                                        temp_files.append(temp_path)
                
                await asyncio.sleep(0.2)
                
            except Exception as e:
                print(f"音频合成失败: {e}")
        
        if not temp_files:
            return 0
        
        # 合并
        await self._merge_audio(temp_files, output_path)
        
        # 清理
        for f in temp_files:
            Path(f).unlink(missing_ok=True)
        
        # 获取时长
        return self._get_duration(output_path)
    
    async def _merge_audio(self, audio_files: List[str], output_path: str):
        """合并音频"""
        list_file = self.audio_dir / "list.txt"
        with open(list_file, "w") as f:
            for af in audio_files:
                f.write(f"file '{Path(af).absolute()}'\n")
        
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_file), "-c", "copy", output_path
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        
        list_file.unlink(missing_ok=True)
    
    def _get_duration(self, audio_path: str) -> float:
        """获取音频时长"""
        import subprocess
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", 
                 "format=duration", "-of", "csv=p=0", audio_path],
                capture_output=True, text=True
            )
            return float(result.stdout.strip())
        except:
            return 0