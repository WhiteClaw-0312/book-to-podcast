"""
并发处理的图书转播客 Pipeline
文稿生成与音频合成并行执行（使用 edge-tts）
"""

import os
import json
import asyncio
import openai
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

# ==================== 配置 ====================

QWEN_API_KEY = "sk-sp-24c19ee00acc4bae93d0983c74fa2854"

OUTPUT_DIR = Path("data")
SCRIPTS_DIR = OUTPUT_DIR / "output" / "scripts"
AUDIO_DIR = OUTPUT_DIR / "output" / "audio"


# ==================== 数据结构 ====================

@dataclass
class Chapter:
    """章节"""
    number: int
    title: str
    content: str


@dataclass
class ProcessResult:
    """处理结果"""
    chapter_number: int
    script_path: str
    audio_path: str
    duration: float
    success: bool


# ==================== 文稿生成器 ====================

class ScriptGenerator:
    """播客文稿生成器"""
    
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=QWEN_API_KEY,
            base_url="https://coding.dashscope.aliyuncs.com/v1"
        )
        SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    
    async def generate(self, chapter: Chapter, book_title: str, author: str) -> Dict:
        """生成单章文稿"""
        print(f"📝 [文稿] 开始生成第 {chapter.number} 章...", flush=True)
        
        prompt = f"""将以下图书章节转换为双人对话式播客文案。

书名: {book_title}
作者: {author}
章节: 第 {chapter.number} 章 - {chapter.title}

内容:
{chapter.content[:6000]}

要求:
1. 主持人: 小北（活泼好奇）和阿南（沉稳博学）
2. 格式: JSON，包含 dialogues 数组
3. 每句 30-50 字，总共约 50 句对话
4. 开场介绍主题，结尾总结要点

输出格式:
{{"chapter_number": {chapter.number}, "chapter_title": "{chapter.title}", "dialogues": [{{"speaker": "小北", "content": "..."}}, ...], "duration_estimate": 300}}

只输出 JSON:"""

        try:
            # 在线程池中执行同步 API 调用
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model="qwen3.5-plus",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=4000
                )
            )
            
            result = response.choices[0].message.content
            
            # 解析 JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                script = json.loads(json_match.group())
            else:
                raise ValueError("无法解析 JSON")
            
            # 保存
            script_path = SCRIPTS_DIR / f"chapter_{chapter.number:02d}.json"
            with open(script_path, "w", encoding="utf-8") as f:
                json.dump(script, f, ensure_ascii=False, indent=2)
            
            # 保存 TXT
            txt_path = SCRIPTS_DIR / f"chapter_{chapter.number:02d}.txt"
            with open(txt_path, "w", encoding="utf-8") as f:
                for d in script.get("dialogues", []):
                    f.write(f"[{d['speaker']}]: {d['content']}\n\n")
            
            print(f"✅ [文稿] 第 {chapter.number} 章完成: {len(script.get('dialogues', []))} 句", flush=True)
            
            return {
                "success": True,
                "script": script,
                "path": str(script_path)
            }
            
        except Exception as e:
            print(f"❌ [文稿] 第 {chapter.number} 章失败: {e}", flush=True)
            return {"success": False, "error": str(e)}


# ==================== 音频合成器 ====================

class AudioSynthesizer:
    """音频合成器（使用 edge-tts）"""
    
    def __init__(self):
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    
    async def synthesize(self, chapter_number: int, dialogues: List[Dict]) -> Dict:
        """合成单章音频"""
        print(f"🎙️ [音频] 开始合成第 {chapter_number} 章...", flush=True)
        
        output_path = str(AUDIO_DIR / f"chapter_{chapter_number:02d}.mp3")
        
        success = await self._synthesize_with_edge(dialogues, output_path)
        
        if success:
            duration = self._get_duration(output_path)
            print(f"✅ [音频] 第 {chapter_number} 章完成: {duration:.1f}秒", flush=True)
            return {
                "success": True,
                "path": output_path,
                "duration": duration
            }
        else:
            print(f"❌ [音频] 第 {chapter_number} 章失败", flush=True)
            return {"success": False}
    
    async def _synthesize_with_edge(self, dialogues: List[Dict], output_path: str) -> bool:
        """使用 edge-tts 合成"""
        temp_files = []
        
        for i, d in enumerate(dialogues):
            speaker = d["speaker"]
            content = d["content"]
            
            voice = "zh-CN-XiaoxiaoNeural" if speaker == "小北" else "zh-CN-YunxiNeural"
            temp_path = str(AUDIO_DIR / f"edge_temp_{i}.mp3")
            
            cmd = ["edge-tts", "--voice", voice, "--text", content, "--write-media", temp_path]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            
            if Path(temp_path).exists() and Path(temp_path).stat().st_size > 0:
                temp_files.append(temp_path)
        
        if not temp_files:
            return False
        
        await self._merge_audio(temp_files, output_path)
        
        for f in temp_files:
            Path(f).unlink(missing_ok=True)
        
        return Path(output_path).exists() and Path(output_path).stat().st_size > 0
    
    async def _merge_audio(self, audio_files: List[str], output_path: str):
        """合并音频"""
        list_file = AUDIO_DIR / "audio_list.txt"
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
            return 0.0


# ==================== 并发 Pipeline ====================

class ConcurrentPipeline:
    """
    并发处理 Pipeline
    - 文稿生成完成后立即开始音频合成
    - 多个章节可并行处理
    """
    
    def __init__(self, max_concurrent: int = 3):
        self.script_gen = ScriptGenerator()
        self.audio_gen = AudioSynthesizer()
        self.max_concurrent = max_concurrent
        
        self.results: List[ProcessResult] = []
        self.completed = 0
        self.total = 0
    
    async def process_chapter(self, chapter: Chapter, book_title: str, author: str) -> ProcessResult:
        """
        处理单个章节（文稿 → 音频）
        文稿生成完成后立即开始音频合成
        """
        # Step 1: 生成文稿
        script_result = await self.script_gen.generate(chapter, book_title, author)
        
        if not script_result["success"]:
            return ProcessResult(
                chapter_number=chapter.number,
                script_path="",
                audio_path="",
                duration=0,
                success=False
            )
        
        # Step 2: 立即合成音频（文稿生成完成后）
        dialogues = script_result["script"]["dialogues"]
        audio_result = await self.audio_gen.synthesize(chapter.number, dialogues)
        
        self.completed += 1
        print(f"📊 进度: {self.completed}/{self.total}", flush=True)
        
        return ProcessResult(
            chapter_number=chapter.number,
            script_path=script_result["path"],
            audio_path=audio_result.get("path", ""),
            duration=audio_result.get("duration", 0),
            success=audio_result["success"]
        )
    
    async def run(self, chapters: List[Chapter], book_title: str, author: str) -> List[ProcessResult]:
        """
        并发处理所有章节
        限制最大并发数，避免 API 过载
        """
        self.total = len(chapters)
        self.completed = 0
        
        print(f"🚀 开始并发处理 {self.total} 个章节（最大并发: {self.max_concurrent}）", flush=True)
        
        # 创建信号量限制并发
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_with_semaphore(chapter):
            async with semaphore:
                return await self.process_chapter(chapter, book_title, author)
        
        # 并发执行所有任务
        tasks = [process_with_semaphore(ch) for ch in chapters]
        results = await asyncio.gather(*tasks)
        
        self.results = list(results)
        
        # 统计
        success_count = sum(1 for r in results if r.success)
        total_duration = sum(r.duration for r in results if r.success)
        
        print(f"\n{'='*60}", flush=True)
        print(f"✅ 处理完成!", flush=True)
        print(f"📊 成功: {success_count}/{self.total} 章", flush=True)
        print(f"⏱️ 总时长: {total_duration/60:.1f} 分钟", flush=True)
        print(f"{'='*60}", flush=True)
        
        return self.results


# ==================== 主函数 ====================

async def process_book(skill_json_path: str):
    """
    处理整本书
    
    Args:
        skill_json_path: Skill JSON 文件路径
    """
    # 加载 Skill
    with open(skill_json_path, "r", encoding="utf-8") as f:
        skill = json.load(f)
    
    book_title = skill["metadata"]["title"]
    author = skill["metadata"].get("author", "未知")
    
    # 转换为 Chapter 对象
    chapters = [
        Chapter(
            number=ch["number"],
            title=ch["title"],
            content=ch["content"]
        )
        for ch in skill["chapters"]
    ]
    
    print(f"📚 书名: {book_title}", flush=True)
    print(f"✍️ 作者: {author}", flush=True)
    print(f"📖 章节数: {len(chapters)}", flush=True)
    
    # 创建 Pipeline 并执行
    pipeline = ConcurrentPipeline(max_concurrent=2)  # 最多同时处理 2 个章节
    results = await pipeline.run(chapters, book_title, author)
    
    return results


def run_concurrent_pipeline(skill_json_path: str):
    """同步入口"""
    return asyncio.run(process_book(skill_json_path))


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        skill_path = sys.argv[1]
    else:
        skill_path = "data/skills/无语问上帝_skill_full.json"
    
    run_concurrent_pipeline(skill_path)