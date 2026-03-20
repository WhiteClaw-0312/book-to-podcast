"""
数据库迁移脚本 v5.0
- 新增 chapter_skills 表
- 更新 prompt_templates 表
"""
import sys
sys.path.insert(0, '/home/admin/.openclaw/workspace/book-to-podcast/backend')

from sqlalchemy import text
from app.database import engine, Base
from app.models import ChapterSkill, PromptTemplate
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """执行迁移"""
    logger.info("开始数据库迁移 v5.0...")
    
    with engine.connect() as conn:
        # 1. 创建 chapter_skills 表
        logger.info("创建 chapter_skills 表...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS chapter_skills (
                id VARCHAR(16) PRIMARY KEY,
                chapter_id VARCHAR(16) UNIQUE NOT NULL,
                
                summary TEXT,
                key_points TEXT,
                themes TEXT,
                examples TEXT,
                insights TEXT,
                important_details TEXT,
                full_skill_md TEXT,
                
                content_length INTEGER DEFAULT 0,
                skill_length INTEGER DEFAULT 0,
                processing_time REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
            )
        """))
        
        # 2. 更新 prompt_templates 表（添加新字段）
        logger.info("更新 prompt_templates 表...")
        
        # 检查并添加新列
        new_columns = [
            ("style", "VARCHAR(20) DEFAULT 'casual'"),
            ("speaker_count", "INTEGER DEFAULT 2"),
            ("speakers", "TEXT"),
            ("dialogue_count", "INTEGER DEFAULT 65"),
            ("interaction_level", "VARCHAR(20) DEFAULT 'balanced'"),
            ("content_depth", "VARCHAR(20) DEFAULT 'moderate'"),
            ("emotion_style", "VARCHAR(20) DEFAULT 'natural'"),
            ("pace", "VARCHAR(20) DEFAULT 'moderate'"),
            ("enable_intro", "BOOLEAN DEFAULT 1"),
            ("enable_summary", "BOOLEAN DEFAULT 1"),
            ("keep_quotes", "BOOLEAN DEFAULT 0"),
            ("highlight_quotes", "BOOLEAN DEFAULT 0"),
            ("enable_qa", "BOOLEAN DEFAULT 0"),
        ]
        
        for col_name, col_type in new_columns:
            try:
                conn.execute(text(f"ALTER TABLE prompt_templates ADD COLUMN {col_name} {col_type}"))
                logger.info(f"  添加列: {col_name}")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    logger.info(f"  列已存在: {col_name}")
                else:
                    logger.error(f"  添加列失败: {col_name}, {e}")
        
        # 3. 更新 chapters 表
        logger.info("更新 chapters 表...")
        try:
            conn.execute(text("ALTER TABLE chapters ADD COLUMN word_count INTEGER DEFAULT 0"))
            logger.info("  添加列: word_count")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                logger.info("  列已存在: word_count")
            else:
                logger.error(f"  添加列失败: word_count, {e}")
        
        # 更新 status 注释
        logger.info("  更新章节状态支持 'skilled'")
        
        conn.commit()
        
        # 4. 创建默认 Prompt 配置
        logger.info("创建默认 Prompt 配置...")
        try:
            conn.execute(text("""
                INSERT INTO prompt_templates (id, name, description, style, speaker_count, speakers, dialogue_count, is_system, is_default)
                VALUES ('sys_default', '默认配置', '系统默认播客配置', 'casual', 2, 
                    '[{"name":"小北","gender":"female"},{"name":"阿南","gender":"male"}]', 
                    65, 1, 1)
            """))
            conn.commit()
            logger.info("  创建默认配置成功")
        except Exception as e:
            if "unique constraint" in str(e).lower() or "primary key" in str(e).lower():
                logger.info("  默认配置已存在")
            else:
                logger.error(f"  创建默认配置失败: {e}")
        
        logger.info("数据库迁移完成！")
        
        # 显示表结构
        result = conn.execute(text("PRAGMA table_info(chapter_skills)"))
        logger.info("\nchapter_skills 表结构:")
        for row in result:
            logger.info(f"  {row}")
        
        result = conn.execute(text("PRAGMA table_info(prompt_templates)"))
        logger.info("\nprompt_templates 表结构:")
        for row in result:
            logger.info(f"  {row}")


if __name__ == "__main__":
    migrate()