#!/usr/bin/env python3
"""数据库迁移：添加章节管理相关字段"""
import sqlite3
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "data" / "books.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查字段是否已存在
    cursor.execute("PRAGMA table_info(books)")
    columns = [col[1] for col in cursor.fetchall()]
    
    # 添加 raw_text 字段
    if "raw_text" not in columns:
        print("添加 books.raw_text 字段...")
        cursor.execute("ALTER TABLE books ADD COLUMN raw_text TEXT")
    
    # 添加 pages_json 字段
    if "pages_json" not in columns:
        print("添加 books.pages_json 字段...")
        cursor.execute("ALTER TABLE books ADD COLUMN pages_json TEXT")
    
    # 检查 chapters 表
    cursor.execute("PRAGMA table_info(chapters)")
    chapter_columns = [col[1] for col in cursor.fetchall()]
    
    # 添加 page_range 字段
    if "page_range" not in chapter_columns:
        print("添加 chapters.page_range 字段...")
        cursor.execute("ALTER TABLE chapters ADD COLUMN page_range VARCHAR(50)")
    
    conn.commit()
    conn.close()
    print("迁移完成！")

if __name__ == "__main__":
    migrate()