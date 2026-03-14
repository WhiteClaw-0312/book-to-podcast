"""配置管理"""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API 配置
    QWEN_API_KEY: str = "sk-sp-24c19ee00acc4bae93d0983c74fa2854"
    QWEN_BASE_URL: str = "https://coding.dashscope.aliyuncs.com/v1"
    QWEN_MODEL: str = "qwen3.5-plus"
    
    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # 数据目录
    DATA_DIR: Path = Path(__file__).parent.parent / "data"
    UPLOADS_DIR: Path = DATA_DIR / "uploads"
    PODCASTS_DIR: Path = DATA_DIR / "podcasts"
    CACHE_DIR: Path = DATA_DIR / "cache"
    DB_PATH: Path = DATA_DIR / "books.db"
    
    # 文件配置
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    FILE_EXPIRE_DAYS: int = 7
    
    # TTS 配置
    TTS_ENGINE: str = "edge"  # edge (免费) | qwen (付费)
    
    class Config:
        env_file = ".env"


settings = Settings()

# 确保目录存在
for d in [settings.DATA_DIR, settings.UPLOADS_DIR, settings.PODCASTS_DIR, settings.CACHE_DIR]:
    d.mkdir(parents=True, exist_ok=True)