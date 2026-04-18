"""
统一的任务进度持久化层
后台任务（评分/报告/分析）的进度双写到内存 + 数据库
服务器重启后可从数据库恢复进行中的任务状态
"""
import json
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict

from database import SessionLocal
from models.models import TaskProgress
from core.logger import get_logger

logger = get_logger("progress_store")


class ProgressStore:
    """进度持久化管理器（线程安全，单例使用）"""

    def __init__(self):
        self._lock = threading.Lock()

    # ---- 内部辅助 ----
    @staticmethod
    def _make_key(progress_type: str, ref_id: str) -> str:
        return f"{progress_type}:{ref_id}"

    def _upsert(self, key: str, progress_type: str, ref_id: str,
                status: str = None, detail: dict = None, error: str = None):
        """写入一条进度记录（INSERT or UPDATE）— status=None 时保留原值"""
        db = SessionLocal()
        try:
            row = db.query(TaskProgress).filter(
                TaskProgress.progress_key == key
            ).first()
            if row:
                if status is not None:
                    row.status = status
                if error is not None:
                    row.error = error
                row.updated_at = datetime.utcnow()
                if detail is not None:
                    row.detail_json = json.dumps(detail, ensure_ascii=False)
            else:
                row = TaskProgress(
                    progress_key=key,
                    progress_type=progress_type,
                    ref_id=ref_id,
                    status=status or "pending",
                    detail_json=json.dumps(detail, ensure_ascii=False) if detail else None,
                    error=error,
                )
                db.add(row)
            db.commit()
        except Exception as e:
            logger.error(f"写入失败 {key}: {e}")
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            db.close()

    # ---- 通用 API ----
    def update(self, progress_type: str, ref_id: str,
               status: str, detail: dict = None, error: str = None):
        """更新进度（内存由各模块自行管理，此处只管数据库持久化）"""
        key = self._make_key(progress_type, ref_id)
        with self._lock:
            self._upsert(key, progress_type, ref_id, status, detail, error)

    def update_module_detail(self, progress_type: str, ref_id: str,
                             module_name: str, module_status: str, error: str = None):
        """便捷方法：更新评分模块级进度"""
        key = self._make_key(progress_type, ref_id)
        with self._lock:
            db = SessionLocal()
            try:
                row = db.query(TaskProgress).filter(
                    TaskProgress.progress_key == key
                ).first()
                if row and row.detail_json:
                    detail = json.loads(row.detail_json)
                else:
                    detail = {"modules": {}}

                modules = detail.setdefault("modules", {})
                entry = {"status": module_status}
                if error:
                    entry["error"] = error
                modules[module_name] = detail["modules"][module_name] = entry

                # 确定顶层 status
                top_status = row.status if row else None
                if top_status in (None, "pending"):
                    top_status = progress_type  # "scoring"

                self._upsert(key, progress_type, ref_id, top_status, detail, error)
            except Exception as e:
                logger.error(f"update_module_detail 失败: {e}")
            finally:
                db.close()

    def get(self, progress_type: str, ref_id: str) -> Optional[Dict]:
        """读取进度记录"""
        key = self._make_key(progress_type, ref_id)
        db = SessionLocal()
        try:
            row = db.query(TaskProgress).filter(
                TaskProgress.progress_key == key
            ).first()
            if not row:
                return None
            result = {
                "status": row.status,
                "progress_type": row.progress_type,
                "ref_id": row.ref_id,
                "error": row.error,
            }
            if row.detail_json:
                result["detail"] = json.loads(row.detail_json)
            return result
        finally:
            db.close()

    def delete(self, progress_type: str, ref_id: str):
        """删除进度记录（任务彻底完成后清理）"""
        key = self._make_key(progress_type, ref_id)
        db = SessionLocal()
        try:
            db.query(TaskProgress).filter(
                TaskProgress.progress_key == key
            ).delete()
            db.commit()
        except Exception as e:
            logger.error(f"删除失败 {key}: {e}")
        finally:
            db.close()

    def recover_in_progress(self, progress_type: str = None) -> list:
        """
        启动时恢复未完成的任务
        返回: [{"progress_type": ..., "ref_id": ..., "status": ..., "detail": ...}, ...]
        """
        db = SessionLocal()
        try:
            query = db.query(TaskProgress).filter(
                TaskProgress.status.in_(["scoring", "generating", "running", "pending"])
            )
            if progress_type:
                query = query.filter(TaskProgress.progress_type == progress_type)

            rows = query.all()
            results = []
            for row in rows:
                item = {
                    "progress_type": row.progress_type,
                    "ref_id": row.ref_id,
                    "status": row.status,
                    "detail": json.loads(row.detail_json) if row.detail_json else {},
                }
                results.append(item)
            return results
        finally:
            db.close()

    def cleanup_completed(self, max_age_hours: int = 24):
        """清理已完成的旧进度记录"""
        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
            db.query(TaskProgress).filter(
                TaskProgress.status.in_(["completed", "failed"]),
                TaskProgress.updated_at < cutoff,
            ).delete(synchronize_session=False)
            db.commit()
        except Exception as e:
            logger.error(f"清理失败: {e}")
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            db.close()


# 全局单例
progress_store = ProgressStore()
