"""
综合分析 API
Agent 4: 基于 DeepSeek-V3.2 的多维度对比分析
"""
import json
import uuid
import time
from datetime import datetime
from typing import Optional
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from database import get_db, SessionLocal
from models.models import (
    User, Project, InspectionTask, Report,
    AnalysisRecord, AnalysisProject
)
from api.deps import get_current_user, check_role, get_user_project_filter
from config import settings
from core.logger import get_logger

logger = get_logger("analysis")

router = APIRouter()

# 进度缓存（内存+数据库双写）
analysis_progress = {}  # {analysis_id: {status, current_step, progress_pct, error}}

# 分析生成速率限制：防止用户频繁触发分析
_analysis_trigger_times: dict = {}  # {(user_id, mode): last_trigger_timestamp}
_ANALYSIS_RATE_LIMIT = 60  # 60秒内不能重复触发同一类型的分析


def _persist_analysis_progress(analysis_id: str):
    """将分析进度持久化到数据库"""
    try:
        from core.progress_store import progress_store
        data = analysis_progress.get(analysis_id, {})
        progress_store.update(
            "analysis", analysis_id,
            status=data.get("status", "running"),
            detail={
                "current_step": data.get("current_step", ""),
                "progress_pct": data.get("progress_pct", 0),
            },
            error=data.get("error")
        )
    except Exception:
        pass


# ==================== 请求/响应模型 ====================

class AnalysisStartRequest(BaseModel):
    mode: str  # "cross_project" | "cross_time" | "all_projects"
    project_a_id: Optional[int] = None
    project_b_id: Optional[int] = None
    time_range_start: Optional[str] = None
    time_range_end: Optional[str] = None
    report_a_id: Optional[str] = None
    report_b_id: Optional[str] = None
    filters: Optional[dict] = None


# ==================== 后台任务 ====================

def run_analysis_sync(analysis_id: str, request_data: dict, user_id: int):
    """同步运行分析任务（在 BackgroundTasks 线程中执行）"""
    import asyncio as asyncio_module

    analysis_progress[analysis_id] = {
        "status": "running",
        "current_step": "validate_input",
        "progress_pct": 0,
        "error": None
    }
    _persist_analysis_progress(analysis_id)

    loop = asyncio_module.new_event_loop()
    asyncio_module.set_event_loop(loop)

    # 在新事件循环中重置共享 httpx 客户端，避免绑定到旧 loop
    from core.llm_client import DeepSeekClient
    DeepSeekClient.reset_client()

    try:
        logger.info(f"开始综合分析: {analysis_id}")
        result = loop.run_until_complete(_run_analysis_graph(analysis_id, request_data, user_id))

        analysis_progress[analysis_id]["status"] = "completed"
        analysis_progress[analysis_id]["progress_pct"] = 100
        analysis_progress[analysis_id]["current_step"] = "completed"
        _persist_analysis_progress(analysis_id)
        logger.info(f"综合分析完成: {analysis_id}")
    except Exception as e:
        logger.error(f"综合分析失败: {e}")
        import traceback
        traceback.print_exc()
        analysis_progress[analysis_id]["status"] = "failed"
        analysis_progress[analysis_id]["error"] = str(e)
        _persist_analysis_progress(analysis_id)

        # 更新数据库记录状态
        db = SessionLocal()
        try:
            record = db.query(AnalysisRecord).filter(
                AnalysisRecord.analysis_id == analysis_id
            ).first()
            if record:
                record.summary_text = f"分析失败: {str(e)[:200]}"
                db.commit()
        finally:
            db.close()
    finally:
        loop.close()


async def _run_analysis_graph(analysis_id: str, request_data: dict, user_id: int):
    """执行 LangGraph 分析工作流"""
    from agents.analysis import build_analysis_graph

    initial_state = {
        "analysis_id": analysis_id,
        "mode": request_data["mode"],
        "project_a_id": request_data.get("project_a_id"),
        "project_b_id": request_data.get("project_b_id"),
        "time_range_start": request_data.get("time_range_start"),
        "time_range_end": request_data.get("time_range_end"),
        "report_a_id": request_data.get("report_a_id"),
        "report_b_id": request_data.get("report_b_id"),
        "filters": request_data.get("filters"),
        "reports_data": [],
        "projects_info": [],
        "label_a": "",
        "label_b": "",
        "comparison_matrix": [],
        "score_analysis": {},
        "issue_analysis": {},
        "module_analysis": {},
        "ai_result": {},
        "executive_summary": "",
        "action_items": [],
        "chart_data": {},
        "final_report_md": "",
        "export_paths": {},
        "current_step": "init",
        "progress_pct": 0,
        "valid": True,
        "error_message": "",
        "errors": []
    }

    graph = build_analysis_graph()

    # 使用 ainvoke 并在回调中更新进度
    async def _update_progress(step: str, pct: int):
        analysis_progress[analysis_id]["current_step"] = step
        analysis_progress[analysis_id]["progress_pct"] = pct

    # LangGraph 支持流式回调
    final_state = None
    # 手动进度映射（并行节点不返回进度）
    step_progress = {
        "validate_input": ("验证参数", 5),
        "collect_reports": ("收集报告数据", 15),
        "analyze_score": ("分析得分", 25),
        "analyze_issue": ("分析问题", 30),
        "analyze_module": ("分析模块", 35),
        "generate_insight": ("AI生成洞察", 40),
        "render_charts": ("生成图表", 75),
        "assemble_report": ("组装报告", 85),
        "export_files": ("导出文件", 90),
        "save_result": ("保存结果", 95),
    }
    async for event in graph.astream(initial_state):
        # event 是 {node_name: output_dict} 格式
        for node_name, output in event.items():
            step = output.get("current_step", "")
            pct = output.get("progress_pct", 0)
            if not step:
                # 并行节点没有 current_step，使用手动映射
                mapped = step_progress.get(node_name, (node_name, 0))
                step, pct = mapped
            await _update_progress(step, pct)

            # 检查是否验证失败
            if output.get("valid") is False:
                error_msg = output.get("error_message", "验证失败")
                raise ValueError(error_msg)

            final_state = output

    return final_state


# ==================== API 端点 ====================

