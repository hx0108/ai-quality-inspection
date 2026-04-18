"""
Orchestrator API
一键执行完整流程: Agent 2 → Agent 3 → Agent 4
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from database import get_db
from models.models import User, InspectionTask
from api.deps import get_current_user
from core.logger import get_logger

logger = get_logger("orchestrator_api")

router = APIRouter(tags=["Orchestrator"])


class RunPipelineRequest(BaseModel):
    """执行流水线请求"""
    task_id: str
    skip_scoring: bool = False  # 跳过评分（已有评分结果时）
    skip_report: bool = False   # 跳过报告生成


class PipelineStatusResponse(BaseModel):
    """流水线状态响应"""
    task_id: str
    status: str  # running, completed, failed
    current_step: str
    steps_completed: list
    scoring_completed: bool = False
    report_completed: bool = False
    total_score: Optional[float] = None
    report_id: Optional[str] = None
    error: Optional[str] = None
    error_detail: Optional[str] = None
    duration_seconds: Optional[float] = None


@router.post("/run", summary="一键执行完整流程")
async def run_full_pipeline(
    request: RunPipelineRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    一键执行完整流程

    流程: Agent 2 (评分) → Agent 3 (报告) → Agent 4 (整改追踪)

    - 自动调用现有的 scoring graph 和 report graph
    - 追踪整改状态
    - 返回完整执行结果
    """
    task_id = request.task_id
    logger.info(f"[Orchestrator API] 收到请求: task_id={task_id}, user={current_user.username}")

    # 验证任务存在
    task = db.query(InspectionTask).filter(
        InspectionTask.task_id == task_id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    try:
        # 导入 orchestrator
        from agents.orchestrator.graph import get_orchestrator_graph

        # 获取 graph
        orchestrator = get_orchestrator_graph()

        # 准备输入状态
        input_state = {
            "task_id": task_id,
            "standard_type": task.standard_type or "diecheng"
        }

        # 运行流水线（同步等待完成）
        logger.info(f"[Orchestrator API] 启动流水线: {task_id}")
        result = await orchestrator.ainvoke(input_state)

        # 提取结果
        pipeline_result = result.get("pipeline_result", {})
        error = result.get("error")
        duration = result.get("duration_seconds")

        if error:
            logger.error(f"[Orchestrator API] 流水线失败: {task_id}, error={error}")
            return {
                "success": False,
                "task_id": task_id,
                "status": "failed",
                "current_step": result.get("current_step", "unknown"),
                "error": error,
                "error_detail": result.get("error_detail"),
                "duration_seconds": duration
            }

        logger.info(f"[Orchestrator API] 流水线完成: {task_id}, "
                   f"耗时={duration}s, 总分={pipeline_result.get('scoring', {}).get('total_score')}")

        return {
            "success": True,
            "task_id": task_id,
            "status": "completed",
            "current_step": "done",
            "steps_completed": pipeline_result.get("steps_completed", []),
            "scoring": {
                "completed": pipeline_result.get("scoring", {}).get("completed", False),
                "total_score": pipeline_result.get("scoring", {}).get("total_score"),
                "module_count": pipeline_result.get("scoring", {}).get("module_count", 0)
            },
            "report": {
                "completed": pipeline_result.get("report", {}).get("completed", False),
                "report_id": pipeline_result.get("report", {}).get("report_id"),
                "file_path": pipeline_result.get("report", {}).get("file_path")
            },
            "rectification": {
                "tracked": pipeline_result.get("rectification", {}).get("tracked", False),
                "pending_count": pipeline_result.get("rectification", {}).get("pending_count", 0),
                "completed_count": pipeline_result.get("rectification", {}).get("completed_count", 0)
            },
            "duration_seconds": duration
        }

    except Exception as e:
        logger.error(f"[Orchestrator API] 流水线异常: {task_id}, error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail="流水线执行失败，请稍后重试")


@router.get("/status/{task_id}", summary="获取流水线状态")
async def get_pipeline_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取任务流水线执行状态"""
    task = db.query(InspectionTask).filter(
        InspectionTask.task_id == task_id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    # 从数据库获取最新状态
    return {
        "task_id": task_id,
        "task_status": task.status,
        "total_score": task.total_score,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None
    }


@router.post("/scoring-only", summary="仅执行评分")
async def run_scoring_only(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    仅执行 Agent 2 评分阶段

    适用于:
    - 已有检查数据，只需评分
    - 报告生成失败后单独重试评分
    """
    task = db.query(InspectionTask).filter(
        InspectionTask.task_id == task_id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    try:
        from agents.orchestrator.nodes import run_scoring

        input_state = {
            "task_id": task_id,
            "standard_type": task.standard_type or "diecheng"
        }

        result = await run_scoring(input_state)

        if result.get("error"):
            return {
                "success": False,
                "error": result["error"],
                "error_detail": result.get("error_detail")
            }

        return {
            "success": True,
            "scoring_completed": True,
            "total_score": result.get("total_score"),
            "module_scores": result.get("module_scores", [])
        }

    except Exception as e:
        logger.error(f"[Orchestrator API] 评分失败: {task_id}, error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail="评分执行失败，请稍后重试")


@router.post("/report-only", summary="仅执行报告生成")
async def run_report_only(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    仅执行 Agent 3 报告生成阶段

    适用于:
    - 评分已完成，单独重试报告生成
    - 只想生成/更新报告
    """
    task = db.query(InspectionTask).filter(
        InspectionTask.task_id == task_id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    if not task.total_score:
        raise HTTPException(status_code=400, detail="请先完成评分")

    try:
        from agents.orchestrator.nodes import run_report

        input_state = {
            "task_id": task_id,
            "total_score": task.total_score,
            "project_name": task.project.name if task.project else "",
            "check_date": str(task.check_date) if task.check_date else ""
        }

        result = await run_report(input_state)

        if result.get("error"):
            return {
                "success": False,
                "error": result["error"],
                "error_detail": result.get("error_detail")
            }

        return {
            "success": True,
            "report_completed": True,
            "report_id": result.get("report_id"),
            "file_path": result.get("report_file_path")
        }

    except Exception as e:
        logger.error(f"[Orchestrator API] 报告生成失败: {task_id}, error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail="报告生成失败，请稍后重试")


from sqlalchemy.orm import Session
