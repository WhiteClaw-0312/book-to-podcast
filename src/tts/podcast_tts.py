"""
TTS 语音合成模块 - 使用 edge-tts
支持多说话人播客
"""

import asyncio
import subprocess
from pathlib import Path
from typing import List, Dict
from pydantic import BaseModel


class TTSConfig(BaseModel):
    """TTS配置"""
    voice_a: str = "zh-CN-XiaoxiaoNeural"  # 小北：活泼女声
    voice_b: str = "zh-CN-YunxiNeural"     # 阿南：沉稳男声
    rate: str = "+0%"
    output_dir: str = "data/output/audio"


class PodcastTTS:
    """播客TTS合成器"""
    
    SPEAKER_VOICES = {
        "小北": "zh-CN-XiaoxiaoNeural",  # 活泼女声
        "阿南": "zh-CN-YunxiNeural",     # 沉稳男声
    }
    
    def __init__(self, config: TTSConfig = None):
        self.config = config or TTSConfig()
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_voice(self, speaker: str) -> str:
        """获取说话人对应的语音"""
        return self.SPEAKER_VOICES.get(speaker, self.config.voice_a)
    
    async def synthesize_text(
        self,
        text: str,
        output_path: str,
        voice: str,
        rate: str = "+0%"
    ) -> bool:
        """
        合成单段文本
        """
        try:
            cmd = [
                "edge-tts",
                "--voice", voice,
                "--text", text,
                "--write-media", output_path,
                "--rate", rate
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            print(f"TTS错误: {e}")
            return False
    
    async def synthesize_dialogue(
        self,
        speaker: str,
        content: str,
        output_path: str
    ) -> bool:
        """合成单句对话"""
        voice = self.get_voice(speaker)
        return await self.synthesize_text(content, output_path, voice, self.config.rate)
    
    async def synthesize_chapter(
        self,
        dialogues: List[Dict[str, str]],
        output_path: str
    ) -> bool:
        """
        合成整章播客
        """
        temp_files = []
        
        # 合成每句
        for i, dialogue in enumerate(dialogues):
            temp_path = str(self.output_dir / f"temp_{i}.mp3")
            
            success = await self.synthesize_dialogue(
                dialogue["speaker"],
                dialogue["content"],
                temp_path
            )
            
            if success:
                temp_files.append(temp_path)
            else:
                print(f"⚠️ 第{i+1}句合成失败")
        
        if not temp_files:
            return False
        
        # 合并音频
        await self._merge_audio(temp_files, output_path)
        
        # 清理临时文件
        for f in temp_files:
            Path(f).unlink(missing_ok=True)
        
        return True
    
    async def _merge_audio(self, audio_files: List[str], output_path: str):
        """合并音频文件"""
        # 创建文件列表（使用绝对路径）
        list_file = self.output_dir / "audio_list.txt"
        with open(list_file, "w") as f:
            for af in audio_files:
                # 转换为绝对路径
                abs_path = str(Path(af).absolute())
                f.write(f"file '{abs_path}'\n")
        
        # 使用ffmpeg合并
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
    
    def synthesize_chapter_sync(
        self,
        dialogues: List[Dict[str, str]],
        output_path: str
    ) -> bool:
        """同步版本"""
        return asyncio.run(self.synthesize_chapter(dialogues, output_path))


def synthesize_podcast(
    script_path: str,
    output_path: str = None
) -> bool:
    """
    从文稿文件合成播客音频
    
    使用示例:
        synthesize_podcast(
            "data/output/scripts/chapter_01.json",
            "data/output/audio/chapter_01.mp3"
        )
    """
    import json
    
    # 加载文稿
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)
    
    # 获取对话列表
    dialogues = [
        {"speaker": d["speaker"], "content": d["content"]}
        for d in script["dialogues"]
    ]
    
    # 设置输出路径
    if not output_path:
        output_path = f"data/output/audio/{Path(script_path).stem}.mp3"
    
    # 合成
    tts = PodcastTTS()
    return tts.synthesize_chapter_sync(dialogues, output_path)