@router.post("/start")
async def start_analysis(
    request: AnalysisStartRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    启动综合分析（后台任务）
    权限: admin/inspector/site_supervisor/field_supervisor 可用，project_staff 不可用
    """
    # project_staff 不可使用综合分析
    if current_user.role == "project_staff":
        raise HTTPException(status_code=403, detail="无权使用综合分析功能")

    # 生成分析ID
    analysis_id = f"ANA-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"

    # 参数预校验
    mode = request.mode
    if mode not in ("cross_project", "cross_time", "all_projects"):
        raise HTTPException(status_code=400, detail=f"不支持的模式: {mode}")

    if mode == "cross_project":
        if not request.report_a_id or not request.report_b_id:
            raise HTTPException(status_code=400, detail="跨项目对比需要选择两个报告")
        if request.report_a_id == request.report_b_id:
            raise HTTPException(status_code=400, detail="请选择两个不同的报告")

    elif mode == "cross_time":
        if not request.project_a_id:
            raise HTTPException(status_code=400, detail="跨时段对比需要选择一个项目")

    elif mode == "all_projects":
        if not request.time_range_start or not request.time_range_end:
            raise HTTPException(status_code=400, detail="全项目概览需要指定时间范围")

    # 速率限制：60秒内同一用户不能重复触发同类型分析
    rate_key = (current_user.id, mode)
    now = time.time()
    if rate_key in _analysis_trigger_times:
        elapsed = now - _analysis_trigger_times[rate_key]
        if elapsed < _ANALYSIS_RATE_LIMIT:
            raise HTTPException(
                status_code=429,
                detail=f"分析生成过于频繁，请{int(_ANALYSIS_RATE_LIMIT - elapsed)}秒后再试"
            )
    _analysis_trigger_times[rate_key] = now

    # 创建初始记录
    db = SessionLocal()
    try:
        record = AnalysisRecord(
            analysis_id=analysis_id,
            mode=mode,
            project_a_id=request.project_a_id,
            project_b_id=request.project_b_id,
            report_a_id=request.report_a_id,
            report_b_id=request.report_b_id,
            time_range_start=request.time_range_start,
            time_range_end=request.time_range_end,
            summary_text="分析进行中...",
            created_by=current_user.id
        )
        db.add(record)
        db.commit()
    finally:
        db.close()

    # 后台执行
    request_data = request.model_dump()
    background_tasks.add_task(run_analysis_sync, analysis_id, request_data, current_user.id)

    return {
        "analysis_id": analysis_id,
        "status": "running",
        "message": "分析任务已启动"
    }


@router.get("/{analysis_id}/progress")
async def get_progress(
    analysis_id: str,
    current_user: User = Depends(get_current_user)
):
    """查询分析进度（管理员/检查员/督导可查所有， others 只能查自己创建的）"""
    # 权限检查：admin/inspector/site_supervisor/field_supervisor 可查所有记录
    if current_user.role not in ("admin", "inspector", "site_supervisor", "field_supervisor"):
        db_check = SessionLocal()
        try:
            rec = db_check.query(AnalysisRecord).filter(
                AnalysisRecord.analysis_id == analysis_id
            ).first()
            if not rec or rec.created_by != current_user.id:
                raise HTTPException(status_code=403, detail="无权访问此分析记录")
        finally:
            db_check.close()

    progress = analysis_progress.get(analysis_id)
    if not progress:
        # 先尝试从进度持久化表恢复
        try:
            from core.progress_store import progress_store
            db_progress = progress_store.get("analysis", analysis_id)
            if db_progress and db_progress.get("status") in ("running", "pending"):
                detail = db_progress.get("detail", {})
                progress = {
                    "status": db_progress["status"],
                    "current_step": detail.get("current_step", ""),
                    "progress_pct": detail.get("progress_pct", 0),
                    "error": db_progress.get("error"),
                }
                analysis_progress[analysis_id] = progress
        except Exception:
            pass

    if not progress:
        # 检查数据库是否有已完成/失败的记录
        db = SessionLocal()
        try:
            record = db.query(AnalysisRecord).filter(
                AnalysisRecord.analysis_id == analysis_id
            ).first()
            if record:
                if record.result_json:
                    return {
                        "analysis_id": analysis_id,
                        "status": "completed",
                        "current_step": "completed",
                        "progress_pct": 100,
                        "estimated_remaining_sec": 0
                    }
                elif "失败" in (record.summary_text or ""):
                    return {
                        "analysis_id": analysis_id,
                        "status": "failed",
                        "current_step": "failed",
                        "progress_pct": 0,
                        "error": record.summary_text
                    }
        finally:
            db.close()

        raise HTTPException(status_code=404, detail="分析记录不存在")

    return {
        "analysis_id": analysis_id,
        "status": progress["status"],
        "current_step": progress["current_step"],
        "progress_pct": progress["progress_pct"],
        "estimated_remaining_sec": max(0, (100 - progress["progress_pct"]) // 5),
        "error": progress.get("error")
    }


@router.get("/{analysis_id}/result")
async def get_result(
    analysis_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取分析结果（管理员/检查员/督导可看全部， others 只能看自己创建的）"""
    db = SessionLocal()
    try:
        record = db.query(AnalysisRecord).filter(
            AnalysisRecord.analysis_id == analysis_id
        ).first()
        if not record:
            raise HTTPException(status_code=404, detail="分析记录不存在")

        # admin/inspector/site_supervisor/field_supervisor 可看所有记录
        if current_user.role not in ("admin", "inspector", "site_supervisor", "field_supervisor") and record.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="无权访问此分析记录")

        if not record.result_json:
            # 检查进度
            progress = analysis_progress.get(analysis_id)
            if progress and progress["status"] == "running":
                return {
                    "analysis_id": analysis_id,
                    "status": "running",
                    "progress_pct": progress["progress_pct"],
                    "current_step": progress["current_step"]
                }
            raise HTTPException(status_code=400, detail="分析结果尚未就绪")

        result_data = json.loads(record.result_json) if isinstance(record.result_json, str) else record.result_json

        # 构建响应
        response = {
            "analysis_id": record.analysis_id,
            "mode": record.mode,
            "status": "completed",
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "executive_summary": record.summary_text,
            "score_analysis": result_data.get("score_analysis", {}),
            "issue_analysis": result_data.get("issue_analysis", {}),
            "module_analysis": result_data.get("module_analysis", {}),
            "chart_data": result_data.get("chart_data", {}),
            "comparison_matrix": result_data.get("comparison_matrix", []),
            "projects_info": result_data.get("projects_info", []),
            "label_a": result_data.get("label_a", ""),
            "label_b": result_data.get("label_b", ""),
            "ai_result": result_data.get("ai_result", {}),
            "action_items": result_data.get("ai_result", {}).get("action_items", []),
            "export_paths": {
                "word": record.file_path,
                "pdf": record.pdf_path
            } if record.file_path else {}
        }

        # 模式三额外返回排行数据
        if record.mode == "all_projects":
            ap_records = db.query(AnalysisProject).filter(
                AnalysisProject.analysis_id == analysis_id
            ).order_by(AnalysisProject.rank_position).all()
            response["ranking"] = [
                {
                    "rank": ap.rank_position,
                    "project_id": ap.project_id,
                    "report_id": ap.report_id,
                    "grade": ap.grade
                }
                for ap in ap_records
            ]

        return response
    finally:
        db.close()


