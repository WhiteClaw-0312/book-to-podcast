"""
音频合成模块
支持 Qwen TTS（主方案）+ edge-tts（保底）
"""

import os
import json
import asyncio
import aiohttp
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel
from dataclasses import dataclass


class AudioConfig(BaseModel):
    """音频配置"""
    # Qwen TTS 配置
    qwen_api_key: str = ""
    qwen_model: str = "qwen3-tts-instruct-flash"
    qwen_base_url: str = "https://dashscope.aliyuncs.com/api/v1"
    
    # 音色配置
    voice_male: str = "Zhichu"      # 男声音色（阿南）
    voice_female: str = "Cherry"    # 女声音色（小北）
    
    # 指令控制（qwen3-tts-instruct-flash 支持）
    instructions_male: str = "语气沉稳温和，适合播客讲解和知识分享，语速适中。"
    instructions_female: str = "语气活泼自然，适合播客主持和轻松对话，语速稍快。"
    
    # edge-tts 保底配置
    edge_voice_male: str = "zh-CN-YunxiNeural"
    edge_voice_female: str = "zh-CN-XiaoxiaoNeural"
    
    # 输出配置
    output_dir: str = "data/output/audio"
    
    # 引擎选择
    primary_engine: str = "qwen"  # qwen 或 edge
    fallback_enabled: bool = True  # 是否启用保底


@dataclass
class AudioOutput:
    """音频输出"""
    chapter_number: int
    audio_path: str
    duration_seconds: float
    engine_used: str
    success: bool


