"""
知识库查询 API
为各角色提供历史问题点查询功能
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models.models import User, Issue, InspectionRecord, InspectionTask, Project
from api.deps import get_current_user
from core.logger import get_logger
from core.rag_engine import search_issues, get_issue_stats

logger = get_logger("knowledge_base_api")

router = APIRouter(tags=["知识库"])


class IssueSearchRequest(BaseModel):
    """问题搜索请求"""
    query: str = ""  # 关键词搜索
    project_id: Optional[int] = None  # 项目ID过滤
    module_name: Optional[str] = None  # 模块过滤
    severity: Optional[str] = None  # 严重程度过滤
    start_date: Optional[str] = None  # 开始日期
    end_date: Optional[str] = None  # 结束日期
    limit: int = 20  # 返回数量


class IssueResponse(BaseModel):
    """问题响应"""
    issue_id: str
    description: str
    module_name: str
    severity: str
    location: str
    project_name: str
    check_date: str
    task_id: str


class StatsResponse(BaseModel):
    """统计响应"""
    total_issues: int
    by_module: dict
    by_severity: dict
    by_project: dict


@router.get("/issues", summary="查询历史问题点")
async def search_historical_issues(
    query: str = Query("", description="搜索关键词"),
    project_id: Optional[int] = Query(None, description="项目ID"),
    module_name: Optional[str] = Query(None, description="模块名称"),
    severity: Optional[str] = Query(None, description="严重程度: 一般/中等/严重"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    多维度查询历史问题点

    权限说明：
    - 一线检查员：只能查询本人参与的项目
    - 驻场经理：只能查询本项目
    - 品质管理员/总监：可查询所有项目
    """
    # 权限控制：数据范围过滤
    visible_projects = _get_visible_projects(db, current_user)

    if not visible_projects:
        return {"issues": [], "total": 0, "message": "无权限访问的项目"}

    # 构建查询条件
    filters = []
    filters.append(InspectionRecord.project_id.in_(visible_projects))

    if project_id:
        if project_id not in visible_projects:
            return {"issues": [], "total": 0, "message": "无权访问该项目"}
        filters.append(InspectionRecord.project_id == project_id)

    if module_name:
        filters.append(Issue.module_name == module_name)

    if severity:
        filters.append(Issue.severity == severity)

    if start_date:
        filters.append(InspectionTask.check_date >= start_date)

    if end_date:
        filters.append(InspectionTask.check_date <= end_date)

    # 执行查询
    query_obj = db.query(Issue).join(
        InspectionRecord, Issue.record_id == InspectionRecord.record_id
    ).join(
        InspectionTask, InspectionRecord.task_id == InspectionTask.task_id
    ).join(
        Project, InspectionRecord.project_id == Project.id
    ).filter(*filters)

    if query:
        query_obj = query_obj.filter(
            Issue.description.like(f"%{query}%")
        )

    total = query_obj.count()
    issues = query_obj.order_by(InspectionTask.check_date.desc()).limit(50).all()

    return {
        "issues": [
            {
                "issue_id": i.issue_id,
                "description": i.description,
                "module_name": i.module_name,
                "severity": i.severity,
                "location": i.location,
                "project_name": i.record.task.project.name if i.record and i.record.task and i.record.task.project else "",
                "check_date": str(i.record.task.check_date) if i.record and i.record.task and i.record.task.check_date else "",
                "task_id": i.record.task.task_id if i.record and i.record.task else ""
            }
            for i in issues
        ],
        "total": total
    }


@router.get("/stats", summary="问题点统计")
async def get_issue_statistics(
    project_id: Optional[int] = Query(None, description="项目ID"),
    module_name: Optional[str] = Query(None, description="模块名称"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取问题点统计信息

    返回：
    - 总问题数
    - 按模块分布
    - 按严重程度分布
    - 按项目分布（管理员可见）
    """
    visible_projects = _get_visible_projects(db, current_user)

    if not visible_projects:
        return {"error": "无权限访问的项目"}

    filters = [InspectionRecord.project_id.in_(visible_projects)]

    if project_id and project_id in visible_projects:
        filters.append(InspectionRecord.project_id == project_id)

    if module_name:
        filters.append(Issue.module_name == module_name)

    if start_date:
        filters.append(InspectionTask.check_date >= start_date)

    if end_date:
        filters.append(InspectionTask.check_date <= end_date)

    # 总问题数
    total = db.query(Issue).join(
        InspectionRecord, Issue.record_id == InspectionRecord.record_id
    ).join(
        InspectionTask, InspectionRecord.task_id == InspectionTask.task_id
    ).filter(*filters).count()

    # 按模块统计
    module_stats = db.query(
        Issue.module_name,
        db.func.count(Issue.id).label("count")
    ).join(
        InspectionRecord, Issue.record_id == InspectionRecord.record_id
    ).join(
        InspectionTask, InspectionRecord.task_id == InspectionTask.task_id
    ).filter(*filters).group_by(Issue.module_name).all()

    # 按严重程度统计
    severity_stats = db.query(
        Issue.severity,
        db.func.count(Issue.id).label("count")
    ).join(
        InspectionRecord, Issue.record_id == InspectionRecord.record_id
    ).join(
        InspectionTask, InspectionRecord.task_id == InspectionTask.task_id
    ).filter(*filters).group_by(Issue.severity).all()

    # 按项目统计（仅品质管理员可见完整列表）
    project_stats = []
    if current_user.role in ["admin", "quality_admin"]:
        project_filters = [] if project_id in visible_projects else [InspectionRecord.project_id.in_(visible_projects)]
        project_stats_query = db.query(
            Project.name,
            db.func.count(Issue.id).label("count")
        ).join(
            InspectionRecord, Project.id == InspectionRecord.project_id
        ).join(
            Issue, InspectionRecord.record_id == Issue.record_id
        ).join(
            InspectionTask, InspectionRecord.task_id == InspectionTask.task_id
        ).filter(*(filters + project_filters)).group_by(Project.name).all()
        project_stats = [{"project": p[0], "count": p[1]} for p in project_stats_query]

    return {
        "total_issues": total,
        "by_module": {m.module_name: m.count for m in module_stats},
        "by_severity": {s.severity: s.count for s in severity_stats},
        "by_project": project_stats,
        "period": f"{start_date or '开始'} ~ {end_date or '至今'}"
    }


@router.get("/modules", summary="获取模块列表")
async def get_modules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有模块名称列表，用于下拉选择"""
    modules = db.query(Issue.module_name).distinct().all()
    return {"modules": [m[0] for m in modules if m[0]]}


@router.get("/projects", summary="获取可访问项目列表")
async def get_accessible_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户可访问的项目列表"""
    visible = _get_visible_projects(db, current_user)
    projects = db.query(Project).filter(Project.id.in_(visible)).all()
    return {
        "projects": [
            {"id": p.id, "name": p.name}
            for p in projects
        ]
    }


@router.get("/frequent-issues", summary="高频问题TOP10")
async def get_frequent_issues(
    project_id: Optional[int] = Query(None, description="项目ID"),
    limit: int = Query(10, description="返回数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取高频问题（按问题描述聚类）

    帮助用户了解反复出现的问题类型
    """
    visible_projects = _get_visible_projects(db, current_user)

    filters = [InspectionRecord.project_id.in_(visible_projects)]
    if project_id and project_id in visible_projects:
        filters.append(InspectionRecord.project_id == project_id)

    # 统计相同描述的问题出现次数
    frequent = db.query(
        Issue.description,
        Issue.module_name,
        Issue.severity,
        db.func.count(Issue.id).label("count")
    ).join(
        InspectionRecord, Issue.record_id == InspectionRecord.record_id
    ).join(
        InspectionTask, InspectionRecord.task_id == InspectionTask.task_id
    ).filter(*filters).group_by(
        Issue.description,
        Issue.module_name,
        Issue.severity
    ).order_by(
        db.func.count(Issue.id).desc()
    ).limit(limit).all()

    return {
        "frequent_issues": [
            {
                "description": f.description[:100] + "..." if len(f.description) > 100 else f.description,
                "module_name": f.module_name,
                "severity": f.severity,
                "occurrence_count": f.count
            }
            for f in frequent
        ]
    }


def _get_visible_projects(db: Session, user: User) -> List[int]:
    """
    根据用户角色获取可见项目ID列表

    权限逻辑：
    - admin/quality_admin: 所有项目
    - field_supervisor: 所属项目
    - 项目人员: 所属项目
    - 检查员: 参与过的项目
    """
    if user.role in ["admin", "quality_admin"]:
        # 管理员可见所有项目
        all_projects = db.query(Project.id).all()
        return [p[0] for p in all_projects]

    elif user.role == "field_supervisor":
        # 驻场经理只可见本项目
        if user.project_id:
            return [user.project_id]
        return []

    elif hasattr(user, 'project_id') and user.project_id:
        # 项目人员只可见本项目
        return [user.project_id]

    else:
        # 尝试从检查记录获取用户参与过的项目
        from models.models import InspectionTask
        tasks = db.query(InspectionTask.task_id).filter(
            InspectionTask.inspector_id == user.id
        ).distinct().all()

        if not tasks:
            return []

        records = db.query(InspectionRecord.project_id).filter(
            InspectionRecord.task_id.in_([t[0] for t in tasks])
        ).distinct().all()

        return [r[0] for r in records]