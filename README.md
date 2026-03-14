# 枕边书 📚

> AI 图书转播客 · 按次计费

## 功能

- 📄 **智能 OCR** - 自动识别扫描版 PDF
- 🎙️ **双人播客** - AI 生成自然对话
- 💰 **按次计费** - 1次 = 1章

## 快速开始

### 后端

```bash
cd backend
pip install -r requirements.txt
python -m app.main
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## API

| 接口 | 说明 |
|------|------|
| `POST /api/books` | 上传书籍 |
| `GET /api/books/{id}` | 获取状态 |
| `POST /api/books/{id}/generate` | 生成播客 |
| `GET /api/keys/{key}/balance` | 查询余额 |

## 部署

```bash
# 初始化数据库
python scripts/manage.py create-key --name "测试" --balance 100

# 启动后端
cd backend && python -m app.main

# 构建前端
cd frontend && npm run build
```

## 许可证

MIT