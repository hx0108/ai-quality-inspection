"""
数据概览统计 API
仪表盘首页数据聚合
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_

from database import get_db
from models.models import (
    User, Project, InspectionTask, InspectionRecord,
    Issue, ScoringResult, Report, Rectification
)
from api.deps import get_current_user

router = APIRouter()


@router.get("/dashboard", summary="仪表盘数据概览")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """聚合返回仪表盘所需的全部统计数据"""

    # ===== 1. 核心数字 =====
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # 总项目数
    total_projects = db.query(func.count(Project.id)).scalar() or 0

    # 总任务数 & 各状态
    task_stats = db.query(
        InspectionTask.status,
        func.count(InspectionTask.id)
    ).group_by(InspectionTask.status).all()
    task_status_map = {s: c for s, c in task_stats}
    total_tasks = sum(task_status_map.values())
    pending_tasks = task_status_map.get("pending", 0)
    in_progress_tasks = task_status_map.get("in_progress", 0)
    completed_tasks = task_status_map.get("completed", 0)

    # 本月任务数
    monthly_tasks = db.query(func.count(InspectionTask.id)).filter(
        InspectionTask.created_at >= month_start
    ).scalar() or 0

    # ===== 2. 问题统计 =====
    issue_severity = db.query(
        Issue.severity,
        func.count(Issue.id)
    ).group_by(Issue.severity).all()
    severity_map = {s: c for s, c in issue_severity}
    total_issues = sum(severity_map.values())
    serious_issues = severity_map.get("严重", 0)
    general_issues = severity_map.get("一般", 0)
    minor_issues = severity_map.get("轻微", 0)

    # 本月新增问题
    monthly_issues = db.query(func.count(Issue.id)).filter(
        Issue.created_at >= month_start
    ).scalar() or 0

    # ===== 3. 整改统计 =====
    rect_stats = db.query(
        Rectification.status,
        func.count(Rectification.id)
    ).group_by(Rectification.status).all()
    rect_map = {s: c for s, c in rect_stats}
    pending_rectifications = rect_map.get("pending", 0)
    submitted_rectifications = rect_map.get("submitted", 0)
    approved_rectifications = rect_map.get("approved", 0)
    rejected_rectifications = rect_map.get("rejected", 0)
    total_rectifications = sum(rect_map.values())

    # ===== 4. 报告数 =====
    total_reports = db.query(func.count(Report.id)).scalar() or 0

    # ===== 5. 检查覆盖率 =====
    # 本月有多少项目被检查过（有任务）
    monthly_checked_projects = db.query(
        func.count(func.distinct(InspectionTask.project_id))
    ).filter(
        InspectionTask.created_at >= month_start
    ).scalar() or 0

    coverage_rate = round(monthly_checked_projects / total_projects * 100, 1) if total_projects > 0 else 0

    # ===== 6. 最近6个月得分趋势 =====
    six_months_ago = now - timedelta(days=180)
    monthly_scores = db.query(
        func.strftime('%Y-%m', InspectionTask.created_at).label('month'),
        func.round(func.avg(InspectionTask.total_score), 1).label('avg_score'),
        func.count(InspectionTask.id).label('task_count')
    ).filter(
        InspectionTask.total_score.isnot(None),
        InspectionTask.created_at >= six_months_ago
    ).group_by(
        func.strftime('%Y-%m', InspectionTask.created_at)
    ).order_by('month').all()

    score_trend = [
        {"month": row.month, "avg_score": float(row.avg_score) if row.avg_score else 0, "task_count": row.task_count}
        for row in monthly_scores
    ]

    # ===== 7. 各项目最新得分 =====
    latest_scores_subq = db.query(
        InspectionTask.project_id,
        func.max(InspectionTask.check_date).label('latest_date')
    ).filter(
        InspectionTask.total_score.isnot(None)
    ).group_by(InspectionTask.project_id).subquery()

    project_scores = db.query(
        Project.name,
        func.max(InspectionTask.total_score).label('total_score'),
        InspectionTask.check_date
    ).join(
        latest_scores_subq,
        and_(
            InspectionTask.project_id == latest_scores_subq.c.project_id,
            InspectionTask.check_date == latest_scores_subq.c.latest_date
        )
    ).join(
        Project, InspectionTask.project_id == Project.id
    ).group_by(Project.name, InspectionTask.check_date).all()

    project_latest_scores = [
        {"project_name": row.name, "latest_score": float(row.total_score) if row.total_score else 0, "check_date": row.check_date}
        for row in project_scores
    ]

    # ===== 8. 问题按模块分布 =====
    module_issues = db.query(
        Issue.module_name,
        func.count(Issue.id)
    ).group_by(Issue.module_name).order_by(func.count(Issue.id).desc()).limit(8).all()

    issue_by_module = [
        {"module_name": row.module_name, "count": row[1]}
        for row in module_issues
    ]

    # ===== 9. 最近5条待处理任务 =====
    recent_tasks = db.query(InspectionTask).order_by(
        InspectionTask.created_at.desc()
    ).limit(5).all()

    recent_task_list = [
        {
            "task_id": t.task_id,
            "project_name": t.project.name if t.project else "",
            "check_date": t.check_date,
            "status": t.status,
            "total_score": float(t.total_score) if t.total_score else None
        }
        for t in recent_tasks
    ]

    return {
        "summary": {
            "total_projects": total_projects,
            "total_tasks": total_tasks,
            "pending_tasks": pending_tasks,
            "in_progress_tasks": in_progress_tasks,
            "completed_tasks": completed_tasks,
            "monthly_tasks": monthly_tasks,
            "total_issues": total_issues,
            "serious_issues": serious_issues,
            "general_issues": general_issues,
            "minor_issues": minor_issues,
            "monthly_issues": monthly_issues,
            "total_rectifications": total_rectifications,
            "pending_rectifications": pending_rectifications,
            "total_reports": total_reports,
            "coverage_rate": coverage_rate,
            "monthly_checked_projects": monthly_checked_projects,
        },
        "score_trend": score_trend,
        "project_latest_scores": project_latest_scores,
        "issue_by_module": issue_by_module,
        "recent_tasks": recent_task_list,
    }
