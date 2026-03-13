#!/usr/bin/env python
"""
处理《无语问上帝》全书
"""
import sys
sys.path.insert(0, '/home/admin/.openclaw/workspace/book-to-podcast')

from src.skills.book_to_podcast import BookToPodcastPipeline, PipelineConfig

# 配置
config = PipelineConfig(
    qwen_api_key="sk-sp-24c19ee00acc4bae93d0983c74fa2854",  # 百炼 Coding Plan
    qwen_tts_api_key="sk-62a401c7f96448c4981f5f8aa937f7eb",  # Qwen TTS
    output_base_dir="data",
    primary_tts_engine="qwen",
    enable_tts_fallback=True
)

# 创建 Pipeline
pipeline = BookToPodcastPipeline(config)

# 执行
result = pipeline.run(
    pdf_path="data/books/无语问上帝.pdf",
    skill_name="无语问上帝"
)

print("\n" + "="*60)
print("最终结果:")
print(f"成功: {result['success']}")
print(f"章节: {result['skill']['chapters']}")
print(f"文稿: {result['scripts']['count']}")
print(f"音频: {result['audios']['success']}/{result['audios']['count']}")
print(f"总时长: {result['audios']['total_duration']/60:.1f} 分钟")