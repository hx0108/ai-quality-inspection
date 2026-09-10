"""
依赖注入模块
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models.models import User
from config import settings

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """获取当前登录用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        # 优先使用 user_id 查找，兼容旧 token 用 username
        user_id: int = payload.get("user_id")
        username: str = payload.get("sub")
        if user_id is None and username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
    else:
        user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="用户已被禁用")
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户已被禁用")
    return current_user


def check_role(allowed_roles: list):
    """角色检查装饰器"""
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
        return current_user
    return role_checker


def mask_phone(phone: str) -> str:
    """手机号脱敏：138****5678"""
    if not phone or len(phone) < 11:
        return phone or ""
    return phone[:3] + "****" + phone[-4:]


def get_user_project_ids(current_user, db):
    """
    获取用户关联的所有项目ID列表。
    优先从 user_projects 表读取（多项目），回退到 user.project_id（单项目兼容）。
    """
    from models.models import UserProject
    ups = db.query(UserProject).filter(UserProject.user_id == current_user.id).all()
    if ups:
        return [up.project_id for up in ups]
    # 回退：从旧的 project_id 字段读取
    if current_user.project_id:
        return [current_user.project_id]
    return []


def get_user_project_filter(current_user, db=None):
    """
    生成项目级过滤条件。
    - admin / inspector：返回 None（不过滤，看全部）
    - site_supervisor：返回 None（督导可看全部项目）
    - field_supervisor / project_staff：返回其关联的项目ID列表（只看自己项目）
    - 无关联项目的 field_supervisor/project_staff：返回 []（无权访问任何数据）

    返回值：None = 不过滤, list[int] = 允许访问的项目ID列表（空=无权）
    用法：
        filter_ids = get_user_project_filter(user, db)
        if filter_ids is not None:
            query = query.filter(Model.project_id.in_(filter_ids))
    """
    if current_user.role in ("admin", "inspector"):
        return None  # 不过滤
    if current_user.role == "site_supervisor":
        return None  # 督导可看全部项目
    if current_user.role in ("field_supervisor", "project_staff"):
        if db is None:
            if current_user.project_id is None:
                return []
            return [current_user.project_id]
        return get_user_project_ids(current_user, db)
    return []


def apply_task_visibility(query, current_user, db):
    """Apply the same task visibility rules used by the task center.

    Keeping this in one place prevents list, detail and export endpoints from
    drifting into different authorization behavior.
    """
    from models.models import InspectionTask, TaskAssignment

    if current_user.role in ("field_supervisor", "project_staff"):
        project_ids = get_user_project_ids(current_user, db)
        if not project_ids:
            return query.filter(InspectionTask.id == -1)
        return query.filter(InspectionTask.project_id.in_(project_ids))

    if current_user.role == "inspector":
        assigned_task_ids = db.query(TaskAssignment.task_id).filter(
            TaskAssignment.inspector_id == current_user.id
        )
        return query.filter(InspectionTask.task_id.in_(assigned_task_ids))

    if current_user.role in ("admin", "site_supervisor"):
        return query

    return query.filter(InspectionTask.id == -1)
