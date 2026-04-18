"""
短记忆服务
在单个检查会话中保持上下文
TTL: 24小时自动过期
"""
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
import json
import threading
from config import settings

# 线程安全内存存储
_memory_store: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()

# 默认TTL: 24小时
DEFAULT_TTL_HOURS = 24


class ShortMemory:
    """
    短记忆管理器
    用于在单个检查任务会话中保持上下文
    """

    @classmethod
    def set(
        cls,
        session_id: str,
        key: str,
        value: Any,
        expire_hours: int = DEFAULT_TTL_HOURS,
    ) -> None:
        """
        存储短记忆

        Args:
            session_id: 会话ID (通常为 task_id)
            key: 记忆键
            value: 记忆值
            expire_hours: 过期时间（小时），默认24小时
        """
        expire_at = datetime.now() + timedelta(hours=expire_hours)

        with _lock:
            if session_id not in _memory_store:
                _memory_store[session_id] = {}

            _memory_store[session_id][key] = {
                "value": value,
                "expire_at": expire_at,
                "created_at": datetime.now(),
            }

    @classmethod
    def get(cls, session_id: str, key: str) -> Optional[Any]:
        """
        获取短记忆

        Args:
            session_id: 会话ID
            key: 记忆键

        Returns:
            记忆值，如果不存在或已过期返回None
        """
        with _lock:
            if session_id not in _memory_store:
                return None

            if key not in _memory_store[session_id]:
                return None

            entry = _memory_store[session_id][key]
            if datetime.now() > entry["expire_at"]:
                # 已过期，删除
                del _memory_store[session_id][key]
                return None

            return entry["value"]

    @classmethod
    def get_session_context(cls, session_id: str) -> Dict[str, Any]:
        """
        获取会话完整上下文（用于传递给LLM）

        Args:
            session_id: 会话ID

        Returns:
            所有未过期的记忆字典
        """
        with _lock:
            if session_id not in _memory_store:
                return {}

            context = {}
            expired_keys = []

            for key, entry in _memory_store[session_id].items():
                if datetime.now() <= entry["expire_at"]:
                    context[key] = entry["value"]
                else:
                    expired_keys.append(key)

            # 清理过期记忆
            for key in expired_keys:
                del _memory_store[session_id][key]

            return context

    @classmethod
    def set_session_context(cls, session_id: str, context: Dict[str, Any]) -> None:
        """
        批量设置会话上下文

        Args:
            session_id: 会话ID
            context: 上下文字典
        """
        for key, value in context.items():
            cls.set(session_id, key, value)

    @classmethod
    def append(cls, session_id: str, key: str, value: Any) -> None:
        """
        追加记忆（用于列表类型）

        Args:
            session_id: 会话ID
            key: 记忆键
            value: 要追加的值
        """
        current = cls.get(session_id, key)
        if current is None:
            current = []

        if not isinstance(current, list):
            current = [current]

        current.append(value)
        cls.set(session_id, key, current)

    @classmethod
    def get_scoring_context(cls, task_id: str, module_name: str) -> Dict[str, Any]:
        """
        获取评分专用的上下文

        Args:
            task_id: 任务ID
            module_name: 当前模块名称

        Returns:
            包含以下内容的字典:
            - completed_modules: 已完成的模块列表
            - module_scores: 各模块评分摘要
            - recurring_issues: 反复出现的问题（跨模块）
        """
        context = cls.get_session_context(task_id)

        # 格式化用于Prompt的历史记忆
        scoring_context = {
            "completed_modules": context.get("completed_modules", []),
            "module_scores": context.get("module_scores", {}),
            "recurring_issues": context.get("recurring_issues", []),
        }

        return scoring_context

    @classmethod
    def update_scoring_result(
        cls,
        task_id: str,
        module_name: str,
        score: float,
        issues: List[Dict],
    ) -> None:
        """
        更新评分结果到短记忆

        Args:
            task_id: 任务ID
            module_name: 模块名称
            score: 模块百分制得分
            issues: 该模块的问题列表
        """
        # 更新已完成的模块列表
        completed = cls.get(task_id, "completed_modules") or []
        if module_name not in completed:
            completed.append(module_name)
            cls.set(task_id, "completed_modules", completed)

        # 更新模块得分
        module_scores = cls.get(task_id, "module_scores") or {}
        module_scores[module_name] = score
        cls.set(task_id, "module_scores", module_scores)

        # 记录问题（用于识别反复出现的问题）
        if issues:
            all_issues = cls.get(task_id, "all_issues") or []
            for issue in issues:
                all_issues.append({
                    "module": module_name,
                    "description": issue.get("description", ""),
                    "severity": issue.get("severity", "一般"),
                })
            cls.set(task_id, "all_issues", all_issues)

            # 识别反复出现的问题（同一描述在多个模块出现）
            recurring = cls._find_recurring_issues(all_issues)
            if recurring:
                cls.set(task_id, "recurring_issues", recurring)

    @classmethod
    def _find_recurring_issues(cls, issues: List[Dict]) -> List[Dict]:
        """识别反复出现的问题"""
        issue_count: Dict[str, int] = {}
        issue_modules: Dict[str, List[str]] = {}

        for issue in issues:
            desc = issue.get("description", "")[:50]  # 取前50字符作为key
            if not desc:
                continue

            if desc not in issue_count:
                issue_count[desc] = 0
                issue_modules[desc] = []

            issue_count[desc] += 1
            if issue.get("module") not in issue_modules[desc]:
                issue_modules[desc].append(issue.get("module"))

        # 返回出现2次以上的问题
        recurring = []
        for desc, count in issue_count.items():
            if count >= 2:
                recurring.append({
                    "description": desc,
                    "count": count,
                    "modules": issue_modules.get(desc, []),
                })

        return recurring

    @classmethod
    def clear_session(cls, session_id: str) -> None:
        """清除会话记忆"""
        with _lock:
            if session_id in _memory_store:
                del _memory_store[session_id]

    @classmethod
    def get_all_sessions(cls) -> List[str]:
        """获取所有活跃会话ID"""
        with _lock:
            return list(_memory_store.keys())

    @classmethod
    def cleanup_expired(cls) -> int:
        """清理所有过期记忆，返回清理数量"""
        cleaned = 0
        with _lock:
            for session_id in list(_memory_store.keys()):
                expired_keys = []
                for key, entry in _memory_store[session_id].items():
                    if datetime.now() > entry["expire_at"]:
                        expired_keys.append(key)

                for key in expired_keys:
                    del _memory_store[session_id][key]
                    cleaned += 1

                # 如果会话为空，删除会话
                if not _memory_store[session_id]:
                    del _memory_store[session_id]

        return cleaned

    @classmethod
    def build_memory_prompt(cls, task_id: str, module_name: str) -> str:
        """
        构建记忆上下文文本，用于插入到LLM Prompt中

        Args:
            task_id: 任务ID
            module_name: 当前模块名称

        Returns:
            格式化的记忆上下文字符串
        """
        context = cls.get_scoring_context(task_id, module_name)

        if not context.get("completed_modules"):
            return ""  # 首次评分，无历史记忆

        lines = ["\n\n【本次任务历史上下文】（供参考）"]

        # 已完成模块
        if context["completed_modules"]:
            lines.append(f"- 已评分模块: {', '.join(context['completed_modules'])}")

        # 模块得分
        if context["module_scores"]:
            scores_text = ", ".join([
                f"{m}: {s:.1f}分" for m, s in context["module_scores"].items()
            ])
            lines.append(f"- 各模块得分: {scores_text}")

        # 反复问题
        if context["recurring_issues"]:
            lines.append("- 反复出现的问题:")
            for issue in context["recurring_issues"][:3]:  # 最多3条
                lines.append(f"  • {issue['description']}（出现{issue['count']}次，涉及: {', '.join(issue['modules'])})")

        return "\n".join(lines)


def start_cleanup_timer(interval_hours: int = 1):
    """
    启动定期清理过期记忆的定时器

    Args:
        interval_hours: 清理间隔（小时）
    """
    import threading
    import time

    def cleanup_loop():
        while True:
            time.sleep(interval_hours * 3600)
            cleaned = ShortMemory.cleanup_expired()
            if cleaned > 0:
                from core.logger import get_logger
                logger = get_logger("short_memory")
                logger.info(f"清理了 {cleaned} 条过期短记忆")

    thread = threading.Thread(target=cleanup_loop, daemon=True)
    thread.start()
    return thread