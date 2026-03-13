"""
统一 TTS 模块
支持 Qwen TTS（推荐）和 edge-tts（保底）
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from pydantic import BaseModel


class UnifiedTTSConfig(BaseModel):
    """统一 TTS 配置"""
    # 引擎选择
    primary_engine: str = "qwen"      # qwen 或 edge
    fallback_engine: str = "edge"      # 保底引擎
    
    # Qwen TTS 配置
    qwen_api_key: str = ""
    qwen_model: str = "qwen3-tts-instruct-flash"
    
    # edge-tts 配置
    edge_voice_male: str = "zh-CN-YunxiNeural"
    edge_voice_female: str = "zh-CN-XiaoxiaoNeural"
    
    # 输出配置
    output_dir: str = "data/output/audio"


class UnifiedTTS:
    """
    统一 TTS 引擎
    - 主方案: Qwen TTS（支持指令控制，适合播客）
    - 保底方案: edge-tts（免费，机械感较强）
    """
    
    def __init__(self, config: Optional[UnifiedTTSConfig] = None):
        self.config = config or UnifiedTTSConfig()
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 延迟导入引擎
        self._qwen_engine = None
        self._edge_engine = None
    
    @property
    def qwen_engine(self):
        """延迟加载 Qwen TTS 引擎"""
        if self._qwen_engine is None:
            from ..qwen_tts import QwenTTSEngine, QwenTTSConfig
            qwen_config = QwenTTSConfig(
                api_key=self.config.qwen_api_key,
                model=self.config.qwen_model,
                output_dir=str(self.output_dir)
            )
            self._qwen_engine = QwenTTSEngine(qwen_config)
        return self._qwen_engine
    
    @property
    def edge_engine(self):
        """延迟加载 edge-tts 引擎"""
        if self._edge_engine is None:
            from ..podcast_tts import PodcastTTS, TTSConfig
            edge_config = TTSConfig(
                voice_a=self.config.edge_voice_female,
                voice_b=self.config.edge_voice_male,
                output_dir=str(self.output_dir)
            )
            self._edge_engine = PodcastTTS(edge_config)
        return self._edge_engine
    
    async def synthesize_chapter(
        self,
        dialogues: List[Dict[str, str]],
        output_path: str,
        engine: str = "auto"
    ) -> tuple[bool, str]:
        """
        合成整章播客
        
        Args:
            dialogues: 对话列表
            output_path: 输出路径
            engine: 引擎选择 (auto, qwen, edge)
        
        Returns:
            (是否成功, 使用的引擎名称)
        """
        # 决定使用哪个引擎
        if engine == "auto":
            use_engine = self.config.primary_engine
        else:
            use_engine = engine
        
        # 尝试主引擎
        if use_engine == "qwen":
            try:
                success = await self._synthesize_with_qwen(dialogues, output_path)
                if success:
                    return True, "qwen"
            except Exception as e:
                print(f"⚠️ Qwen TTS 失败: {e}")
                print("🔄 切换到 edge-tts...")
                use_engine = self.config.fallback_engine
        
        # 保底引擎
        if use_engine == "edge":
            success = await self._synthesize_with_edge(dialogues, output_path)
            return success, "edge"
        
        return False, ""
    
    async def _synthesize_with_qwen(
        self,
        dialogues: List[Dict[str, str]],
        output_path: str
    ) -> bool:
        """使用 Qwen TTS 合成"""
        return await self.qwen_engine.synthesize_chapter(dialogues, output_path)
    
    async def _synthesize_with_edge(
        self,
        dialogues: List[Dict[str, str]],
        output_path: str
    ) -> bool:
        """使用 edge-tts 合成"""
        return await self.edge_engine.synthesize_chapter(dialogues, output_path)
    
    def synthesize_chapter_sync(
        self,
        dialogues: List[Dict[str, str]],
        output_path: str,
        engine: str = "auto"
    ) -> tuple[bool, str]:
        """同步版本"""
        return asyncio.run(self.synthesize_chapter(dialogues, output_path, engine))


def synthesize_podcast(
    script_path: str,
    output_path: str = None,
    engine: str = "auto",
    qwen_api_key: str = ""
) -> tuple[bool, str]:
    """
    合成播客音频（统一入口）
    
    Args:
        script_path: 文稿 JSON 文件路径
        output_path: 输出音频路径
        engine: 引擎选择 (auto, qwen, edge)
        qwen_api_key: Qwen TTS API Key
    
    Returns:
        (是否成功, 使用的引擎名称)
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
    
    # 配置
    config = UnifiedTTSConfig(qwen_api_key=qwen_api_key)
    
    # 合成
    tts = UnifiedTTS(config)
    return tts.synthesize_chapter_sync(dialogues, output_path, engine)