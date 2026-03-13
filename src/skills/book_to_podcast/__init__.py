"""图书转播客 Skill

完整的图书转播客流程：
1. PDF → Skill（使用 skill-seekers）
2. Skill → 播客文稿（使用 qwen3.5-plus，按章节）
3. 文稿 → 音频（edge-tts）
"""

from .pipeline import BookToPodcastPipeline, PipelineConfig
from .pdf_to_skill import PDFSkillExtractor, PDFSkillConfig
from .podcast_writer import PodcastScriptGenerator, PodcastConfig
from .audio_synthesizer import AudioSynthesizer, AudioConfig
from .concurrent_pipeline import ConcurrentPipeline, process_book, run_concurrent_pipeline

__all__ = [
    "BookToPodcastPipeline", "PipelineConfig",
    "PDFSkillExtractor", "PDFSkillConfig",
    "PodcastScriptGenerator", "PodcastConfig",
    "AudioSynthesizer", "AudioConfig",
    "ConcurrentPipeline", "process_book", "run_concurrent_pipeline"
]