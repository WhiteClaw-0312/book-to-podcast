"""任务管理器"""
import os
import json
import uuid
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

from models.task import Task, TaskStatus, TaskProgress, ChapterInfo


class TaskManager:
    """任务管理器"""
    
    def __init__(self, data_dir: str = "data/tasks"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.tasks: Dict[str, Task] = {}
        self._load_tasks()
    
    def _load_tasks(self):
        """加载已有任务"""
        for task_file in self.data_dir.glob("*.json"):
            try:
                with open(task_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 转换 status 为枚举
                    if isinstance(data.get("status"), str):
                        data["status"] = TaskStatus(data["status"])
                    task = Task(**data)
                    self.tasks[task.id] = task
            except Exception as e:
                print(f"加载任务失败: {task_file}, {e}")
    
    def _save_task(self, task: Task):
        """保存任务"""
        task_file = self.data_dir / f"{task.id}.json"
        with open(task_file, "w", encoding="utf-8") as f:
            # 转换为可序列化的字典
            data = task.model_dump()
            data["created_at"] = data["created_at"].isoformat() if isinstance(data.get("created_at"), datetime) else data.get("created_at", "")
            data["updated_at"] = data["updated_at"].isoformat() if isinstance(data.get("updated_at"), datetime) else data.get("updated_at", "")
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    
    def create_task(self, filename: str) -> Task:
        """创建新任务"""
        task_id = str(uuid.uuid4())[:8]
        task = Task(
            id=task_id,
            filename=filename,
            book_title=Path(filename).stem,
            status=TaskStatus.PENDING,
            progress=TaskProgress(
                status=TaskStatus.PENDING,
                message="等待处理",
                progress=0
            )
        )
        self.tasks[task_id] = task
        self._save_task(task)
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def update_task(self, task_id: str, **kwargs):
        """更新任务"""
        task = self.tasks.get(task_id)
        if task:
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            task.updated_at = datetime.now()
            self._save_task(task)
    
    def update_progress(
        self, 
        task_id: str, 
        status: TaskStatus,
        progress: int = None,
        message: str = None
    ):
        """更新进度"""
        task = self.tasks.get(task_id)
        if task:
            task.status = status
            task.progress.status = status
            if progress is not None:
                task.progress.progress = progress
            if message:
                task.progress.message = message
            task.updated_at = datetime.now()
            self._save_task(task)
    
    def complete_chapter(self, task_id: str, chapter: ChapterInfo):
        """完成一个章节"""
        task = self.tasks.get(task_id)
        if task:
            task.chapters.append(chapter)
            task.total_duration += chapter.duration
            self._save_task(task)
    
    def list_tasks(self, limit: int = 20) -> list:
        """列出最近的任务"""
        tasks = sorted(
            self.tasks.values(),
            key=lambda t: t.created_at,
            reverse=True
        )
        return tasks[:limit]
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            task_file = self.data_dir / f"{task_id}.json"
            if task_file.exists():
                task_file.unlink()
            return True
        return False


# 全局任务管理器
task_manager = TaskManager()