class AudioSynthesizer:
    """
    音频合成器
    
    - 主方案: Qwen TTS（支持指令控制，情感自然）
    - 保底方案: edge-tts（免费，机械感较强）
    """
    
    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def synthesize_chapter(
        self,
        chapter_number: int,
        dialogues: List[Dict[str, str]],
        output_name: str = None
    ) -> AudioOutput:
        """
        合成单章音频
        
        Args:
            chapter_number: 章节编号
            dialogues: 对话列表 [{"speaker": "小北", "content": "..."}]
            output_name: 输出文件名
        
        Returns:
            AudioOutput 对象
        """
        if not output_name:
            output_name = f"chapter_{chapter_number:02d}"
        
        output_path = str(self.output_dir / f"{output_name}.mp3")
        
        print(f"🎙️ 合成第 {chapter_number} 章音频...")
        
        # 尝试主引擎
        engine = self.config.primary_engine
        success = False
        
        if engine == "qwen":
            success = await self._synthesize_with_qwen(dialogues, output_path)
            if not success and self.config.fallback_enabled:
                print(f"⚠️ Qwen TTS 失败，切换到 edge-tts...")
                engine = "edge"
        
        if engine == "edge" or not success:
            success = await self._synthesize_with_edge(dialogues, output_path)
            engine = "edge"
        
        if success:
            # 获取时长
            duration = self._get_audio_duration(output_path)
            print(f"✅ 第 {chapter_number} 章完成: {duration:.1f}秒")
            
            return AudioOutput(
                chapter_number=chapter_number,
                audio_path=output_path,
                duration_seconds=duration,
                engine_used=engine,
                success=True
            )
        else:
            print(f"❌ 第 {chapter_number} 章合成失败")
            return AudioOutput(
                chapter_number=chapter_number,
                audio_path="",
                duration_seconds=0,
                engine_used="",
                success=False
            )
    
    async def synthesize_all_chapters(
        self,
        scripts: List[Dict]
    ) -> List[AudioOutput]:
        """
        合成所有章节音频
        
        Args:
            scripts: 文稿列表，每个包含 chapter_number 和 dialogues
        
        Returns:
            AudioOutput 列表
        """
        outputs = []
        total = len(scripts)
        
        for i, script in enumerate(scripts):
            print(f"\n🎵 处理 {i+1}/{total}...")
            
            output = await self.synthesize_chapter(
                chapter_number=script["chapter_number"],
                dialogues=script["dialogues"]
            )
            
            outputs.append(output)
        
        # 统计
        success_count = sum(1 for o in outputs if o.success)
        total_duration = sum(o.duration_seconds for o in outputs if o.success)
        
        print(f"\n🎉 全部完成: {success_count}/{total} 章, 总时长 {total_duration/60:.1f} 分钟")
        
        return outputs
    
    # ==================== Qwen TTS ====================
    
    async def _synthesize_with_qwen(
        self,
        dialogues: List[Dict[str, str]],
        output_path: str
    ) -> bool:
        """使用 Qwen TTS 合成"""
        temp_files = []
        
        for i, dialogue in enumerate(dialogues):
            speaker = dialogue["speaker"]
            content = dialogue["content"]
            
            temp_path = str(self.output_dir / f"qwen_temp_{i}.wav")
            
            # 获取音色和指令
            voice = self.config.voice_female if speaker == "小北" else self.config.voice_male
            instructions = self.config.instructions_female if speaker == "小北" else self.config.instructions_male
            
            success = await self._qwen_synthesize_single(
                text=content,
                output_path=temp_path,
                voice=voice,
                instructions=instructions
            )
            
            if success and Path(temp_path).exists():
                temp_files.append(temp_path)
            else:
                print(f"⚠️ 第 {i+1} 句合成失败")
        
        if not temp_files:
            return False
        
        # 合并音频
        await self._merge_audio(temp_files, output_path)
        
        # 清理临时文件
        for f in temp_files:
            Path(f).unlink(missing_ok=True)
        
        return Path(output_path).exists()
    
    async def _qwen_synthesize_single(
        self,
        text: str,
        output_path: str,
        voice: str,
        instructions: str
    ) -> bool:
        """Qwen TTS 合成单句"""
        url = f"{self.config.qwen_base_url}/services/aigc/multimodal-generation/generation"
        
        headers = {
            "Authorization": f"Bearer {self.config.qwen_api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.config.qwen_model,
            "input": {
                "text": text,
                "voice": voice,
                "language_type": "Chinese",
                "instructions": instructions,
                "optimize_instructions": True
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        return False
                    
                    result = await resp.json()
                    audio_url = result.get("output", {}).get("audio", {}).get("url")
                    
                    if not audio_url:
                        return False
                    
                    # 下载音频
                    async with session.get(audio_url) as audio_resp:
                        if audio_resp.status == 200:
                            audio_data = await audio_resp.read()
                            with open(output_path, "wb") as f:
                                f.write(audio_data)
                            return True
            
        except Exception as e:
            print(f"Qwen TTS 错误: {e}")
            return False
    
    # ==================== edge-tts ====================
    
    async def _synthesize_with_edge(
        self,
        dialogues: List[Dict[str, str]],
        output_path: str
    ) -> bool:
        """使用 edge-tts 合成"""
        temp_files = []
        
        for i, dialogue in enumerate(dialogues):
            speaker = dialogue["speaker"]
            content = dialogue["content"]
            
            temp_path = str(self.output_dir / f"edge_temp_{i}.mp3")
            
            # 获取音色
            voice = self.config.edge_voice_female if speaker == "小北" else self.config.edge_voice_male
            
            success = await self._edge_synthesize_single(content, temp_path, voice)
            
            if success and Path(temp_path).exists():
                temp_files.append(temp_path)
        
        if not temp_files:
            return False
        
        # 合并
        await self._merge_audio(temp_files, output_path)
        
        # 清理
        for f in temp_files:
            Path(f).unlink(missing_ok=True)
        
        return Path(output_path).exists()
    
    async def _edge_synthesize_single(
        self,
        text: str,
        output_path: str,
        voice: str
    ) -> bool:
        """edge-tts 合成单句"""
        try:
            cmd = [
                "edge-tts",
                "--voice", voice,
                "--text", text,
                "--write-media", output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            print(f"edge-tts 错误: {e}")
            return False
    
    # ==================== 工具方法 ====================
    
    async def _merge_audio(self, audio_files: List[str], output_path: str):
        """使用 ffmpeg 合并音频"""
        # 创建文件列表
        list_file = self.output_dir / "audio_list.txt"
        with open(list_file, "w") as f:
            for af in audio_files:
                abs_path = str(Path(af).absolute())
                f.write(f"file '{abs_path}'\n")
        
        # 合并
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await process.communicate()
        
        # 清理
        list_file.unlink(missing_ok=True)
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长"""
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", 
                 "format=duration", "-of", "csv=p=0", audio_path],
                capture_output=True,
                text=True
            )
            return float(result.stdout.strip())
        except:
            return 0.0
    
    # ==================== 同步接口 ====================
    
    def synthesize_chapter_sync(
        self,
        chapter_number: int,
        dialogues: List[Dict[str, str]],
        output_name: str = None
    ) -> AudioOutput:
        """同步版本"""
        return asyncio.run(self.synthesize_chapter(
            chapter_number, dialogues, output_name
        ))
    
    def synthesize_all_sync(
        self,
        scripts: List[Dict]
    ) -> List[AudioOutput]:
        """同步版本"""
        return asyncio.run(self.synthesize_all_chapters(scripts))


# ==================== 便捷函数 ====================

def synthesize_from_scripts(
    scripts_dir: str,
    qwen_api_key: str = "",
    output_dir: str = "data/output/audio"
) -> List[AudioOutput]:
    """
    从文稿目录合成所有音频
    
    Args:
        scripts_dir: 文稿目录
        qwen_api_key: Qwen TTS API Key
        output_dir: 输出目录
    
    Returns:
        AudioOutput 列表
    """
    scripts_path = Path(scripts_dir)
    scripts = []
    
    # 加载所有文稿
    for json_file in sorted(scripts_path.glob("chapter_*.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            script = json.load(f)
            scripts.append(script)
    
    # 配置
    config = AudioConfig(
        qwen_api_key=qwen_api_key,
        output_dir=output_dir
    )
    
    # 合成
    synthesizer = AudioSynthesizer(config)
    return synthesizer.synthesize_all_sync(scripts)