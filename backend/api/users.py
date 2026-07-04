"""
用户管理 API
"""
import re
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
import bcrypt

from database import get_db
from models.models import User
from api.deps import get_current_user, check_role, mask_phone

router = APIRouter()


# ==================== 请求/响应模型 ====================
class UserCreate(BaseModel):
    username: str
    password: str
    real_name: str
    role: str = "inspector"
    phone: Optional[str] = None
    project_id: Optional[int] = None
    project_ids: Optional[list] = None


class UserUpdate(BaseModel):
    real_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None
    phone: Optional[str] = None
    project_id: Optional[int] = None
    project_ids: Optional[list] = None


class UserResponse(BaseModel):
    id: int
    username: str
    phone: Optional[str] = None
    real_name: str
    role: str
    is_active: bool
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== API 端点 ====================
# force reload marker - remove after debug
@router.get("", summary="获取用户列表")
async def list_users(
    page: int = 1,
    page_size: int = 20,
    role: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role(["admin"]))
):
    """获取用户列表（仅管理员）"""
    from models.models import Project, UserProject
    from sqlalchemy.orm import joinedload
    query = db.query(User).options(joinedload(User.project))
    if role:
        query = query.filter(User.role == role)
    total = query.count()
    users = query.order_by(User.id).offset((page - 1) * page_size).limit(page_size).all()

    # 批量查询所有用户的项目归属
    user_ids = [u.id for u in users]
    user_projects_map = {}
    user_projects_id_map = {}
    if user_ids:
        for uid, pid, pname in db.query(UserProject.user_id, UserProject.project_id, Project.name).join(
            Project, UserProject.project_id == Project.id
        ).filter(UserProject.user_id.in_(user_ids)).all():
            user_projects_map.setdefault(uid, []).append(pname)
            user_projects_id_map.setdefault(uid, []).append(pid)

    return {
        "total": total,
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "phone": mask_phone(u.phone),
                "real_name": u.real_name,
                "role": u.role,
                "is_active": u.is_active,
                "project_id": u.project_id,
                "project_name": u.project.name if u.project else None,
                "project_names": user_projects_map.get(u.id, []),
                "project_ids": user_projects_id_map.get(u.id, []),
                "created_at": u.created_at.isoformat() if u.created_at else None
            }
            for u in users
        ]
    }


@router.post("", summary="创建用户")
async def create_user(
    req: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role(["admin"]))
):
    """创建新用户（仅管理员）"""
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 校验手机号
    if req.phone:
        if not re.match(r'^1[3-9]\d{9}$', req.phone):
            raise HTTPException(status_code=400, detail="手机号格式不正确")
        phone_exists = db.query(User).filter(User.phone == req.phone).first()
        if phone_exists:
            raise HTTPException(status_code=400, detail="该手机号已被注册")

    valid_roles = ["admin", "inspector", "site_supervisor", "field_supervisor", "project_staff"]
    if req.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"无效角色，可选: {valid_roles}")

    password_hash = bcrypt.hashpw(req.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = User(
        username=req.username,
        password_hash=password_hash,
        real_name=req.real_name,
        role=req.role,
        phone=req.phone if req.phone else None,
        project_id=req.project_id,
        must_change_pwd=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 同步写入 user_projects 表
    from models.models import UserProject
    pids = req.project_ids if req.project_ids else ([req.project_id] if req.project_id else [])
    for pid in pids:
        db.add(UserProject(user_id=user.id, project_id=pid))
    if pids:
        user.project_id = pids[0]
    db.commit()

    return {"id": user.id, "username": user.username, "message": "用户创建成功"}


@router.put("/{user_id}", summary="更新用户")
async def update_user(
    user_id: int,
    req: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role(["admin"]))
):
    """更新用户信息（仅管理员）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if req.real_name is not None:
        user.real_name = req.real_name
    if req.role is not None:
        valid_roles = ["admin", "inspector", "site_supervisor", "field_supervisor", "project_staff"]
        if req.role not in valid_roles:
            raise HTTPException(status_code=400, detail="无效角色")
        user.role = req.role
    if req.is_active is not None:
        user.is_active = req.is_active
    if req.password is not None:
        user.password_hash = bcrypt.hashpw(req.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user.must_change_pwd = True
    if req.phone is not None:
        if req.phone:
            if not re.match(r'^1[3-9]\d{9}$', req.phone):
                raise HTTPException(status_code=400, detail="手机号格式不正确")
            phone_exists = db.query(User).filter(User.phone == req.phone, User.id != user_id).first()
            if phone_exists:
                raise HTTPException(status_code=400, detail="该手机号已被注册")
        user.phone = req.phone if req.phone else None

    # 更新项目归属（project_ids 优先于 project_id）
    from models.models import UserProject
    pids = req.project_ids if req.project_ids is not None else ([req.project_id] if req.project_id is not None else None)
    if pids is not None:
        # 清除旧关联，写入新关联
        db.query(UserProject).filter(UserProject.user_id == user_id).delete()
        for pid in pids:
            db.add(UserProject(user_id=user_id, project_id=pid))
        user.project_id = pids[0] if pids else None

    user.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "用户更新成功"}


@router.delete("/{user_id}", summary="删除用户")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role(["admin"]))
):
    """删除用户（仅管理员）"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    db.delete(user)
    db.commit()
    return {"message": "用户删除成功"}


@router.get("/roles", summary="获取角色列表")
async def get_roles(
    current_user: User = Depends(check_role(["admin"]))
):
    """获取所有可用角色"""
    return {
        "roles": [
            {"value": "admin", "label": "系统管理员"},
            {"value": "inspector", "label": "检查员"},
            {"value": "site_supervisor", "label": "阵地督导"},
            {"value": "field_supervisor", "label": "驻场经理"},
            {"value": "project_staff", "label": "项目人员"}
        ]
    }
