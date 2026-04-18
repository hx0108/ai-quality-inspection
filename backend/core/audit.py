"""
审计日志工具
在关键操作处插入日志记录，不参与业务判断逻辑
"""
import json
from datetime import datetime, timezone as _tz
from database import SessionLocal
from models.models import Base
from sqlalchemy import Column, Integer, String, Text, DateTime

# 定义审计日志模型（与 models.py 分离，自包含）
from sqlalchemy.orm import declarative_base

# 复用已有 Base
from models.models import Base as AppBase
from core.logger import get_logger

logger = get_logger("audit")


class AuditLog(AppBase):
    """审计日志表"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, comment="操作用户ID")
    username = Column(String(100), nullable=True, comment="用户名")
    action = Column(String(50), nullable=False, comment="操作类型: login/scoring_edit/report_delete/user_manage/data_export")
    target_type = Column(String(50), nullable=True, comment="目标类型: task/report/user/analysis")
    target_id = Column(String(100), nullable=True, comment="目标ID")
    detail = Column(Text, nullable=True, comment="操作详情JSON")
    ip_address = Column(String(50), nullable=True, comment="IP地址")
    user_agent = Column(String(500), nullable=True, comment="浏览器UA")
    created_at = Column(DateTime, default=lambda: datetime.now(_tz.utc))


def log_action(
    action: str,
    user_id: int = None,
    username: str = None,
    target_type: str = None,
    target_id: str = None,
    detail: dict = None,
    ip_address: str = None,
    user_agent: str = None
):
    """
    记录审计日志（异步写入，不阻塞主流程）

    用法:
        log_action("login", user_id=user.id, username=user.username, ip_address=request.client.host)
        log_action("scoring_edit", user_id=user.id, target_type="scoring", target_id=scoring_id, detail={"old": 3, "new": 4})
    """
    try:
        db = SessionLocal()
        log = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=json.dumps(detail, ensure_ascii=False) if detail else None,
            ip_address=ip_address,
            user_agent=(user_agent or "")[:500] if user_agent else None,
        )
        db.add(log)
        db.commit()
    except Exception as e:
        # 审计日志写入失败不应影响主流程
        logger.error(f"审计日志写入失败: {e}")
    finally:
        db.close()


# 确保表存在的迁移函数
def ensure_audit_table():
    """确保 audit_logs 表存在"""
    from database import engine
    AuditLog.__table__.create(bind=engine, checkfirst=True)
    logger.info("Audit log table ready")
