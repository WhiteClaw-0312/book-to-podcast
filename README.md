# 图书转播客 (Book to Podcast)

将图书内容转换为双人对话式播客音频的 AI 工具。

## 功能特性

- 📖 **图书转 Skill**: 使用 pdf2skills 一键转换 PDF/EPUB 为可执行 AI Skill
- 📝 **播客文稿生成**: 双人对话风格，幽默风趣，内容严谨
- 🎙️ **语音合成**: edge-tts 开源 TTS，支持多说话人对话

## 技术栈

- **图书转 Skill**: [pdf2skills](https://pdf2skills.memect.cn/) - PDF/EPUB → 可执行 AI Skill
- **文稿生成**: Qwen3.5-plus (百炼 Coding Plan API)
- **语音合成**: edge-tts (免费，支持中文多说话人)

## 项目结构

```
book-to-podcast/
├── src/
│   ├── parser/        # 图书解析模块（备选方案）
│   ├── knowledge/     # 知识库构建模块（备选方案）
│   ├── script/        # 播客文稿生成模块
│   └── tts/           # 语音合成模块
├── data/
│   ├── books/         # 原始图书
│   ├── skills/        # pdf2skills 生成的 Skill
│   └── output/        # 输出文件
├── tests/
└── docs/
```

## 工作流程

```
PDF/EPUB → pdf2skills → Skill (含知识库) → 播客文稿 → TTS → 音频播客
```

## 快速开始

### 1. 使用 pdf2skills 转换图书

访问 https://pdf2skills.memect.cn/ 上传 PDF/EPUB 文件，获取 skills.zip。

### 2. 生成播客文稿

```bash
pip install -r requirements.txt
python src/main.py --skill data/skills/无语问上帝 --output data/output/
```

## 开发者

HandFoot Company - 白 (首席程序员)

## License

MIT