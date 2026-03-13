# Book to Podcast Skill

> 将图书转换为双人对话式播客音频的完整流程

## 功能

将 PDF 图书转换为播客音频，包含三个核心模块：

1. **PDF → Skill** - 使用 skill-seekers 提取结构化知识
2. **Skill → 播客文稿** - 使用 Qwen3.5-plus 生成双人对话
3. **文稿 → 音频** - 使用 Qwen TTS（主）+ edge-tts（保底）

## 安装

```bash
# 安装依赖
pip install -r requirements.txt

# 安装 skill-seekers（可选，用于 PDF 转 Skill）
pip install skill-seekers

# 安装 edge-tts（保底 TTS）
pip install edge-tts

# 安装 ffmpeg（音频合并）
# Ubuntu: sudo apt install ffmpeg
# Mac: brew install ffmpeg
```

## 快速开始

```python
from src.skills.book_to_podcast import BookToPodcastPipeline, PipelineConfig

# 配置
config = PipelineConfig(
    qwen_api_key="sk-xxx",           # Qwen3.5-plus API Key
    qwen_tts_api_key="sk-xxx",       # Qwen TTS API Key
    output_base_dir="data"
)

# 创建 Pipeline
pipeline = BookToPodcastPipeline(config)

# 执行完整流程
result = pipeline.run("book.pdf")

# 输出结果
print(f"章节: {result['skill']['chapters']}")
print(f"文稿: {result['scripts']['count']} 个")
print(f"音频: {result['audios']['success']}/{result['audios']['count']} 章")
print(f"总时长: {result['audios']['total_duration']/60:.1f} 分钟")
```

## 模块说明

### 1. PDF 转 Skill (pdf_to_skill.py)

从 PDF 提取结构化知识：

- 主方案：使用 skill-seekers 库
- 保底方案：PyMuPDF + Qwen OCR

```python
from src.skills.book_to_podcast import PDFSkillExtractor, PDFSkillConfig

config = PDFSkillConfig(
    qwen_api_key="sk-xxx",
    output_dir="data/skills"
)

extractor = PDFSkillExtractor(config)
skill = extractor.extract("book.pdf", "书名")

print(f"章节: {len(skill.chapters)}")
print(f"主题: {skill.themes}")
print(f"关键观点: {skill.key_points}")
```

### 2. 播客文稿生成 (podcast_writer.py)

使用 Qwen3.5-plus 生成双人对话：

- 主持人 A（小北）：活泼好奇，善于提问
- 主持人 B（阿南）：沉稳博学，善于总结

```python
from src.skills.book_to_podcast import PodcastScriptGenerator, PodcastConfig

config = PodcastConfig(
    qwen_api_key="sk-xxx",
    host_a_name="小北",
    host_b_name="阿南",
    podcast_name="枕边书"
)

generator = PodcastScriptGenerator(config)

# 生成单章
script = generator.generate_chapter_script(
    book_title="无语问上帝",
    author="菲利普·杨西",
    chapter_number=1,
    chapter_title="要命的错误",
    chapter_content="..."
)

# 生成全部
scripts = generator.generate_all_scripts(
    book_title="无语问上帝",
    author="菲利普·杨西",
    chapters=[{"number": 1, "title": "...", "content": "..."}]
)
```

### 3. 音频合成 (audio_synthesizer.py)

使用 Qwen TTS（主）+ edge-tts（保底）合成音频：

- Qwen TTS：支持指令控制情感、语调
- edge-tts：免费，机械感较强

```python
from src.skills.book_to_podcast import AudioSynthesizer, AudioConfig

config = AudioConfig(
    qwen_api_key="sk-xxx",
    primary_engine="qwen",  # 或 "edge"
    fallback_enabled=True
)

synthesizer = AudioSynthesizer(config)

# 合成单章
audio = synthesizer.synthesize_chapter_sync(
    chapter_number=1,
    dialogues=[
        {"speaker": "小北", "content": "大家好！"},
        {"speaker": "阿南", "content": "欢迎收听。"}
    ]
)

# 合成全部
audios = synthesizer.synthesize_all_sync(scripts)
```

## Prompt 模板

播客文稿生成的 Prompt 可以在 `podcast_writer.py` 中找到，支持反复打磨优化：

- `SYSTEM_PROMPT` - 系统提示词
- `CHAPTER_PROMPT_TEMPLATE` - 章节转换模板

可调整参数：
- 主持人风格描述
- 对话风格（幽默/严谨/轻松/故事）
- 每章最大对话数

## 输出结构

```
data/
├── skills/
│   ├── 书名_skill.json    # Skill JSON
│   └── 书名_skill.md      # Skill Markdown
├── output/
│   ├── scripts/
│   │   ├── chapter_01.json
│   │   ├── chapter_01.txt
│   │   ├── chapter_02.json
│   │   └── ...
│   └── audio/
│       ├── chapter_01.mp3
│       ├── chapter_02.mp3
│       └── ...
```

## API Keys

需要以下 API Keys：

| Key | 用途 | 获取方式 |
|-----|------|---------|
| Qwen API Key | OCR + 文稿生成 | [百炼平台](https://bailian.console.aliyun.com/) |
| Qwen TTS API Key | 语音合成 | [百炼平台](https://bailian.console.aliyun.com/) |

## 版本历史

- v1.0 - 初始版本
  - PDF 转 Skill（skill-seekers / PyMuPDF + Qwen）
  - 播客文稿生成（Qwen3.5-plus）
  - 音频合成（Qwen TTS + edge-tts 保底）

## 参考

- [Skill Seekers](https://github.com/yusufkaraaslan/Skill_Seekers) - PDF 转 Skill 参考
- [Qwen TTS](https://help.aliyun.com/zh/model-studio/qwen-tts) - 阿里云 TTS 文档