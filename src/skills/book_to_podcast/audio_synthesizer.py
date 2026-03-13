"""
音频合成模块
使用 edge-tts 合成播客音频
"""

import os
import json
import asyncio
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from pydantic import BaseModel
from dataclasses import dataclass


class AudioConfig(BaseModel):
    """音频配置"""
    # edge-tts 配置
    edge_voice_male: str = "zh-CN-YunxiNeural"
    edge_voice_female: str = "zh-CN-XiaoxiaoNeural"
    
    # 输出配置
    output_dir: str = "data/output/audio"


@dataclass
class AudioOutput:
    """音频输出"""
    chapter_number: int
    audio_path: str
    duration_seconds: float
    success: bool


class AudioSynthesizer:
    """音频合成器 - 使用 edge-tts"""
    
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
        """合成单章音频"""
        if not output_name:
            output_name = f"chapter_{chapter_number:02d}"
        
        output_path = str(self.output_dir / f"{output_name}.mp3")
        
        print(f"🎙️ 合成第 {chapter_number} 章音频...")
        
        success = await self._synthesize_with_edge(dialogues, output_path)
        
        if success:
            duration = self._get_duration(output_path)
            print(f"✅ 第 {chapter_number} 章完成: {duration:.1f}秒")
            return AudioOutput(
                chapter_number=chapter_number,
                audio_path=output_path,
                duration_seconds=duration,
                success=True
            )
        else:
            print(f"❌ 第 {chapter_number} 章合成失败")
            return AudioOutput(
                chapter_number=chapter_number,
                audio_path="",
                duration_seconds=0,
                success=False
            )
    
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
            
            voice = self.config.edge_voice_female if speaker == "小北" else self.config.edge_voice_male
            temp_path = str(self.output_dir / f"edge_temp_{i}.mp3")
            
            cmd = ["edge-tts", "--voice", voice, "--text", content, "--write-media", temp_path]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            
            if Path(temp_path).exists() and Path(temp_path).stat().st_size > 0:
                temp_files.append(temp_path)
        
        if not temp_files:
            return False
        
        # 合并音频
        await self._merge_audio(temp_files, output_path)
        
        # 清理临时文件
        for f in temp_files:
            Path(f).unlink(missing_ok=True)
        
        return Path(output_path).exists() and Path(output_path).stat().st_size > 0
    
    async def _merge_audio(self, audio_files: List[str], output_path: str):
        """使用 ffmpeg 合并音频"""
        list_file = self.output_dir / "audio_list.txt"
        with open(list_file, "w") as f:
            for af in audio_files:
                abs_path = str(Path(af).absolute())
                f.write(f"file '{abs_path}'\n")
        
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
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries",
                 "format=duration", "-of", "csv=p=0", audio_path],
                capture_output=True, text=True
            )
            return float(result.stdout.strip())
        except:
            return 0.0
    
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
    
    async def synthesize_all_chapters(
        self,
        scripts: List[Dict]
    ) -> List[AudioOutput]:
        """合成所有章节音频"""
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


def synthesize_from_scripts(
    scripts_dir: str,
    output_dir: str = "data/output/audio"
) -> List[AudioOutput]:
    """从文稿目录合成所有音频"""
    scripts_path = Path(scripts_dir)
    scripts = []
    
    # 加载所有文稿
    for json_file in sorted(scripts_path.glob("chapter_*.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            script = json.load(f)
            scripts.append(script)
    
    # 配置
    config = AudioConfig(output_dir=output_dir)
    
    # 合成
    synthesizer = AudioSynthesizer(config)
    return asyncio.run(synthesizer.synthesize_all_chapters(scripts))