@router.delete("/{analysis_id}")
async def delete_analysis(
    analysis_id: str,
    current_user: User = Depends(check_role(["admin"]))
):
    """删除综合分析记录（仅系统管理员）"""
    import os

    db = SessionLocal()
    try:
        record = db.query(AnalysisRecord).filter(
            AnalysisRecord.analysis_id == analysis_id
        ).first()
        if not record:
            raise HTTPException(status_code=404, detail="分析记录不存在")

        # 删除关联的导出文件
        for path in [record.file_path, record.pdf_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

        # 删除关联的 AnalysisProject 记录
        db.query(AnalysisProject).filter(
            AnalysisProject.analysis_id == analysis_id
        ).delete()

        # 删除分析记录
        db.delete(record)
        db.commit()

        # 清理内存中的进度缓存
        analysis_progress.pop(analysis_id, None)

        return {"message": "分析记录已删除"}
    finally:
        db.close()


@router.get("/history")
async def get_history(
    page: int = 1,
    size: int = 20,
    mode: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """历史分析记录列表（分页）
    - 管理员/检查员/督导可看全部记录
    - 其他用户只能看自己创建的记录
    """
    db = SessionLocal()
    try:
        query = db.query(AnalysisRecord).order_by(desc(AnalysisRecord.created_at))

        # admin/inspector/site_supervisor/field_supervisor 可看所有记录
        if current_user.role not in ("admin", "inspector", "site_supervisor", "field_supervisor"):
            query = query.filter(AnalysisRecord.created_by == current_user.id)

        if mode:
            query = query.filter(AnalysisRecord.mode == mode)

        total = query.count()
        records = query.offset((page - 1) * size).limit(size).all()

        items = []
        for r in records:
            # 构建摘要描述
            summary = r.summary_text or "无摘要"
            if r.mode == "cross_project":
                # 优先从报告获取项目名
                if r.report_a_id and r.report_b_id:
                    ra = db.query(Report).filter(Report.report_id == r.report_a_id).first()
                    rb = db.query(Report).filter(Report.report_id == r.report_b_id).first()
                    pa_name = db.query(Project).filter(Project.id == ra.project_id).first().name if ra else "?"
                    pb_name = db.query(Project).filter(Project.id == rb.project_id).first().name if rb else "?"
                    summary = f"{pa_name} vs {pb_name}"
                elif r.project_a_id and r.project_b_id:
                    pa = db.query(Project).filter(Project.id == r.project_a_id).first()
                    pb = db.query(Project).filter(Project.id == r.project_b_id).first()
                    summary = f"{pa.name if pa else '?'} vs {pb.name if pb else '?'}"
            elif r.mode == "cross_time":
                pa = db.query(Project).filter(Project.id == r.project_a_id).first()
                summary = f"{pa.name if pa else '?'} 跨时段分析"
            elif r.mode == "all_projects":
                summary = f"全项目概览 ({r.time_range_start} ~ {r.time_range_end})"

            items.append({
                "analysis_id": r.analysis_id,
                "mode": r.mode,
                "summary": summary,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "status": "completed" if r.result_json else ("failed" if "失败" in (r.summary_text or "") else "running"),
                "has_file": bool(r.file_path)
            })

        return {
            "total": total,
            "page": page,
            "size": size,
            "records": items
        }
    finally:
        db.close()


@router.get("/projects-with-reports")
async def get_projects_with_reports(
    start: Optional[str] = None,
    end: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """获取有报告的项目列表（按项目隔离）"""
    db = SessionLocal()
    try:
        # 项目级隔离：site_supervisor / field_supervisor / project_staff 只能看自己项目
        project_filter = get_user_project_filter(current_user, db)
        if project_filter is not None and len(project_filter) == 0:
            return []

        # 查找有报告的项目
        query = db.query(
            Report.project_id,
            Project.name.label("project_name"),
            func.count(Report.report_id).label("report_count"),
            func.max(Report.total_score).label("latest_score"),
            func.max(Report.generated_at).label("latest_report_date")
        ).join(
            Project, Report.project_id == Project.id
        ).filter(
            Report.content_json.isnot(None),
            Report.content_json != ""
        )

        if project_filter is not None:
            query = query.filter(Report.project_id.in_(project_filter))

        # 关联任务过滤时间范围
        if start or end:
            query = query.join(
                InspectionTask, Report.task_id == InspectionTask.task_id
            )
            if start:
                query = query.filter(InspectionTask.check_date >= start)
            if end:
                query = query.filter(InspectionTask.check_date <= end)

        query = query.group_by(Report.project_id, Project.name).order_by(Project.id)

        results = query.all()

        # 为每个项目获取最新报告ID
        projects = []
        for r in results:
            latest_report = db.query(Report).filter(
                Report.project_id == r.project_id,
                Report.content_json.isnot(None)
            ).order_by(desc(Report.generated_at)).first()

            reports_list = db.query(Report).filter(
                Report.project_id == r.project_id,
                Report.content_json.isnot(None)
            ).order_by(desc(Report.generated_at)).all()

            projects.append({
                "project_id": r.project_id,
                "project_name": r.project_name,
                "latest_score": round(float(r.latest_score or 0), 2),
                "latest_report_id": latest_report.report_id if latest_report else None,
                "latest_report_date": latest_report.generated_at.isoformat() if latest_report and latest_report.generated_at else None,
                "report_count": r.report_count,
                "reports": [
                    {
                        "report_id": rpt.report_id,
                        "total_score": round(float(rpt.total_score or 0), 2),
                        "generated_at": rpt.generated_at.isoformat() if rpt.generated_at else None,
                    }
                    for rpt in reports_list
                ]
            })

        return {"projects": projects}
    finally:
        db.close()


@router.get("/{analysis_id}/download")
async def download_file(
    analysis_id: str,
    file_type: str = "word",
    current_user: User = Depends(get_current_user)
):
    """下载分析报告文件（Word/PDF）（管理员/检查员/督导可下载所有， others 只能下载自己创建的）"""
    db = SessionLocal()
    try:
        record = db.query(AnalysisRecord).filter(
            AnalysisRecord.analysis_id == analysis_id
        ).first()
        if not record:
            raise HTTPException(status_code=404, detail="分析记录不存在")

        # admin/inspector/site_supervisor/field_supervisor 可下载所有记录
        if current_user.role not in ("admin", "inspector", "site_supervisor", "field_supervisor") and record.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="无权访问此分析记录")

        import os

        if file_type == "pdf":
            if not record.pdf_path:
                raise HTTPException(status_code=400, detail="该分析暂无PDF文件")
            if not os.path.exists(record.pdf_path):
                raise HTTPException(status_code=404, detail="PDF文件已被删除或移动")
            filename = os.path.basename(record.pdf_path)
            return FileResponse(
                path=record.pdf_path,
                filename=filename,
                media_type="application/pdf"
            )
        else:
            if not record.file_path:
                raise HTTPException(status_code=400, detail="该分析暂无Word文件")
            if not os.path.exists(record.file_path):
                raise HTTPException(status_code=404, detail="Word文件已被删除或移动")
            filename = os.path.basename(record.file_path)
            return FileResponse(
                path=record.file_path,
                filename=filename,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
    finally:
        db.close()


# ==================== 仪表盘数据统计 ====================
def _build_coverage_detail(db, month_start_str: str):
    """构建本月覆盖率明细：已检查/未检查项目列表，与 summary.mcp 使用相同逻辑"""
    from models.models import Project, InspectionTask

    # 本月有检查任务（check_date >= 月初）的项目ID
    checked_ids = set(
        row[0] for row in db.query(func.distinct(InspectionTask.project_id)).filter(
            InspectionTask.check_date >= month_start_str
        ).all()
    )

    all_projects = db.query(Project).order_by(Project.name).all()

    checked = []
    unchecked = []
    for p in all_projects:
        if p.id in checked_ids:
            # 获取该项目本月最近一次检查日期
            latest = db.query(func.max(InspectionTask.check_date)).filter(
                InspectionTask.project_id == p.id,
                InspectionTask.check_date >= month_start_str
            ).scalar()
            checked.append({
                "project_id": p.id,
                "project_name": p.name,
                "check_date": latest,
            })
        else:
            unchecked.append({
                "id": p.id,
                "name": p.name,
            })

    return {
        "checked_projects": checked,
        "unchecked_projects": unchecked,
    }


@router.get("/dashboard/stats", summary="仪表盘数据概览")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """聚合返回仪表盘所需的全部统计数据"""
    from models.models import (
        Project, InspectionTask, InspectionRecord,
        Issue, ScoringResult, Report, Rectification
    )
    from sqlalchemy import and_
    from datetime import timedelta

    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_start_str = month_start.strftime("%Y-%m-%d")

    # 核心数字
    total_projects = db.query(func.count(Project.id)).scalar() or 0

    task_stats = db.query(
        InspectionTask.status, func.count(InspectionTask.id)
    ).group_by(InspectionTask.status).all()
    tsm = {s: c for s, c in task_stats}
    total_tasks = sum(tsm.values())

    monthly_tasks = db.query(func.count(InspectionTask.id)).filter(
        InspectionTask.created_at >= month_start
    ).scalar() or 0

    # 只统计已完成模块的问题（进行中的模块问题尚未确认）
    completed_record_ids = db.query(InspectionRecord.record_id).filter(
        InspectionRecord.status == "completed"
    ).subquery()
    issue_sev = db.query(
        Issue.severity, func.count(Issue.id)
    ).filter(
        Issue.record_id.in_(db.query(completed_record_ids.c.record_id))
    ).group_by(Issue.severity).all()
    sev_map = {s: c for s, c in issue_sev}
    total_issues = sum(sev_map.values())
    monthly_issues = db.query(func.count(Issue.id)).filter(
        Issue.created_at >= month_start,
        Issue.record_id.in_(db.query(completed_record_ids.c.record_id))
    ).scalar() or 0

    rect_stats = db.query(
        Rectification.status, func.count(Rectification.id)
    ).group_by(Rectification.status).all()
    rm = {s: c for s, c in rect_stats}

    total_reports = db.query(func.count(Report.id)).scalar() or 0

    mcp = db.query(func.count(func.distinct(InspectionTask.project_id))).filter(
        InspectionTask.check_date >= month_start_str
    ).scalar() or 0
    coverage = round(mcp / total_projects * 100, 1) if total_projects > 0 else 0

    # 得分趋势（近6月）—— 直接从 ScoringResult 计算，不依赖 task.total_score
    from collections import defaultdict
    six_months = now - timedelta(days=180)

    # 获取所有有评分结果的模块得分
    scoring_rows = db.query(
        InspectionTask.task_id,
        func.strftime('%Y-%m', InspectionTask.created_at).label('month'),
        ScoringResult.module_name,
        func.max(ScoringResult.module_pct_score).label('module_score')
    ).join(
        InspectionRecord, ScoringResult.record_id == InspectionRecord.record_id
    ).join(
        InspectionTask, InspectionRecord.task_id == InspectionTask.task_id
    ).filter(
        InspectionTask.created_at >= six_months,
        ScoringResult.module_pct_score.isnot(None)
    ).group_by(
        InspectionTask.task_id,
        func.strftime('%Y-%m', InspectionTask.created_at),
        ScoringResult.module_name
    ).all()

    # 按任务计算加权总分
    task_month = {}
    task_modules = defaultdict(dict)
    for row in scoring_rows:
        task_month[row.task_id] = row.month
        task_modules[row.task_id][row.module_name] = float(row.module_score)

    monthly_scores = defaultdict(list)
    for task_id, modules in task_modules.items():
        total = sum(
            modules.get(mname, 0) * mweight
            for mname, mweight in settings.MODULE_WEIGHTS.items()
        )
        monthly_scores[task_month[task_id]].append(round(total, 1))

    trend_result = [
        {"month": m, "avg_score": round(sum(s) / len(s), 1), "task_count": len(s)}
        for m, s in sorted(monthly_scores.items()) if s
    ]

    # 各项目最新得分 —— 同样从 ScoringResult 计算
    # 获取每个任务的加权总分
    task_total_scores = {}
    for task_id, modules in task_modules.items():
        total = sum(
            modules.get(mname, 0) * mweight
            for mname, mweight in settings.MODULE_WEIGHTS.items()
        )
        task_total_scores[task_id] = round(total, 1)

    # 查找每个项目最新的有评分的任务
    project_tasks = db.query(
        InspectionTask.project_id,
        InspectionTask.task_id,
        InspectionTask.check_date,
        InspectionTask.created_at
    ).filter(
        InspectionTask.created_at >= six_months
    ).order_by(InspectionTask.created_at.desc()).all()

    # 每个项目取最新一个有评分的任务
    project_latest = {}
    for pt in project_tasks:
        if pt.project_id not in project_latest and pt.task_id in task_total_scores:
            project_latest[pt.project_id] = {
                'task_id': pt.task_id,
                'score': task_total_scores[pt.task_id],
                'modules': task_modules.get(pt.task_id, {}),
                'date': pt.check_date,
            }

    project_scores = []
    for pid, info in project_latest.items():
        proj = db.query(Project).filter(Project.id == pid).first()
        if proj:
            project_scores.append({
                "project_id": pid,
                "project_name": proj.name,
                "latest_score": info['score'],
                "check_date": info['date'],
                "modules": info['modules'],
            })
    # 按得分降序
    project_scores.sort(key=lambda x: x['latest_score'], reverse=True)

    # 问题按模块分布（仅已完成模块）
    module_issues = db.query(
        Issue.module_name, func.count(Issue.id)
    ).filter(
        Issue.record_id.in_(db.query(completed_record_ids.c.record_id))
    ).group_by(Issue.module_name).order_by(func.count(Issue.id).desc()).limit(8).all()

    # 各项目整改统计（已整改 vs 未整改）
    project_rect_raw = db.query(
        InspectionTask.project_id,
        Rectification.status,
        func.count(Rectification.id)
    ).join(
        InspectionRecord, Rectification.record_id == InspectionRecord.record_id
    ).join(
        InspectionTask, InspectionRecord.task_id == InspectionTask.task_id
    ).group_by(
        InspectionTask.project_id, Rectification.status
    ).all()

    proj_rect_map = defaultdict(lambda: {"approved": 0, "pending": 0})
    for row in project_rect_raw:
        pid = row[0]
        status = row[1]
        cnt = row[2]
        if status in ("approved", "ai_approved"):
            proj_rect_map[pid]["approved"] += cnt
        else:
            proj_rect_map[pid]["pending"] += cnt

    project_rectification_stats = []
    for pid, counts in proj_rect_map.items():
        proj = db.query(Project).filter(Project.id == pid).first()
        if proj:
            total_r = counts["approved"] + counts["pending"]
            project_rectification_stats.append({
                "project_name": proj.name,
                "approved": counts["approved"],
                "pending": counts["pending"],
                "total": total_r,
                "rate": round(counts["approved"] / total_r * 100, 1) if total_r > 0 else 0,
            })
    project_rectification_stats.sort(key=lambda x: x["rate"], reverse=True)

    # 最近5条任务
    recent = db.query(InspectionTask).order_by(InspectionTask.created_at.desc()).limit(5).all()

    # LLM 用量统计（近30天）
    usage_stats = []
    try:
        from models.models import LlmUsageLog
        thirty_days = now - timedelta(days=30)
        usage_stats = db.query(
            LlmUsageLog.model_name,
            func.sum(LlmUsageLog.total_tokens).label("total_tokens"),
            func.count(LlmUsageLog.id).label("call_count"),
        ).filter(
            LlmUsageLog.timestamp >= thirty_days
        ).group_by(LlmUsageLog.model_name).all()
    except Exception as e:
        logger.error(f"LLM usage query error: {e}")

    return {
        "summary": {
            "total_projects": total_projects,
            "total_tasks": total_tasks,
            "pending_tasks": tsm.get("pending", 0),
            "in_progress_tasks": tsm.get("in_progress", 0),
            "completed_tasks": tsm.get("completed", 0),
            "monthly_tasks": monthly_tasks,
            "total_issues": total_issues,
            "serious_issues": sev_map.get("严重", 0),
            "general_issues": sev_map.get("一般", 0),
            "minor_issues": sev_map.get("轻微", 0),
            "monthly_issues": monthly_issues,
            "total_rectifications": sum(rm.values()),
            "pending_rectifications": rm.get("pending", 0),
            "submitted_rectifications": rm.get("submitted", 0),
            "approved_rectifications": rm.get("approved", 0) + rm.get("ai_approved", 0),
            "rejected_rectifications": rm.get("rejected", 0) + rm.get("ai_rejected", 0),
            "rectification_rate": round((rm.get("approved", 0) + rm.get("ai_approved", 0)) / sum(rm.values()) * 100, 1) if sum(rm.values()) > 0 else 0,
            "total_reports": total_reports,
            "coverage_rate": coverage,
            "monthly_checked_projects": mcp,
        },
        "coverage_detail": _build_coverage_detail(db, month_start_str),
        "score_trend": trend_result,
        "project_latest_scores": project_scores,
        "project_rectification_stats": project_rectification_stats,
        "issue_by_module": [
            {"module_name": r[0], "count": r[1]} for r in module_issues
        ],
        "issue_list": [
            {
                "issue_id": iss.issue_id,
                "module_name": rec.module_name if rec else "",
                "item_name": iss.item_name,
                "description": iss.description or "",
                "severity": iss.severity or "",
            }
            for iss in db.query(Issue).filter(
                Issue.record_id.in_(db.query(completed_record_ids.c.record_id))
            ).all()
            for rec in [db.query(InspectionRecord).filter(InspectionRecord.record_id == iss.record_id).first()]
        ],
        "recent_tasks": [
            {
                "task_id": t.task_id,
                "project_name": t.project.name if t.project else "",
                "check_date": t.check_date,
                "status": t.status,
                "total_score": float(t.total_score) if t.total_score else None,
                "completed_modules": db.query(func.count(InspectionRecord.record_id)).filter(
                    InspectionRecord.task_id == t.task_id,
                    InspectionRecord.status == "completed"
                ).scalar() or 0,
                "total_modules": len(t.assignments) if hasattr(t, 'assignments') and t.assignments else 0,
            }
            for t in recent
        ],
        "llm_usage": {
            "monthly_calls": sum(s.call_count for s in usage_stats),
            "monthly_tokens": sum(s.total_tokens or 0 for s in usage_stats),
            "by_model": {
                s.model_name: {"calls": s.call_count, "tokens": s.total_tokens or 0}
                for s in usage_stats
            },
        },
    }
