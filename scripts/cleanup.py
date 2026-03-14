#!/usr/bin/env python3
"""定时清理过期文件"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path


def cleanup_expired_files():
    """删除 7 天前的文件"""
    
    # 数据目录
    data_dir = Path(__file__).parent.parent / "backend" / "data"
    expire_date = datetime.now() - timedelta(days=7)
    
    print(f"🧹 清理 {expire_date.strftime('%Y-%m-%d')} 之前的文件...")
    
    # 清理上传的 PDF
    uploads_dir = data_dir / "uploads"
    if uploads_dir.exists():
        for f in uploads_dir.iterdir():
            if f.is_file():
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < expire_date:
                    f.unlink()
                    print(f"  删除: {f.name}")
    
    # 清理生成的音频
    podcasts_dir = data_dir / "podcasts"
    if podcasts_dir.exists():
        for book_dir in podcasts_dir.iterdir():
            if book_dir.is_dir():
                mtime = datetime.fromtimestamp(book_dir.stat().st_mtime)
                if mtime < expire_date:
                    shutil.rmtree(book_dir)
                    print(f"  删除: {book_dir.name}/")
    
    # 清理缓存
    cache_dir = data_dir / "cache"
    if cache_dir.exists():
        for f in cache_dir.iterdir():
            if f.is_file():
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < expire_date:
                    f.unlink()
                    print(f"  删除: {f.name}")
    
    print("✅ 清理完成")


if __name__ == "__main__":
    cleanup_expired_files()