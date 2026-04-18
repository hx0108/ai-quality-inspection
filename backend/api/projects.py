"""
项目管理 API
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.models import Project
from api.deps import get_current_user, check_role
from models.models import User

router = APIRouter()


# ==================== 请求/响应模型 ====================
class ProjectCreate(BaseModel):
    name: str
    code: Optional[str] = None
    address: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    address: Optional[str] = None


# ==================== API 端点 ====================
@router.get("", summary="获取项目列表")
async def list_projects(
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取项目列表"""
    total = db.query(Project).count()
    projects = db.query(Project).order_by(Project.id).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "items": [
            {
                "id": p.id,
                "name": p.name,
                "code": p.code,
                "address": p.address,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in projects
        ]
    }


@router.post("", summary="创建项目")
async def create_project(
    req: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "field_supervisor"]))
):
    """创建项目"""
    existing = db.query(Project).filter(Project.name == req.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="项目名称已存在")

    project = Project(name=req.name, code=req.code, address=req.address)
    db.add(project)
    db.commit()
    db.refresh(project)
    return {"id": project.id, "name": project.name, "message": "项目创建成功"}


@router.put("/{project_id}", summary="更新项目")
async def update_project(
    project_id: int,
    req: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "field_supervisor"]))
):
    """更新项目信息"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    if req.name is not None:
        existing = db.query(Project).filter(Project.name == req.name, Project.id != project_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="项目名称已存在")
        project.name = req.name
    if req.code is not None:
        project.code = req.code
    if req.address is not None:
        project.address = req.address

    db.commit()
    return {"message": "项目更新成功"}


@router.delete("/{project_id}", summary="删除项目")
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role(["admin"]))
):
    """删除项目（仅管理员）"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 检查是否有关联任务
    if project.tasks and len(project.tasks) > 0:
        raise HTTPException(status_code=400, detail="该项目下有关联检查任务，无法删除")

    db.delete(project)
    db.commit()
    return {"message": "项目删除成功"}


@router.get("/all", summary="获取所有项目（下拉选择用）")
async def list_all_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取所有项目（不分页，用于下拉选择）"""
    projects = db.query(Project).order_by(Project.id).all()
    return {
        "items": [
            {"id": p.id, "name": p.name, "code": p.code}
            for p in projects
        ]
    }
