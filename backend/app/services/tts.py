"""TTS 服务 - 完全免费的 edge-tts"""
import asyncio
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
import edge_tts


class TTSService:
    """TTS 服务 - 使用 edge-tts（完全免费）"""
    
    # 音色配置
    VOICES = {
        "小北": "zh-CN-XiaoxiaoNeural",      # 活泼女声
        "阿南": "zh-CN-YunxiNeural",         # 沉稳男声
        # 备选音色
        "小北_活泼": "zh-CN-XiaoyiNeural",
        "阿南_深沉": "zh-CN-YunjianNeural",
    }
    
    async def synthesize(
        self,
        speaker: str,
        text: str,
        output_path: str
    ) -> float:
        """
        合成单段语音
        返回音频时长（秒）
        """
        voice = self.VOICES.get(speaker, "zh-CN-XiaoxiaoNeural")
        
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            
            # 获取时长
            duration = self._get_duration(output_path)
            return duration
            
        except Exception as e:
            print(f"TTS 合成失败: {e}")
            return 0
    
    async def synthesize_chapter(
        self,
        dialogues: List[Dict],
        output_path: str,
        progress_callback=None
    ) -> float:
        """
        合成整章音频
        返回总时长（秒）
        """
        output_dir = Path(output_path).parent
        temp_dir = output_dir / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        temp_files = []
        total = len(dialogues)
        
        for i, dialogue in enumerate(dialogues):
            speaker = dialogue.get("speaker", "小北")
            content = dialogue.get("content", "")
            
            if not content.strip():
                continue
            
            temp_path = str(temp_dir / f"temp_{i:04d}.mp3")
            
            duration = await self.synthesize(speaker, content, temp_path)
            
            if duration > 0:
                temp_files.append(temp_path)
            
            # 进度回调
            if progress_callback:
                await progress_callback(i + 1, total)
        
        # 合并音频
        if temp_files:
            await self._merge_audio(temp_files, output_path)
            total_duration = self._get_duration(output_path)
            
            # 清理临时文件
            for f in temp_files:
                Path(f).unlink(missing_ok=True)
            
            # 清理临时目录
            try:
                temp_dir.rmdir()
            except:
                pass
            
            return total_duration
        
        return 0
    
    async def _merge_audio(self, files: List[str], output: str):
        """合并音频文件"""
        list_file = Path(output).parent / "merge_list.txt"
        
        with open(list_file, "w") as f:
            for audio_file in files:
                f.write(f"file '{Path(audio_file).absolute()}'\n")
        
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_file), "-c", "copy", output
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
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
        except Exception:
            return 0