"""TTS 语音合成模块"""

from .podcast_tts import PodcastTTS, TTSConfig, synthesize_podcast
from .unified_tts import UnifiedTTS, UnifiedTTSConfig

__all__ = [
    "PodcastTTS", "TTSConfig", "synthesize_podcast",
    "UnifiedTTS", "UnifiedTTSConfig"
]