"""
线程安全的评分进度追踪器
用于并发评分场景下的状态管理
带TTL自动过期清理 + 数据库持久化
"""
import threading
import time
from datetime import datetime
from typing import Dict, Optional, Any
from core.logger import get_logger

logger = get_logger("scoring_tracker")

# TTL: 24小时后自动清理完成的任务进度
_TASK_TTL_SECONDS = 24 * 3600


class ScoringTracker:
    """线程安全的评分进度追踪器（单例），内存+数据库双写"""

    def __init__(self):
        self._lock = threading.Lock()
        self._data: Dict[str, Dict] = {}  # {task_id: {"modules": {...}, "started_at": ..., "last_access": timestamp}}

    def _cleanup_expired(self):
        """清理超过TTL的记录（在锁内调用）"""
        now = time.time()
        expired = [tid for tid, data in self._data.items()
                   if now - data.get("last_access", 0) > _TASK_TTL_SECONDS]
        for tid in expired:
            del self._data[tid]
        if expired:
            logger.info(f"TTL清理: {len(expired)}条过期记录")

    def _persist(self, task_id: str, status: str = None, module_name: str = None,
                 module_status: str = None, error: str = None):
        """持久化到数据库（不抛异常，不阻塞主流程）"""
        try:
            from core.progress_store import progress_store
            if module_name:
                progress_store.update_module_detail(
                    "scoring", task_id, module_name, module_status, error)
            else:
                detail = None
                if task_id in self._data:
                    detail = {"modules": self._data[task_id].get("modules", {})}
                progress_store.update("scoring", task_id, status or "scoring", detail, error)
        except Exception as e:
            logger.error(f"持久化失败: {e}")

    def init_task(self, task_id: str):
        """初始化任务进度（幂等）"""
        with self._lock:
            self._cleanup_expired()
            if task_id not in self._data:
                self._data[task_id] = {
                    "modules": {},
                    "started_at": datetime.now().isoformat(),
                    "last_access": time.time()
                }
            else:
                self._data[task_id]["last_access"] = time.time()
        self._persist(task_id, status="scoring")

    def set_module_status(self, task_id: str, module_name: str, status: str, error: str = None):
        """设置模块评分状态"""
        with self._lock:
            if task_id not in self._data:
                self._data[task_id] = {
                    "modules": {},
                    "started_at": datetime.now().isoformat(),
                    "last_access": time.time()
                }
            self._data[task_id]["last_access"] = time.time()
            entry = {"status": status}
            if error:
                entry["error"] = error
            self._data[task_id]["modules"][module_name] = entry
        self._persist(task_id, module_name=module_name, module_status=status, error=error)

    def get_module_status(self, task_id: str, module_name: str) -> Optional[Dict]:
        """获取单个模块的评分状态"""
        with self._lock:
            task_data = self._data.get(task_id)
            if not task_data:
                return None
            task_data["last_access"] = time.time()
            return task_data["modules"].get(module_name)

    def get_task_status(self, task_id: str) -> Dict:
        """获取任务的完整评分状态（优先内存，fallback数据库）"""
        with self._lock:
            task_data = self._data.get(task_id)
            if task_data:
                task_data["last_access"] = time.time()
                return task_data

        # 内存没有 → 尝试从数据库恢复
        try:
            from core.progress_store import progress_store
            db_data = progress_store.get("scoring", task_id)
            if db_data:
                detail = db_data.get("detail", {})
                task_data = {
                    "modules": detail.get("modules", {}),
                    "started_at": "",
                    "last_access": time.time()
                }
                with self._lock:
                    self._data[task_id] = task_data
                return task_data
        except Exception:
            pass

        return {"modules": {}}

    def remove_task(self, task_id: str):
        """清理任务进度数据"""
        with self._lock:
            self._data.pop(task_id, None)
        try:
            from core.progress_store import progress_store
            progress_store.delete("scoring", task_id)
        except Exception:
            pass


# 全局单例
scoring_tracker = ScoringTracker()
