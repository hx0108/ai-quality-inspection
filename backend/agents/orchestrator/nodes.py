"""
Orchestrator 节点函数
串联 Agent 2 → Agent 3 → Agent 4

节点:
  start_pipeline     → 初始化流程，验证任务状态
  run_scoring        → 调用 Agent 2 评分
  run_report         → 调用 Agent 3 报告生成
  track_rectification → 追踪 Agent 4 整改状态
  finalize           → 完成流程，汇总结果
"""
import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional

from database import SessionLocal
from models.models import InspectionTask, InspectionRecord, Rectification, Report
from config import settings
from core.logger import get_logger

logger = get_logger("orchestrator")

# ============================================================================
# 防双重执行锁：确保同一 task_id 同时只有一个 Orchestrator 实例在运行
# ============================================================================
_orchestrator_running_tasks: set = set()
_orchestrator_lock = threading.Lock()


async def start_pipeline(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    节点0: 初始化流程
    - 验证任务存在
    - 检查任务状态
    - 初始化计时
    - 检查是否需要跳过评分/报告（已由原触发机制执行）
    """
    task_id = state["task_id"]
    logger.info(f"[Orchestrator] 启动流程: {task_id}")

    start_time = time.time()
    state["started_at"] = datetime.now().isoformat()
    state["steps_completed"] = []
    state["current_step"] = "initializing"
    state["error"] = None
    state["error_detail"] = None

    # ========== 防双重执行检查 ==========
    with _orchestrator_lock:
        if task_id in _orchestrator_running_tasks:
            logger.warning(f"[Orchestrator] 任务正在被其他 Orchestrator 实例处理: {task_id}")
            state["error"] = "ALREADY_RUNNING"
            state["error_detail"] = "该任务正在被其他流程处理，请稍后重试"
            return state
        _orchestrator_running_tasks.add(task_id)

    db = SessionLocal()
    try:
        task = db.query(InspectionTask).filter(
            InspectionTask.task_id == task_id
        ).first()

        if not task:
            state["error"] = "TASK_NOT_FOUND"
            state["error_detail"] = f"任务不存在: {task_id}"
            logger.error(f"[Orchestrator] 任务不存在: {task_id}")
            return state

        # 获取项目信息
        state["project_id"] = task.project_id
        state["project_name"] = task.project.name if task.project else ""
        state["check_date"] = str(task.check_date) if task.check_date else ""
        state["task_status"] = task.status

        # ========== 检查评分是否已完成（由原触发机制执行） ==========
        scoring_done = False
        if task.total_score is not None and task.total_score > 0:
            # 评分已完成，直接使用已有结果
            state["scoring_completed"] = True
            state["total_score"] = task.total_score
            state["module_scores"] = _get_module_scores(db, task_id)
            state["steps_completed"].append("scoring")
            scoring_done = True
            logger.info(f"[Orchestrator] 评分已完成（跳过）: {task_id}, 总分={task.total_score}")
        else:
            # 检查 tracker 是否还有进行中的评分
            try:
                from core.scoring_tracker import scoring_tracker
                tracker_status = scoring_tracker.get_task_status(task_id)
                modules = tracker_status.get("modules", {})
                if modules:
                    all_done = all(m.get("status") == "completed" for m in modules.values())
                    if all_done:
                        state["scoring_completed"] = True
                        state["total_score"] = task.total_score or 0
                        state["module_scores"] = _get_module_scores(db, task_id)
                        state["steps_completed"].append("scoring")
                        scoring_done = True
                        logger.info(f"[Orchestrator] 评分已完成（从tracker跳过）: {task_id}")
            except Exception as e:
                logger.warning(f"[Orchestrator] 检查 tracker 失败: {e}")

        # ========== 检查报告是否已完成或正在生成 ==========
        if scoring_done:
            # 检查报告是否正在由原触发机制生成中
            try:
                from api.scoring import _triggering_tasks as scoring_triggering_tasks
                if task_id in scoring_triggering_tasks:
                    logger.info(f"[Orchestrator] 报告正在由原触发机制生成中（跳过）: {task_id}")
                    state["report_completed"] = True  # 跳过，避免重复生成
                    state["report_skipped"] = True   # 标记为跳过，等原机制完成
            except ImportError:
                pass

            if not state.get("report_completed"):
                existing_report = db.query(Report).filter(
                    Report.task_id == task_id
                ).order_by(Report.generated_at.desc()).first()

                if existing_report:
                    state["report_completed"] = True
                    state["report_id"] = existing_report.report_id
                    state["report_file_path"] = existing_report.file_path or ""
                    state["steps_completed"].append("report")
                    logger.info(f"[Orchestrator] 报告已存在（跳过）: {task_id}, report_id={existing_report.report_id}")

        # 检查是否有可评分的记录
        completed_records = db.query(InspectionRecord).filter(
            InspectionRecord.task_id == task_id,
            InspectionRecord.status == "completed"
        ).count()

        if completed_records == 0 and not scoring_done:
            state["error"] = "NO_COMPLETED_RECORDS"
            state["error_detail"] = "没有已完成的检查记录，无法进行评分"
            logger.error(f"[Orchestrator] 没有可评分的记录: {task_id}")
            return state

        state["completed_records_count"] = completed_records
        logger.info(f"[Orchestrator] 任务验证通过: {task_id}, 完成记录数: {completed_records}, "
                   f"评分已done={scoring_done}, 报告已done={state.get('report_completed', False)}")

        return state

    except Exception as e:
        logger.error(f"[Orchestrator] 初始化失败: {e}")
        state["error"] = "INIT_ERROR"
        state["error_detail"] = str(e)
        return state
    finally:
        db.close()


async def run_scoring(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    节点1: 运行 Agent 2 评分
    调用现有的 scoring graph
    """
    task_id = state["task_id"]
    logger.info(f"[Orchestrator] 开始评分: {task_id}")
    state["current_step"] = "scoring"

    # ========== 幂等检查：评分已完成则跳过 ==========
    if state.get("scoring_completed"):
        logger.info(f"[Orchestrator] 评分已完成（幂等跳过）: {task_id}")
        return state

    try:
        # 导入现有的 scoring graph
        from agents.scoring.graph import build_scoring_graph

        # 构建并运行评分图
        scoring_graph = build_scoring_graph()

        # 准备输入状态
        scoring_input = {
            "task_id": task_id,
            "records": [],  # 空列表表示由 graph 自己收集
            "standard_type": state.get("standard_type", "diecheng")
        }

        # 运行评分 graph
        logger.info(f"[Orchestrator] 调用 scoring graph: {task_id}")
        scoring_result = await scoring_graph.ainvoke(scoring_input)

        # 检查评分结果
        errors = scoring_result.get("errors", [])
        if errors:
            logger.warning(f"[Orchestrator] 评分有警告: {errors}")

        # 获取评分结果
        scoring_results = scoring_result.get("scoring_results", [])
        state["scoring_completed"] = True
        state["scoring_results"] = scoring_results
        state["steps_completed"].append("scoring")

        # 获取项目总分
        db = SessionLocal()
        try:
            task = db.query(InspectionTask).filter(
                InspectionTask.task_id == task_id
            ).first()
            state["total_score"] = task.total_score if task else 0
            state["module_scores"] = _get_module_scores(db, task_id)
        finally:
            db.close()

        logger.info(f"[Orchestrator] 评分完成: {task_id}, 总分: {state.get('total_score')}")

        return state

    except Exception as e:
        logger.error(f"[Orchestrator] 评分失败: {e}")
        import traceback
        traceback.print_exc()
        state["error"] = "SCORING_ERROR"
        state["error_detail"] = f"评分失败: {str(e)}"
        state["scoring_completed"] = False
        return state


async def run_report(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    节点2: 运行 Agent 3 报告生成
    调用现有的 report graph
    """
    task_id = state["task_id"]
    logger.info(f"[Orchestrator] 开始生成报告: {task_id}")
    state["current_step"] = "report"

    # ========== 幂等检查：报告已完成则跳过 ==========
    if state.get("report_completed"):
        logger.info(f"[Orchestrator] 报告已完成（幂等跳过）: {task_id}")
        return state

    # 如果评分失败或总分未计算，先计算总分
    if not state.get("total_score"):
        db = SessionLocal()
        try:
            task = db.query(InspectionTask).filter(
                InspectionTask.task_id == task_id
            ).first()
            state["total_score"] = task.total_score if task else 0
            state["module_scores"] = _get_module_scores(db, task_id)
        finally:
            db.close()

    try:
        # 导入现有的 report graph
        from agents.report.graph import build_report_graph

        # 构建并运行报告图
        report_graph = build_report_graph()

        # 准备输入状态
        report_input = {
            "task_id": task_id,
            "module_scores": state.get("module_scores", []),
            "modules_data": state.get("modules_data", {}),
            "total_score": state.get("total_score", 0),
            "project_name": state.get("project_name", ""),
            "check_date": state.get("check_date", ""),
            "issues_by_severity": state.get("issues_by_severity", {}),
            "issue_summary": state.get("issue_summary", {}),
            "modules_total": len(state.get("module_scores", [])),
            "modules_done": 0,
            "module_analyses": []
        }

        # 运行报告 graph
        logger.info(f"[Orchestrator] 调用 report graph: {task_id}")
        report_result = await report_graph.ainvoke(report_input)

        # 检查报告结果
        errors = report_result.get("errors", [])
        if errors:
            logger.warning(f"[Orchestrator] 报告生成有警告: {errors}")

        state["report_completed"] = True
        state["report_id"] = report_result.get("report_id", "")
        state["report_file_path"] = report_result.get("word_path", "")
        state["module_analyses"] = report_result.get("module_analyses", [])
        state["ai_full_report"] = report_result.get("ai_full_report", "")
        state["steps_completed"].append("report")

        logger.info(f"[Orchestrator] 报告生成完成: {task_id}, 报告ID: {state.get('report_id')}")

        return state

    except Exception as e:
        logger.error(f"[Orchestrator] 报告生成失败: {e}")
        import traceback
        traceback.print_exc()
        state["error"] = "REPORT_ERROR"
        state["error_detail"] = f"报告生成失败: {str(e)}"
        state["report_completed"] = False
        return state


async def track_rectification(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    节点3: 追踪 Agent 4 整改状态
    收集待整改问题，为后续整改流程做准备
    """
    task_id = state["task_id"]
    logger.info(f"[Orchestrator] 追踪整改状态: {task_id}")
    state["current_step"] = "rectification"

    db = SessionLocal()
    try:
        # 获取该任务下所有整改记录
        rectifications = db.query(Rectification).filter(
            Rectification.task_id == task_id
        ).all()

        # 统计各状态数量
        status_counts = {
            "pending": 0,       # 待整改
            "submitted": 0,     # 已提交待AI核查
            "ai_approved": 0,   # AI通过
            "ai_rejected": 0,   # AI驳回
            "pending_review": 0, # 待人工审核
            "approved": 0       # 已通过
        }

        pending_list = []
        for r in rectifications:
            if r.status in status_counts:
                status_counts[r.status] += 1

            # 收集待整改的问题
            if r.status == "pending" and r.issue:
                pending_list.append({
                    "rectification_id": r.rectification_id,
                    "issue_id": r.issue_id,
                    "item_name": r.issue.item_name if r.issue else "",
                    "description": r.issue.description if r.issue else "",
                    "severity": r.issue.severity if r.issue else "",
                    "location": r.issue.location if r.issue else ""
                })

        state["rectification_tracked"] = True
        state["rectification_status_counts"] = status_counts
        state["pending_rectifications"] = status_counts["pending"]
        state["completed_rectifications"] = status_counts["approved"] + status_counts["ai_approved"]
        state["pending_rectification_list"] = pending_list[:10]  # 最多10条
        state["steps_completed"].append("rectification")

        logger.info(f"[Orchestrator] 整改追踪完成: 待整改={status_counts['pending']}, "
                   f"已完成={status_counts['approved'] + status_counts['ai_approved']}")

        return state

    except Exception as e:
        logger.error(f"[Orchestrator] 整改追踪失败: {e}")
        state["error"] = "RECTIFICATION_TRACK_ERROR"
        state["error_detail"] = f"整改追踪失败: {str(e)}"
        return state
    finally:
        db.close()


async def finalize(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    节点4: 完成流程
    - 汇总所有结果
    - 计算总耗时
    - 释放运行锁
    """
    task_id = state["task_id"]
    logger.info(f"[Orchestrator] 完成流程: {task_id}")
    state["current_step"] = "done"

    # ========== 释放运行锁 ==========
    with _orchestrator_lock:
        _orchestrator_running_tasks.discard(task_id)

    # 计算耗时
    if state.get("started_at"):
        start = datetime.fromisoformat(state["started_at"])
        duration = (datetime.now() - start).total_seconds()
        state["duration_seconds"] = round(duration, 2)
        state["completed_at"] = datetime.now().isoformat()

    # 汇总结果
    state["pipeline_result"] = {
        "task_id": task_id,
        "project_name": state.get("project_name", ""),
        "check_date": state.get("check_date", ""),
        "scoring": {
            "completed": state.get("scoring_completed", False),
            "total_score": state.get("total_score", 0),
            "module_count": len(state.get("module_scores", []))
        },
        "report": {
            "completed": state.get("report_completed", False),
            "report_id": state.get("report_id", ""),
            "file_path": state.get("report_file_path", "")
        },
        "rectification": {
            "tracked": state.get("rectification_tracked", False),
            "pending_count": state.get("pending_rectifications", 0),
            "completed_count": state.get("completed_rectifications", 0)
        },
        "steps_completed": state.get("steps_completed", []),
        "duration_seconds": state.get("duration_seconds", 0),
        "error": state.get("error"),
        "error_detail": state.get("error_detail")
    }

    state["steps_completed"].append("finalize")

    logger.info(f"[Orchestrator] 流程完成: {task_id}, "
               f"耗时={state.get('duration_seconds')}s, "
               f"评分={state.get('scoring_completed')}, "
               f"报告={state.get('report_completed')}")

    return state


def _get_module_scores(db, task_id: str) -> List[Dict[str, Any]]:
    """获取各模块得分"""
    from models.models import ScoringResult, InspectionRecord

    results = db.query(ScoringResult).join(
        InspectionRecord, ScoringResult.record_id == InspectionRecord.record_id
    ).filter(InspectionRecord.task_id == task_id).all()

    modules = {}
    for r in results:
        if r.module_name not in modules:
            modules[r.module_name] = {"raw_sum": 0, "weight_sum": 0}
        modules[r.module_name]["raw_sum"] += float(r.weighted_score)
        modules[r.module_name]["weight_sum"] += float(r.weight)

    module_scores = []
    for module_name, data in modules.items():
        if data["weight_sum"] > 0:
            max_score = 5 * data["weight_sum"]
            pct = (data["raw_sum"] / max_score) * 100
            module_scores.append({
                "module_name": module_name,
                "module_pct_score": round(pct, 2),
                "weight_ratio": settings.MODULE_WEIGHTS.get(module_name, 0)
            })

    return module_scores


def should_run_report(state: Dict[str, Any]) -> bool:
    """条件边：评分成功后是否运行报告"""
    return state.get("scoring_completed", False) and not state.get("error")


def should_track_rectification(state: Dict[str, Any]) -> bool:
    """条件边：报告成功后是否追踪整改"""
    return state.get("report_completed", False) and not state.get("error")


async def check_human_review_gate(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    可选节点: Human-in-the-Loop 审核门控
    检查评分结果中是否有低置信度项需要人工审核
    仅在 ENABLE_HUMAN_REVIEW_GATE=True 时生效
    """
    task_id = state["task_id"]

    # 配置开关检查
    if not settings.ENABLE_HUMAN_REVIEW_GATE:
        state["needs_human_review"] = False
        return state

    logger.info(f"[Orchestrator] 检查人工审核门控: {task_id}")

    try:
        from models.models import ScoringResult
        db = SessionLocal()
        try:
            threshold = settings.HUMAN_REVIEW_CONFIDENCE_THRESHOLD
            low_conf_count = db.query(ScoringResult).filter(
                ScoringResult.task_id == task_id,
                ScoringResult.needs_human_review == True,
                ScoringResult.human_reviewed == False,
            ).count()

            if low_conf_count > 0:
                state["needs_human_review"] = True
                state["review_count"] = low_conf_count
                state["current_step"] = "pending_review"
                logger.info(f"[Orchestrator] 需人工审核: {task_id}, {low_conf_count}项低置信度")

                # SSE 通知
                try:
                    from core.event_bus import event_bus
                    await event_bus.publish(f"task:{task_id}", {
                        "type": "review_required",
                        "review_count": low_conf_count,
                        "message": f"有 {low_conf_count} 项评分需要人工审核",
                    })
                except Exception:
                    pass
            else:
                state["needs_human_review"] = False
                logger.info(f"[Orchestrator] 无需人工审核: {task_id}")

        finally:
            db.close()
    except Exception as e:
        logger.warning(f"[Orchestrator] 审核门控检查失败（继续流程）: {e}")
        state["needs_human_review"] = False

    return state


def should_wait_for_review(state: Dict[str, Any]) -> str:
    """条件边：是否需要等待人工审核"""
    if state.get("needs_human_review"):
        return "wait_for_review"
    return "run_report"
