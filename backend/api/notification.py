"""
通知 API
消息通知管理
"""
import threading
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.models import User, Notification
from api.deps import get_current_user
from core.logger import get_logger

logger = get_logger("notification")
router = APIRouter(tags=["通知"])


# ============== 数据模型 ==============

class NotificationResponse(BaseModel):
    notification_id: str
    title: str
    content: str
    notify_type: str
    ref_type: Optional[str] = None
    ref_id: Optional[str] = None
    is_read: bool
    created_at: str
    read_at: Optional[str] = None

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    total: int
    unread_count: int
    items: List[NotificationResponse]


class NotificationCreateRequest(BaseModel):
    user_id: int
    username: str
    title: str
    content: str
    notify_type: str
    ref_type: Optional[str] = None
    ref_id: Optional[str] = None


# ============== 通知工具函数 ==============

def _generate_notification_id() -> str:
    """生成通知ID"""
    from models.models import Task
    today = datetime.now().strftime("%Y%m%d")
    import random
    suffix = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    return f"NTF-{today}-{suffix}"


def send_notification(
    user_id: int,
    username: str,
    title: str,
    content: str,
    notify_type: str,
    ref_type: str = None,
    ref_id: str = None,
    async_send: bool = True
):
    """
    发送通知（默认异步，不阻塞主流程）

    notify_type 可选值：
      task_assigned          - 任务分配
      inspection_complete    - 检查完成
      scoring_complete       - 评分完成
      report_ready          - 报告生成完成
      rectification_reminder - 整改提醒
      rectification_approved - 整改通过
      rectification_rejected - 整改驳回
    """
    def _do_send():
        db = SessionLocal()
        try:
            notification = Notification(
                notification_id=_generate_notification_id(),
                user_id=user_id,
                username=username,
                title=title,
                content=content,
                notify_type=notify_type,
                ref_type=ref_type,
                ref_id=ref_id
            )
            db.add(notification)
            db.commit()
            logger.info(f"[通知发送] {username}: {title}")
        except Exception as e:
            logger.error(f"[通知发送失败] {e}")
        finally:
            db.close()

    if async_send:
        threading.Thread(target=_do_send, daemon=True).start()
    else:
        _do_send()


# ============== API 端点 ==============

@router.get("", response_model=NotificationListResponse, summary="获取通知列表")
async def get_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户的通知列表"""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    if unread_only:
        query = query.filter(Notification.is_read == False)

    total = query.count()
    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()

    items = query.order_by(Notification.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()

    return {
        "total": total,
        "unread_count": unread_count,
        "items": [
            {
                "notification_id": n.notification_id,
                "title": n.title,
                "content": n.content,
                "notify_type": n.notify_type,
                "ref_type": n.ref_type,
                "ref_id": n.ref_id,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else "",
                "read_at": n.read_at.isoformat() if n.read_at else None
            }
            for n in items
        ]
    }


@router.get("/unread-count", summary="获取未读数量")
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户未读通知数量"""
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    return {"unread_count": count}


@router.post("/{notification_id}/read", summary="标记已读")
async def mark_as_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """标记单条通知为已读"""
    notification = db.query(Notification).filter(
        Notification.notification_id == notification_id,
        Notification.user_id == current_user.id
    ).first()

    if not notification:
        raise HTTPException(status_code=404, detail="通知不存在")

    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()

    return {"success": True}


@router.post("/read-all", summary="全部已读")
async def mark_all_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """标记全部通知为已读"""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({
        Notification.is_read: True,
        Notification.read_at: datetime.utcnow()
    })
    db.commit()
    return {"success": True}


@router.delete("/{notification_id}", summary="删除通知")
async def delete_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除单条通知"""
    notification = db.query(Notification).filter(
        Notification.notification_id == notification_id,
        Notification.user_id == current_user.id
    ).first()

    if not notification:
        raise HTTPException(status_code=404, detail="通知不存在")

    db.delete(notification)
    db.commit()
    return {"success": True}
