"""
检查引导 API
为检查员提供AI辅助：重点检查项、相似案例、拍照建议
嵌入前端列表模式和巡检模式，不新增独立路由页面
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models.models import User, InspectionTask, InspectionRecord, Project
from api.deps import get_current_user, get_user_project_filter
from core.logger import get_logger

logger = get_logger("guide_api")

router = APIRouter()


class SimilarCaseRequest(BaseModel):
    item_id: str
    item_name: str
    module_name: str
    description: str = ""


@router.get("/focus/{project_id}/{module_name}", summary="获取模块检查重点关注项")
async def get_focus_items(
    project_id: int,
    module_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    获取某模块的检查重点关注项
    - 反复出现问题（长期记忆）
    - 上次检查扣分项
    - 跨项目共性问题
    - 高权重检查项

    前端在进入检查模块时调用，在侧边栏/卡片底部显示
    """
    from agents.guide import get_focus_items
    result = get_focus_items(project_id, module_name)
    return result


@router.get("/project-modules/{project_id}", summary="获取项目所有模块的检查概况")
async def get_project_module_overview(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取项目所有模块的检查概况
    用于检查前准备页面，一览各模块的历史问题数量和评分趋势
    """
    # 项目隔离检查
    project_filter = get_user_project_filter(current_user, db)
    if project_filter is not None and len(project_filter) == 0:
        raise HTTPException(status_code=403, detail="无权访问任何项目")
    if project_filter is not None:
        if project_id not in project_filter:
            raise HTTPException(status_code=403, detail="无权访问此项目")

    # 获取项目信息
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    from core import standards as _stds
    from models.models import ScoringResult, Issue as _Issue

    # 项目最近一次检查任务（决定模块清单与计分标准）
    last_task = db.query(InspectionTask).filter(
        InspectionTask.project_id == project_id
    ).order_by(InspectionTask.check_date.desc()).first()
    std_type = last_task.standard_type if last_task else "diecheng"
    last_check_date = str(last_task.check_date) if last_task else None

    modules = []
    for module_name in _stds.get_modules(std_type):
        cfg = _stds.get_module_cfg(std_type, module_name)
        last_score = None
        issue_count = 0

        if last_task:
            # 模块得分直接取已计算的 module_pct_score（按各标准计分模型正确）
            mod_results = db.query(ScoringResult).join(
                InspectionRecord, ScoringResult.record_id == InspectionRecord.record_id
            ).filter(
                InspectionRecord.task_id == last_task.task_id,
                ScoringResult.module_name == module_name,
                ScoringResult.module_pct_score.isnot(None),
            ).all()
            if mod_results:
                last_score = round(float(mod_results[0].module_pct_score), 2)
            # 该模块问题数
            issue_count = db.query(_Issue).join(
                InspectionRecord, _Issue.record_id == InspectionRecord.record_id
            ).filter(
                InspectionRecord.task_id == last_task.task_id,
                _Issue.module_name == module_name,
            ).count()

        modules.append({
            "module_name": module_name,
            "weight": cfg.get("weight", 0),
            "max_score": cfg.get("max_score"),
            "role": cfg.get("role", "score"),
            "last_score": last_score,
            "last_check_date": last_check_date,
            "last_issue_count": issue_count
        })

    return {
        "project_id": project_id,
        "project_name": project.name,
        "modules": modules
    }


@router.post("/similar-cases", summary="搜索相似历史案例")
async def search_similar_cases(
    request: SimilarCaseRequest,
    current_user: User = Depends(get_current_user)
):
    """
    检查员输入问题描述时，实时推荐相似历史案例
    基于 RAG 引擎搜索

    前端在问题输入框的自动补全/推荐中调用
    """
    from agents.guide import get_similar_cases
    cases = get_similar_cases(
        item_id=request.item_id,
        item_name=request.item_name,
        module_name=request.module_name,
        description=request.description
    )
    return {"total": len(cases), "cases": cases}


@router.get("/photo-tips/{module_name}/{item_id}", summary="获取拍照建议")
async def get_photo_tips(
    module_name: str,
    item_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    获取拍照建议（基于整改验证经验）

    前端在拍照上传区域附近显示
    """
    from agents.guide import get_photo_tips
    tips = get_photo_tips(item_id, module_name)
    return tips


# 导入 settings（用于模块权重）
from config import settings
