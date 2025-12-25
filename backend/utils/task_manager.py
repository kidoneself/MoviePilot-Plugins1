"""
任务管理器
用于管理异步任务状态、进度和二维码
"""
import uuid
import time
from typing import Dict, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class TaskStep:
    """任务步骤"""
    step: str
    status: str  # loading/success/error/warning
    time: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    task_type: str  # create_kind/add_cards/setup_shipping
    status: str  # running/completed/failed
    progress: List[TaskStep] = field(default_factory=list)
    qrcode: Optional[str] = None  # 二维码base64
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self):
        data = asdict(self)
        # 重命名字段以匹配前端期待
        data['steps'] = data.pop('progress')  # progress -> steps
        data['qrcode_base64'] = data.pop('qrcode')  # qrcode -> qrcode_base64
        return data


class TaskManager:
    """任务管理器"""
    
    def __init__(self):
        self.tasks: Dict[str, TaskInfo] = {}
        self._cleanup_interval = 3600  # 1小时后清理完成的任务
    
    def create_task(self, task_type: str) -> str:
        """创建新任务"""
        task_id = str(uuid.uuid4())
        task_info = TaskInfo(
            task_id=task_id,
            task_type=task_type,
            status='running'
        )
        self.tasks[task_id] = task_info
        return task_id
    
    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        return self.tasks.get(task_id)
    
    def add_step(self, task_id: str, step: str, status: str):
        """添加任务步骤"""
        task = self.tasks.get(task_id)
        if task:
            task.progress.append(TaskStep(step=step, status=status))
            task.updated_at = datetime.now().isoformat()
    
    def set_qrcode(self, task_id: str, qrcode_base64: str):
        """设置二维码"""
        task = self.tasks.get(task_id)
        if task:
            task.qrcode = qrcode_base64
            task.updated_at = datetime.now().isoformat()
    
    def complete_task(self, task_id: str, success: bool, result: Optional[dict] = None, error: Optional[str] = None):
        """完成任务"""
        task = self.tasks.get(task_id)
        if task:
            task.status = 'completed' if success else 'failed'
            task.result = result
            task.error = error
            task.updated_at = datetime.now().isoformat()
    
    def cleanup_old_tasks(self):
        """清理旧任务"""
        now = time.time()
        to_remove = []
        for task_id, task in self.tasks.items():
            if task.status in ['completed', 'failed']:
                task_time = datetime.fromisoformat(task.updated_at).timestamp()
                if now - task_time > self._cleanup_interval:
                    to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.tasks[task_id]


# 全局任务管理器实例
_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """获取任务管理器实例"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager

