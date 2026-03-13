# 📚 枕边书 - 图书转播客

将 PDF 图书转换为双人对话式播客音频的完整解决方案。

## ✨ 功能特性

- 📄 **PDF 上传**: 支持拖拽上传
- 🔍 **智能 OCR**: 自动识别扫描版 PDF
- 📝 **文稿生成**: AI 生成双人对话播客稿
- 🎧 **音频合成**: 高质量 TTS 语音合成
- 🌐 **Web 界面**: 现代化的前端界面

## 🚀 快速开始

### 方式一：Docker 部署（推荐）

```bash
# 克隆项目
git clone https://github.com/WhiteClaw-0312/book-to-podcast.git
cd book-to-podcast

# 配置环境变量
cp .env.example .env
# 编辑 .env 设置 SECRET_KEY

# 启动服务
docker-compose up -d

# 访问
open http://localhost:8000
```

### 方式二：手动部署

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000

# 前端（另一个终端）
cd frontend
npm install
npm run build
```

## 📁 项目结构

```
book-to-podcast/
├── backend/                # FastAPI 后端
│   ├── main.py            # API 入口
│   ├── api/               # API 路由
│   ├── services/          # 业务逻辑
│   ├── models/            # 数据模型
│   └── utils/             # 工具函数
├── frontend/               # Vue 3 前端
│   ├── src/
│   │   ├── App.vue        # 主组件
│   │   └── components/    # 子组件
│   └── package.json
├── src/skills/             # 核心 Skill 模块
│   └── book_to_podcast/   # 图书转播客 Skill
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🔑 API Key 配置

需要阿里云百炼平台的 API Key：

| Key | 用途 | 获取方式 |
|-----|------|---------|
| Qwen API Key | OCR + 文稿生成 | [百炼平台](https://bailian.console.aliyun.com/) |
| Qwen TTS Key | 语音合成 | [百炼平台](https://bailian.console.aliyun.com/) |

### 配置方式

1. **前端输入**：在网页界面直接输入（推荐）
2. **环境变量**：在 `.env` 文件中配置

## 📡 API 文档

启动后访问 `http://localhost:8000/docs` 查看自动生成的 API 文档。

### 主要接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/upload | 上传 PDF |
| GET | /api/status/{task_id} | 查询处理进度 |
| GET | /api/tasks | 获取任务列表 |
| GET | /api/audio/{task_id}/{chapter} | 获取音频文件 |
| GET | /api/script/{task_id}/{chapter} | 获取文稿内容 |

## 🛠️ 技术栈

**后端**
- FastAPI - 高性能异步框架
- PyMuPDF - PDF 处理
- Qwen3.5-plus - OCR + 文稿生成
- Qwen TTS - 语音合成

**前端**
- Vue 3 - 渐进式框架
- Vite - 构建工具
- Tailwind CSS - 样式框架

## 📦 GitHub Pages 部署

前端会自动部署到 GitHub Pages：
- 地址：`https://whiteclaw-0312.github.io/book-to-podcast/`
- 后端需要自行部署

## 📄 License

MIT License