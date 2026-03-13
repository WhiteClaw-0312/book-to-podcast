"""
Qwen TTS 语音合成引擎
支持 qwen3-tts-instruct-flash（推荐播客使用）
支持指令控制：情感、语调、语速、角色性格
"""

import os
import json
import asyncio
import aiohttp
import base64
from pathlib import Path
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel
from dataclasses import dataclass


class QwenTTSConfig(BaseModel):
    """Qwen TTS 配置"""
    api_key: str = ""
    model: str = "qwen3-tts-instruct-flash"  # 推荐播客使用
    base_url: str = "https://dashscope.aliyuncs.com/api/v1"
    
    # 音色配置
    voice_male: str = "Zhichu"      # 男声音色
    voice_female: str = "Cherry"    # 女声音色
    
    # 指令控制（仅 instruct-flash 支持）
    instructions_male: str = "语气沉稳温和，适合播客讲解和知识分享，语速适中。"
    instructions_female: str = "语气活泼自然，适合播客主持和轻松对话，语速稍快。"
    
    # 输出配置
    output_dir: str = "data/output/audio"
    language: str = "Chinese"


@dataclass
class DialogueSegment:
    """对话片段"""
    speaker: str      # 说话人名称
    content: str      # 内容
    emotion: str = "" # 情感指令（可选）


class QwenTTSEngine:
    """
    Qwen TTS 引擎
    - 支持 qwen3-tts-instruct-flash（支持指令控制）
    - 支持流式输出
    - 支持多说话人播客
    """
    
    # 系统预置音色
    AVAILABLE_VOICES = {
        # 女声
        "Cherry": "活泼甜美，适合年轻女性角色",
        "Zhixiang": "温柔知性，适合成熟女性角色",
        "Xiaomei": "可爱俏皮，适合儿童或少女角色",
        # 男声
        "Zhichu": "沉稳大气，适合成熟男性角色",
        "Yunxi": "阳光活力，适合年轻男性角色",
        "Yunjian": "深沉磁性，适合旁白或反派角色",
        # 其他
        "Stella": "优雅英文女声",
        "Dylan": "标准英文男声",
    }
    
    def __init__(self, config: Optional[QwenTTSConfig] = None):
        self.config = config or QwenTTSConfig()
        # 从环境变量或配置获取 API Key
        if not self.config.api_key:
            self.config.api_key = os.getenv("QWEN_TTS_API_KEY", "")
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_voice(self, speaker: str) -> str:
        """获取说话人对应的音色"""
        # 根据说话人名称映射音色
        voice_mapping = {
            "小北": self.config.voice_female,
            "阿南": self.config.voice_male,
            "女": self.config.voice_female,
            "男": self.config.voice_male,
        }
        return voice_mapping.get(speaker, self.config.voice_female)
    
    def get_instructions(self, speaker: str, custom_instruction: str = "") -> str:
        """获取说话人对应的指令"""
        if custom_instruction:
            return custom_instruction
        
        instructions_mapping = {
            "小北": self.config.instructions_female,
            "阿南": self.config.instructions_male,
            "女": self.config.instructions_female,
            "男": self.config.instructions_male,
        }
        return instructions_mapping.get(speaker, self.config.instructions_female)
    
    async def synthesize_single(
        self,
        text: str,
        output_path: str,
        voice: str = "Cherry",
        instructions: str = "",
        language: str = "Chinese"
    ) -> bool:
        """
        合成单段文本
        
        Args:
            text: 要合成的文本
            output_path: 输出文件路径
            voice: 音色名称
            instructions: 指令控制（仅 instruct-flash 支持）
            language: 语言类型
        
        Returns:
            是否成功
        """
        url = f"{self.config.base_url}/services/aigc/multimodal-generation/generation"
        
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.config.model,
            "input": {
                "text": text,
                "voice": voice,
                "language_type": language,
            }
        }
        
        # 如果是 instruct-flash 模型，添加指令控制
        if "instruct" in self.config.model and instructions:
            payload["input"]["instructions"] = instructions
            payload["input"]["optimize_instructions"] = True
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        print(f"❌ TTS API 错误: {resp.status} - {error_text}")
                        return False
                    
                    result = await resp.json()
                    
                    # 获取音频URL
                    audio_url = result.get("output", {}).get("audio", {}).get("url")
                    if not audio_url:
                        print(f"❌ 未获取到音频URL: {result}")
                        return False
                    
                    # 下载音频文件
                    async with session.get(audio_url) as audio_resp:
                        if audio_resp.status == 200:
                            audio_data = await audio_resp.read()
                            with open(output_path, "wb") as f:
                                f.write(audio_data)
                            return True
                        else:
                            print(f"❌ 下载音频失败: {audio_resp.status}")
                            return False
                            
        except Exception as e:
            print(f"❌ TTS合成错误: {e}")
            return False
    
    async def synthesize_dialogue(
        self,
        speaker: str,
        content: str,
        output_path: str,
        custom_instruction: str = ""
    ) -> bool:
        """合成单句对话"""
        voice = self.get_voice(speaker)
        instructions = self.get_instructions(speaker, custom_instruction)
        
        return await self.synthesize_single(
            text=content,
            output_path=output_path,
            voice=voice,
            instructions=instructions,
            language=self.config.language
        )
    
    async def synthesize_chapter(
        self,
        dialogues: List[Dict[str, str]],
        output_path: str,
        progress_callback=None
    ) -> bool:
        """
        合成整章播客
        
        Args:
            dialogues: 对话列表 [{"speaker": "小北", "content": "..."}]
            output_path: 输出文件路径
            progress_callback: 进度回调函数
        
        Returns:
            是否成功
        """
        temp_files = []
        
        # 合成每句对话
        for i, dialogue in enumerate(dialogues):
            temp_path = str(self.output_dir / f"qwen_temp_{i}.wav")
            
            success = await self.synthesize_dialogue(
                speaker=dialogue["speaker"],
                content=dialogue["content"],
                output_path=temp_path,
                custom_instruction=dialogue.get("instruction", "")
            )
            
            if success and Path(temp_path).exists():
                temp_files.append(temp_path)
                if progress_callback:
                    progress_callback(i + 1, len(dialogues))
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
        """使用 ffmpeg 合并音频文件"""
        # 创建文件列表（使用绝对路径）
        list_file = self.output_dir / "audio_list.txt"
        with open(list_file, "w") as f:
            for af in audio_files:
                abs_path = str(Path(af).absolute())
                f.write(f"file '{abs_path}'\n")
        
        # 使用 ffmpeg 合并
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
        output_path: str,
        progress_callback=None
    ) -> bool:
        """同步版本"""
        return asyncio.run(self.synthesize_chapter(dialogues, output_path, progress_callback))


def synthesize_podcast_with_qwen(
    script_path: str,
    output_path: str = None,
    api_key: str = ""
) -> bool:
    """
    使用 Qwen TTS 合成播客音频
    
    Args:
        script_path: 文稿JSON文件路径
        output_path: 输出音频路径
        api_key: Qwen TTS API Key
    
    Returns:
        是否成功
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
        output_path = f"data/output/audio/{Path(script_path).stem}_qwen.mp3"
    
    # 配置
    config = QwenTTSConfig(api_key=api_key)
    
    # 合成
    engine = QwenTTSEngine(config)
    return engine.synthesize_chapter_sync(dialogues, output_path)