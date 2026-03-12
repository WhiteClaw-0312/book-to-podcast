# 图书转播客 (Book to Podcast)

将图书内容转换为双人对话式播客音频的 AI 工具。

## 功能特性

- 📖 **图书解析**: 支持 PDF/EPUB 格式，智能提取文本内容
- 🧠 **知识库构建**: 自动提取章节、人物关系、故事背景
- 📝 **播客文稿生成**: 双人对话风格，幽默风趣，内容严谨
- 🎙️ **语音合成**: 开源 TTS，支持多说话人对话

## 技术栈

- Python 3.10+
- PyMuPDF / pdfplumber - 图书解析
- LangChain + ChromaDB - 知识库
- GLM-5 / Qwen - 文稿生成
- Qwen3-TTS / SoulX-Podcast - 语音合成

## 项目结构

```
book-to-podcast/
├── src/
│   ├── parser/        # 图书解析模块
│   ├── knowledge/     # 知识库构建模块
│   ├── script/        # 播客文稿生成模块
│   └── tts/           # 语音合成模块
├── data/
│   ├── books/         # 原始图书
│   ├── knowledge/     # 知识库数据
│   └── output/        # 输出文件
├── tests/
└── docs/
```

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python main.py --book data/books/book.pdf --output data/output/podcast.mp3
```

## 开发者

HandFoot Company - 白 (首席程序员)

## License

MIT