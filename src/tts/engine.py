"""语音合成模块"""

from typing import List, Optional
from pathlib import Path
from pydantic import BaseModel
import subprocess
import json


class TTSConfig(BaseModel):
    """TTS 配置"""
    engine: str = "edge-tts"  # edge-tts, sherpa, qwen3-tts
    voice_a: str = "zh-CN-XiaoxiaoNeural"  # 主持人A声音
    voice_b: str = "zh-CN-YunxiNeural"  # 主持人B声音
    rate: str = "+0%"  # 语速
    output_dir: str = "data/output/audio"


class TTSEngine:
    """TTS 引擎基类"""
    
    def synthesize(self, text: str, output_path: str, voice: str) -> bool:
        raise NotImplementedError


class EdgeTTSEngine(TTSEngine):
    """Edge TTS 引擎（免费，无需API）"""
    
    def synthesize(self, text: str, output_path: str, voice: str, rate: str = "+0%") -> bool:
        """使用 edge-tts 合成语音"""
        try:
            cmd = [
                "edge-tts",
                "--voice", voice,
                "--text", text,
                "--write-media", output_path,
                "--rate", rate
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            return result.returncode == 0
        except Exception as e:
            print(f"TTS 错误: {e}")
            return False


class PodcastTTS:
    """播客语音合成器"""
    
    def __init__(self, config: Optional[TTSConfig] = None):
        self.config = config or TTSConfig()
        self.engine = self._get_engine()
    
    def _get_engine(self) -> TTSEngine:
        """获取 TTS 引擎"""
        if self.config.engine == "edge-tts":
            return EdgeTTSEngine()
        # TODO: 支持更多引擎
        return EdgeTTSEngine()
    
    def synthesize_dialogue(
        self, 
        speaker: str, 
        content: str, 
        output_path: str
    ) -> bool:
        """合成单句对话语音"""
        voice = self.config.voice_a if speaker == "小北" else self.config.voice_b
        return self.engine.synthesize(content, output_path, voice, self.config.rate)
    
    def synthesize_chapter(
        self,
        dialogues: List[dict],
        output_path: str
    ) -> bool:
        """合成整章播客音频"""
        import os
        
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成每句音频
        audio_files = []
        for i, dialogue in enumerate(dialogues):
            temp_path = str(output_dir / f"temp_{i}.mp3")
            success = self.synthesize_dialogue(
                dialogue["speaker"],
                dialogue["content"],
                temp_path
            )
            if success:
                audio_files.append(temp_path)
        
        # 合并音频
        if audio_files:
            self._merge_audio(audio_files, output_path)
            # 清理临时文件
            for f in audio_files:
                os.remove(f)
            return True
        
        return False
    
    def _merge_audio(self, audio_files: List[str], output_path: str):
        """合并多个音频文件"""
        # 使用 ffmpeg 合并
        list_file = "/tmp/audio_list.txt"
        with open(list_file, "w") as f:
            for af in audio_files:
                f.write(f"file '{af}'\n")
        
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            output_path
        ]
        subprocess.run(cmd, capture_output=True)


def check_tts_available() -> dict:
    """检查 TTS 工具可用性"""
    result = {
        "edge-tts": False,
        "ffmpeg": False
    }
    
    # 检查 edge-tts
    try:
        subprocess.run(["edge-tts", "--version"], capture_output=True)
        result["edge-tts"] = True
    except FileNotFoundError:
        pass
    
    # 检查 ffmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True)
        result["ffmpeg"] = True
    except FileNotFoundError:
        pass
    
    return result