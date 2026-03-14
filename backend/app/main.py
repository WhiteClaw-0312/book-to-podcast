"""主入口"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path

from .config import settings
from .database import init_db
from .api import books_router, billing_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 启动时
    init_db()
    print(f"✅ 数据库初始化完成: {settings.DB_PATH}")
    yield
    # 关闭时
    pass


app = FastAPI(
    title="枕边书 API",
    description="图书转播客 API - 按次计费",
    version="3.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境改成具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件
app.mount("/audio", StaticFiles(directory=settings.PODCASTS_DIR), name="audio")

# 路由
app.include_router(books_router)
app.include_router(billing_router)


@app.get("/", response_class=HTMLResponse)
async def index():
    """首页"""
    return """
    <html>
        <head><title>枕边书 API</title></head>
        <body style="font-family: system-ui; padding: 40px; background: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px;">
                <h1 style="color: #2e7d32;">📚 枕边书 API</h1>
                <p>图书转播客 API - 按次计费</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <h3>API 文档</h3>
                <ul>
                    <li><a href="/docs">Swagger UI</a></li>
                    <li><a href="/redoc">ReDoc</a></li>
                </ul>
                <h3>快速开始</h3>
                <ol>
                    <li>创建 API Key: <code>POST /api/keys</code></li>
                    <li>上传书籍: <code>POST /api/books</code></li>
                    <li>生成播客: <code>POST /api/books/{id}/generate</code></li>
                    <li>下载音频: <code>GET /api/books/{id}/chapters/{num}/audio</code></li>
                </ol>
            </div>
        </body>
    </html>
    """


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "version": "3.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )