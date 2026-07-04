"""
评分 API
逐模块自动评分、并发执行、支持人工修改
使用 qwen-plus 进行AI评分
"""
import json
import asyncio
import threading
import uuid as _uuid
import io
import os
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill

from database import get_db, SessionLocal
from models.models import User, InspectionTask, InspectionRecord, Issue, ScoringResult, Photo
from api.deps import get_current_user, check_role
from config import settings
from core.llm_client import QwenClient
from core.scoring_tracker import scoring_tracker
from core.scoring_memory import build_scoring_context
from core.long_memory import get_memory_context_for_scoring
from core.short_memory import ShortMemory
from core.logger import get_logger
from api.tasks import load_template_items

logger = get_logger("scoring")

router = APIRouter()

# 并发控制：最多2个模块同时评分（降低DB写压力，避免阻塞其他检查员）
_scoring_semaphore = threading.Semaphore(2)

# 防并发触发：记录正在评分中的 task_id
_scoring_running_tasks: set = set()
_scoring_tasks_lock = threading.Lock()

# 评分结果内存缓存（task_id -> 完整结果dict）
_scoring_results_cache: dict = {}
_cache_lock = threading.Lock()


# ==================== 请求/响应模型 ====================
class ScoringStart(BaseModel):
    task_id: str


class ScoringResultItem(BaseModel):
    item_id: str
    item_name: str
    score: float
    weight: float
    weighted_score: float
    scoring_basis: str
    improvement_suggestion: str
    is_skipped: bool
    is_fallback: bool = False


class ModuleScore(BaseModel):
    module_name: str
    module_pct_score: float
    items: List[ScoringResultItem]


class ScoreEditRequest(BaseModel):
    score: float  # 0-5
    scoring_basis: Optional[str] = None
    improvement_suggestion: Optional[str] = None
    edit_reason: Optional[str] = None  # 人工修改原因分类


# ==================== 核心评分逻辑 ====================
def trigger_single_module_scoring(task_id: str, module_name: str, record_id: str):
    """
    在后台线程中评分单个模块
    - 使用信号量控制并发数（最多2个同时评分）
    - 180秒超时保护（qwen3.5-plus 单批评分约15-25秒，3批约60秒，预留余量）
    - 评分完成后自动更新项目总分
    """
    # 先等待2秒，让检查完成API响应先返回，避免阻塞其他检查员
    import time
    time.sleep(2)

    _scoring_semaphore.acquire()
    scoring_tracker.init_task(task_id)
    scoring_tracker.set_module_status(task_id, module_name, "scoring")
    logger.info(f"开始评分模块: {module_name} (task={task_id})")

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # 重置 QwenClient 共享 httpx 客户端，避免跨 event loop 问题
        from core.llm_client import QwenClient
        QwenClient.reset_client()
        try:
            # 180秒超时（qwen3.5-plus 单批约15-25秒，3批+网络波动需预留足够时间）
            loop.run_until_complete(
                asyncio.wait_for(
                    _score_module_async(task_id, module_name, record_id),
                    timeout=180.0
                )
            )
            scoring_tracker.set_module_status(task_id, module_name, "completed")
            logger.info(f"完成评分模块: {module_name}")
        except asyncio.TimeoutError:
            logger.warning(f"评分超时: {module_name} (180秒)")
            scoring_tracker.set_module_status(task_id, module_name, "failed", "评分超时(180秒)")
            _save_timeout_defaults(SessionLocal(), task_id, module_name, record_id)
        except Exception as e:
            logger.error(f"评分失败 {module_name}: {e}")
            import traceback
            traceback.print_exc()
            scoring_tracker.set_module_status(task_id, module_name, "failed", str(e))
        finally:
            loop.close()

        # 每次评分后都重算项目总分
        try:
            _compute_and_save_total_score(task_id)
        except Exception as e:
            logger.error(f"计算总分失败: {e}")

        # 使缓存失效（评分数据已变化）
        _invalidate_scoring_cache(task_id)

        # 检查是否所有模块都已完成评分，如果是则自动触发报告生成
        try:
            _check_and_trigger_report(task_id)
        except Exception as e:
            logger.error(f"检查报告触发失败: {e}")
    finally:
        _scoring_semaphore.release()


# 线程安全的报告触发控制
_report_trigger_lock = threading.Lock()
_triggering_tasks = set()  # 正在生成报告的 task_id 集合


def _check_and_trigger_report(task_id: str):
    """
    唯一触发点：当所有模块评分完成后，自动触发 Agent 3 报告生成。
    使用线程锁 + 集合确保只触发一次。
    """
    from models.models import Report as ReportModel

    with _report_trigger_lock:
        if task_id in _triggering_tasks:
            return  # 已有线程在处理此任务的报告

        db = SessionLocal()
        try:
            task = db.query(InspectionTask).filter(InspectionTask.task_id == task_id).first()
            if not task:
                return

            # 如果任务卡在 reporting 状态但没有报告，根据实际进度重置
            if task.status == "reporting":
                existing_report = db.query(ReportModel).filter(ReportModel.task_id == task_id).first()
                if not existing_report:
                    from api.tasks import MODULE_NAMES
                    done_count = db.query(InspectionRecord).filter(
                        InspectionRecord.task_id == task_id,
                        InspectionRecord.status == "completed"
                    ).count()
                    task.status = "completed" if done_count >= len(MODULE_NAMES) else "in_progress"
                    logger.warning(f"_check_and_trigger_report: 任务 {task_id} 卡在 reporting，重置为 {task.status}")
                    db.commit()

            # 已有报告 → 跳过
            existing_report = db.query(ReportModel).filter(ReportModel.task_id == task_id).first()
            if existing_report:
                return

            # 检查所有模板模块是否全部完成（而非仅已分配模块）
            from api.tasks import MODULE_NAMES
            total_modules = len(MODULE_NAMES)

            completed_records = db.query(InspectionRecord).filter(
                InspectionRecord.task_id == task_id,
                InspectionRecord.status == "completed"
            ).all()

            if total_modules == 0 or len(completed_records) < total_modules:
                return  # 还有模块未完成检查，不触发报告

            all_scored = True
            for record in completed_records:
                count = db.query(ScoringResult).filter(
                    ScoringResult.record_id == record.record_id
                ).count()
                if count == 0:
                    all_scored = False
                    break

            if not all_scored:
                return  # 还有模块未评分

            # 标记为正在生成，防止其他线程重复触发
            _triggering_tasks.add(task_id)
            task.status = "reporting"
            db.commit()

        except Exception as e:
            logger.error(f"_check_and_trigger_report 检查失败: {e}")
            return
        finally:
            db.close()

    # 在锁外启动报告生成线程
    def _run_report():
        import asyncio as _asyncio
        loop = _asyncio.new_event_loop()
        _asyncio.set_event_loop(loop)
        try:
            from agents.report import build_report_graph

            graph = build_report_graph()
            result = loop.run_until_complete(graph.ainvoke({
                "task_id": task_id,
                "module_analyses": [],
                "errors": [],
                "modules_done": 0,
                "modules_total": 0,
            }))

            if result.get("errors"):
                logger.warning(f"报告生成有错误: {result['errors']}")

            # 更新任务状态
            db2 = SessionLocal()
            try:
                t = db2.query(InspectionTask).filter(InspectionTask.task_id == task_id).first()
                if t:
                    t.status = "completed"
                    db2.commit()
            finally:
                db2.close()

            logger.info(f"自动报告生成完成: {task_id}")

            # 预热缓存：在后台构建评分结果，用户点击时秒返回
            try:
                db3 = SessionLocal()
                try:
                    _build_scoring_results(task_id, db3)
                    logger.debug(f"评分结果已预缓存: {task_id}")
                finally:
                    db3.close()
            except Exception as e:
                logger.error(f"预缓存失败: {e}")
        except Exception as e:
            logger.error(f"自动报告生成失败: {e}")
            import traceback
            traceback.print_exc()
            db2 = SessionLocal()
            try:
                t = db2.query(InspectionTask).filter(InspectionTask.task_id == task_id).first()
                if t:
                    t.status = "reporting_failed"
                    db2.commit()
            finally:
                db2.close()
        finally:
            loop.close()
            with _report_trigger_lock:
                _triggering_tasks.discard(task_id)

    t = threading.Thread(target=_run_report, daemon=True)
    t.start()


def _save_timeout_defaults(db: Session, task_id: str, module_name: str, record_id: str):
    """超时时保存默认分数（问题项3分，合格项5分）"""
    try:
        # 先清除旧结果
        db.query(ScoringResult).filter(
            ScoringResult.record_id == record_id,
            ScoringResult.module_name == module_name
        ).delete()
        db.commit()

        # 获取问题列表
        issues = db.query(Issue).filter(
            Issue.record_id == record_id,
            Issue.module_name == module_name
        ).all()
        issue_item_ids = set(i.item_id for i in issues)

        # 获取模板（使用任务的 standard_type）
        record = db.query(InspectionRecord).filter(InspectionRecord.record_id == record_id).first()
        standard_type = record.task.standard_type if record and record.task else "diecheng"
        template_items = load_template_items(module_name, standard_type)
        if not template_items:
            return

        today = datetime.now().strftime("%Y%m%d")
        count = db.query(ScoringResult).filter(
            ScoringResult.scoring_id.like(f"SCR-{today}-%")
        ).count()

        for i, item in enumerate(template_items):
            score = 3.0 if item["item_id"] in issue_item_ids else 5.0
            weight = item.get("weight", 0.01)
            scoring_id = f"SCR-{_uuid.uuid4().hex[:12]}"
            result = ScoringResult(
                scoring_id=scoring_id,
                record_id=record_id,
                module_name=module_name,
                item_id=item["item_id"],
                item_name=item.get("item_name", ""),
                score=score,
                weight=weight,
                weighted_score=score * weight,
                scoring_basis="评分超时，使用默认分数",
                improvement_suggestion="",
                is_skipped=False
            )
            db.add(result)
        db.commit()
        logger.info(f"超时默认分数已保存: {module_name}")
    except Exception as e:
        logger.error(f"保存超时默认分数失败: {e}")


def _compute_and_save_total_score(task_id: str):
    """
    计算项目总分
    - 已评分模块：按实际分数计算
    - 未评分模块：按100%满分计算
    """
    db = SessionLocal()
    try:
        task = db.query(InspectionTask).filter(InspectionTask.task_id == task_id).first()
        if not task:
            return

        results = db.query(ScoringResult).join(
            InspectionRecord, ScoringResult.record_id == InspectionRecord.record_id
        ).filter(InspectionRecord.task_id == task_id).all()

        # 按模块分组
        modules_data = {}
        for r in results:
            if r.module_name not in modules_data:
                modules_data[r.module_name] = {"raw_score_sum": 0, "weight_sum": 0}
            modules_data[r.module_name]["raw_score_sum"] += float(r.weighted_score)
            modules_data[r.module_name]["weight_sum"] += float(r.weight)

        # 更新已评分模块的百分制得分
        for r in results:
            data = modules_data.get(r.module_name)
            if data and data["weight_sum"] > 0:
                r.module_pct_score = (data["raw_score_sum"] / (5 * data["weight_sum"])) * 100

        # 计算项目总分：已评分模块的加权得分之和
        project_total = 0
        for module_name, module_weight in settings.MODULE_WEIGHTS.items():
            data = modules_data.get(module_name)
            if data and data["weight_sum"] > 0:
                max_score = 5 * data["weight_sum"]
                module_pct = (data["raw_score_sum"] / max_score * 100)
                project_total += module_pct * module_weight

        task.total_score = round(project_total, 2)
        db.commit()
    finally:
        db.close()


async def _score_module_async(
    task_id: str,
    module_name: str,
    record_id: str
):
    """异步评分核心逻辑"""
    db = SessionLocal()

    try:
        # 获取检查记录
        record = db.query(InspectionRecord).filter(InspectionRecord.record_id == record_id).first()
        if not record:
            logger.warning(f"记录不存在: {record_id}")
            return

        # 清除该模块的旧评分结果
        deleted = db.query(ScoringResult).filter(
            ScoringResult.record_id == record_id,
            ScoringResult.module_name == module_name
        ).delete()
        if deleted > 0:
            logger.info(f"清除旧评分: {module_name} ({deleted}条)")
            db.commit()

        # 获取该模块的问题
        issues = db.query(Issue).filter(
            Issue.record_id == record_id,
            Issue.module_name == module_name
        ).all()

        issues_by_item = {}
        for issue in issues:
            if issue.item_id not in issues_by_item:
                issues_by_item[issue.item_id] = []
            issues_by_item[issue.item_id].append({
                "description": issue.description,
                "severity": issue.severity,
                "location": issue.location
            })

        # 从模板获取检查项（传入 standard_type）
        standard_type = record.task.standard_type if record.task else "diecheng"
        template_items = load_template_items(module_name, standard_type)
        if not template_items:
            logger.warning(f"无模板数据: {module_name}")
            return

        # 分离合格项和有问题项
        qualified_items = []
        problem_items = []

        for item in template_items:
            item_id = item.get("item_id")
            item_issues = issues_by_item.get(item_id, [])
            entry = {
                "item_id": item_id,
                "item_name": item.get("item_name", ""),
                "check_standard": item.get("check_standard", ""),
                "check_method": item.get("check_method", ""),
                "scoring_rule": item.get("scoring_rule", "完全符合5分"),
                "weight": item.get("weight", 0.01),
                "issues": item_issues,
                "is_skipped": False
            }

            if not item_issues:
                qualified_items.append(entry)
            else:
                problem_items.append(entry)

        logger.info(f"{module_name}: 合格{len(qualified_items)}项(直接满分), 有问题{len(problem_items)}项(AI评分)")

        # 合格项直接给满分
        results = []
        for item in qualified_items:
            results.append({
                "item_id": item["item_id"],
                "item_name": item["item_name"],
                "score": 5,
                "scoring_basis": "检查合格，无问题发现，给予满分5分",
                "improvement_suggestion": ""
            })

        # 有问题项调用AI评分
        if problem_items and settings.DASHSCOPE_API_KEY:
            # 构建记忆上下文（RAG + 历史评分参考）
            memory_context = _build_memory_context(
                task_id=task_id,
                project_id=record.project_id,
                module_name=module_name,
                problem_items=problem_items
            )

            llm = QwenClient()
            logger.info(f"AI评分: {module_name} ({len(problem_items)}项有问题)")
            ai_results = await llm.score_module(module_name, problem_items, memory_context=memory_context)
            logger.info(f"AI返回: {module_name} ({len(ai_results)}项)")
            results.extend(ai_results)
        elif problem_items:
            # 无API Key，使用简单规则评分
            for item in problem_items:
                issue_count = len(item["issues"])
                score = max(0, 5 - issue_count)
                results.append({
                    "item_id": item["item_id"],
                    "item_name": item["item_name"],
                    "score": score,
                    "scoring_basis": f"发现{issue_count}个问题，扣{issue_count}分",
                    "improvement_suggestion": ""
                })

        # 合并所有检查项
        all_items = qualified_items + problem_items

        # 保存评分结果（分批提交，每20条commit一次，减少DB锁持有时间）
        batch_size = 20
        for i, item_result in enumerate(results):
            scoring_id = f"SCR-{_uuid.uuid4().hex[:12]}"

            # 优先使用AI评分时注入的原始数据，兼容旧逻辑
            item_id = item_result.get("item_id")
            item_name = item_result.get("item_name", "")
            score = item_result.get("score", 5)

            original_item = next((x for x in all_items if x["item_id"] == item_id), {}) if item_id else {}

            weight = item_result.get("_weight") or original_item.get("weight", 0.01)
            check_standard = item_result.get("_check_standard") or original_item.get("check_standard", "")
            check_method = item_result.get("_check_method") or original_item.get("check_method", "")
            scoring_rule = item_result.get("_scoring_rule") or original_item.get("scoring_rule", "")
            if not item_name:
                item_name = original_item.get("item_name", "")

            result = ScoringResult(
                scoring_id=scoring_id,
                record_id=record_id,
                module_name=module_name,
                item_id=item_id,
                item_name=item_name,
                score=score,
                weight=weight,
                weighted_score=score * weight,
                scoring_basis=item_result.get("scoring_basis", ""),
                improvement_suggestion=item_result.get("improvement_suggestion", ""),
                check_standard=check_standard,
                check_method=check_method,
                scoring_rule=scoring_rule,
                is_skipped=item_result.get("is_skipped", False)
            )
            db.add(result)

            # 每 batch_size 条提交一次，释放写锁
            if (i + 1) % batch_size == 0:
                db.commit()

        # 提交剩余的记录
        db.commit()
        logger.info(f"保存完成: {module_name} ({len(results)}条)")

    except Exception as e:
        logger.error(f"评分异常 {module_name}: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


# ==================== API 端点 ====================
@router.post("/start/{task_id}", summary="手动启动AI评分")
async def start_scoring(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "site_supervisor"]))
):
    """
    手动启动AI评分
    - 对所有已完成但未评分的模块启动并发评分
    """
    # 防并发：检查是否已有评分任务在运行
    with _scoring_tasks_lock:
        if task_id in _scoring_running_tasks:
            raise HTTPException(status_code=409, detail="评分任务正在进行中，请勿重复点击")
        _scoring_running_tasks.add(task_id)

    try:
        task = db.query(InspectionTask).filter(InspectionTask.task_id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        records = db.query(InspectionRecord).filter(
            InspectionRecord.task_id == task_id,
            InspectionRecord.status == "completed"
        ).all()

        if not records:
            raise HTTPException(status_code=400, detail="没有已完成的检查记录")

        scoring_tracker.init_task(task_id)

        # 检查哪些模块已有评分，跳过已完成的
        skipped_modules = []
        modules_to_score = []

        for record in records:
            existing_count = db.query(ScoringResult).filter(
                ScoringResult.record_id == record.record_id
            ).count()
            if existing_count > 0:
                skipped_modules.append(record.module_name)
                scoring_tracker.set_module_status(task_id, record.module_name, "completed")
            else:
                modules_to_score.append(record)

        if skipped_modules:
            logger.info(f"跳过已评分模块: {skipped_modules}")

        # 使用 LangGraph 并行评分
        if modules_to_score:
            import asyncio as _asyncio

            def _run_scoring_graph():
                loop = _asyncio.new_event_loop()
                _asyncio.set_event_loop(loop)
                try:
                    from agents.scoring import build_scoring_graph
                    graph = build_scoring_graph()
                    loop.run_until_complete(graph.ainvoke({
                        "task_id": task_id,
                        "records": [],
                        "standard_type": "diecheng",
                        "scoring_results": [],
                        "completed_modules": [],
                        "errors": [],
                    }))
                except Exception as e:
                    logger.error(f"LangGraph 评分失败: {e}")
                finally:
                    loop.close()
                    # 评分完成后移除标记
                    with _scoring_tasks_lock:
                        _scoring_running_tasks.discard(task_id)

            t = threading.Thread(target=_run_scoring_graph, daemon=True)
            t.start()

        else:
            # 没有需要评分的模块，也要移除标记
            with _scoring_tasks_lock:
                _scoring_running_tasks.discard(task_id)

        return {
            "message": "AI评分任务已启动" if modules_to_score else "所有模块已有评分结果",
            "task_id": task_id,
            "total_modules": len(records),
            "skipped_modules": skipped_modules,
            "scoring_modules": [r.module_name for r in modules_to_score],
            "scoring_method": "Qwen-plus AI评分"
        }
    except HTTPException:
        with _scoring_tasks_lock:
            _scoring_running_tasks.discard(task_id)
        raise


@router.get("/status/{task_id}", summary="查询评分进度")
async def get_scoring_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """查询评分进度"""
    completed_records = db.query(InspectionRecord).filter(
        InspectionRecord.task_id == task_id,
        InspectionRecord.status == "completed"
    ).all()
    completed_modules = set(r.module_name for r in completed_records)

    # 统计已评分的结果（单次批量查询替代 N+1）
    scored_module_names = set()
    current_scoring_module = None
    if completed_records:
        record_ids = [r.record_id for r in completed_records]
        scored_rows = db.query(ScoringResult.record_id).filter(
            ScoringResult.record_id.in_(record_ids)
        ).distinct().all()
        scored_record_ids = {r[0] for r in scored_rows}
        for record in completed_records:
            if record.record_id in scored_record_ids:
                scored_module_names.add(record.module_name)

    # 从 tracker 获取正在评分的模块
    tracker_status = scoring_tracker.get_task_status(task_id)
    modules_detail = tracker_status.get("modules", {})
    all_done = True
    for module_name, pstatus in modules_detail.items():
        if pstatus.get("status") == "scoring":
            current_scoring_module = module_name
            all_done = False
        elif pstatus.get("status") not in ("completed", None):
            all_done = False

    is_complete = len(scored_module_names) >= len(completed_modules) and len(completed_modules) > 0 and all_done

    return {
        "task_id": task_id,
        "total_modules": len(completed_modules),
        "scored_modules": len(scored_module_names),
        "progress": f"{len(scored_module_names)}/{len(completed_modules)}",
        "is_complete": is_complete,
        "current_module": current_scoring_module,
        "modules_detail": modules_detail
    }


@router.get("/module-status/{task_id}", summary="获取每个模块的检查+评分状态")
async def get_module_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取每个模块的检查状态和评分状态"""
    task = db.query(InspectionTask).filter(InspectionTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 获取所有检查记录
    records = db.query(InspectionRecord).filter(
        InspectionRecord.task_id == task_id
    ).all()
    record_map = {r.module_name: r for r in records}

    # 获取评分进度
    tracker_status = scoring_tracker.get_task_status(task_id)
    modules_detail = tracker_status.get("modules", {})

    # 获取所有评分结果（按模块分组）
    scoring_results = db.query(ScoringResult).join(
        InspectionRecord, ScoringResult.record_id == InspectionRecord.record_id
    ).filter(InspectionRecord.task_id == task_id).all()

    scored_modules = {}
    for r in scoring_results:
        if r.module_name not in scored_modules:
            scored_modules[r.module_name] = {"count": 0, "pct_score": float(r.module_pct_score) if r.module_pct_score else None}
        scored_modules[r.module_name]["count"] += 1

    modules = []
    scored_count = 0
    current_total = 0
    scored_total_weight = 0

    for module_name, module_weight in settings.MODULE_WEIGHTS.items():
        record = record_map.get(module_name)
        scored_info = scored_modules.get(module_name)

        # 检查状态
        if record:
            inspection_status = record.status
        else:
            inspection_status = "not_started"

        # 评分状态
        tracker_module = modules_detail.get(module_name, {})
        tracker_status_val = tracker_module.get("status")

        if scored_info and scored_info["count"] > 0:
            scoring_status = "completed"
            score_count = scored_info["count"]
            pct_score = scored_info.get("pct_score")
            scored_count += 1
        elif tracker_status_val == "scoring":
            scoring_status = "scoring"
            score_count = 0
            pct_score = None
        elif tracker_status_val == "failed":
            scoring_status = "failed"
            score_count = 0
            pct_score = None
        else:
            scoring_status = "pending"
            score_count = 0
            pct_score = None

        # 模块贡献分数（只按已评分模块计算）
        if pct_score is not None:
            current_total += pct_score * module_weight
            scored_total_weight += module_weight

        modules.append({
            "module_name": module_name,
            "weight": module_weight,
            "inspection_status": inspection_status,
            "scoring_status": scoring_status,
            "score_count": score_count,
            "pct_score": round(pct_score, 2) if pct_score is not None else None
        })

    # 项目总分 = Σ(模块百分制得分 × 模块权重)
    current_total = current_total  # 已是加权后的总分，不需要再归一化

    return {
        "task_id": task_id,
        "modules": modules,
        "scored_module_count": scored_count,
        "total_module_count": len(settings.MODULE_WEIGHTS),
        "current_total_score": round(current_total, 2)
    }


def _build_scoring_results(task_id: str, db: Session) -> dict:
    """构建评分结果（含缓存）"""
    # 命中内存缓存 → 直接返回（零DB查询）
    with _cache_lock:
        if task_id in _scoring_results_cache:
            return _scoring_results_cache[task_id]

    task = db.query(InspectionTask).filter(InspectionTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    results = db.query(ScoringResult).join(
        InspectionRecord, ScoringResult.record_id == InspectionRecord.record_id
    ).filter(InspectionRecord.task_id == task_id).all()

    # 获取所有检查记录的 record_id
    record_ids = list(set(r.record_id for r in results))

    # 批量获取所有相关的 issues 和 photos
    all_issues = db.query(Issue).filter(
        Issue.record_id.in_(record_ids)
    ).all() if record_ids else []

    issue_ids = [i.issue_id for i in all_issues]
    all_photos = db.query(Photo).filter(
        Photo.issue_id.in_(issue_ids)
    ).all() if issue_ids else []

    # 建立 issue_id -> photos 映射
    photos_by_issue = {}
    for p in all_photos:
        if p.issue_id not in photos_by_issue:
            photos_by_issue[p.issue_id] = []
        photos_by_issue[p.issue_id].append({
            "photo_id": p.photo_id,
            "file_path": p.file_path,
            "file_name": p.file_name
        })

    # 建立 (record_id, module_name, item_id) -> issues 映射
    issues_by_key = {}
    for issue in all_issues:
        key = (issue.record_id, issue.module_name, issue.item_id)
        if key not in issues_by_key:
            issues_by_key[key] = []
        issues_by_key[key].append({
            "issue_id": issue.issue_id,
            "description": issue.description or "",
            "severity": issue.severity or "一般",
            "location": issue.location or "",
            "photos": photos_by_issue.get(issue.issue_id, [])
        })

    # 按模块分组
    modules_data = {}
    for r in results:
        if r.module_name not in modules_data:
            modules_data[r.module_name] = {
                "module_name": r.module_name,
                "record_id": r.record_id,
                "items": [],
                "raw_score_sum": 0,
                "weight_sum": 0
            }

        # 获取该项的问题和照片
        item_key = (r.record_id, r.module_name, r.item_id)
        item_issues = issues_by_key.get(item_key, [])

        modules_data[r.module_name]["items"].append({
            "scoring_id": r.scoring_id,
            "item_id": r.item_id,
            "item_name": r.item_name,
            "score": float(r.score),
            "weight": float(r.weight),
            "weighted_score": float(r.weighted_score),
            "check_standard": r.check_standard or "",
            "check_method": r.check_method or "",
            "scoring_rule": r.scoring_rule or "",
            "scoring_basis": r.scoring_basis or "",
            "is_skipped": r.is_skipped,
            "is_fallback": r.is_fallback or False,
            "is_edited": r.is_edited or False,
            "issues": item_issues
        })

        modules_data[r.module_name]["raw_score_sum"] += float(r.weighted_score)
        modules_data[r.module_name]["weight_sum"] += float(r.weight)

    # 计算模块得分和项目总分
    module_scores = []
    total_weighted_score = 0

    for module_name, module_weight in settings.MODULE_WEIGHTS.items():
        data = modules_data.get(module_name)
        if not data or not data["items"]:
            continue

        raw_score_sum = data["raw_score_sum"]
        weight_sum = data["weight_sum"]
        max_score = 5 * weight_sum
        module_pct = (raw_score_sum / max_score * 100) if max_score > 0 else 0

        weighted_contribution = module_pct * module_weight
        total_weighted_score += weighted_contribution

        module_scores.append({
            "module_name": module_name,
            "module_pct_score": round(module_pct, 2),
            "raw_score_sum": round(raw_score_sum, 4),
            "weight_ratio": module_weight,
            "weighted_contribution": round(weighted_contribution, 2),
            "record_id": data.get("record_id"),
            "items": data["items"]
        })

    result = {
        "task_id": task_id,
        "project_name": task.project.name if task.project else "",
        "standard_type": task.standard_type or "diecheng",
        "total_score": round(total_weighted_score, 2),
        "modules": module_scores,
        "scored_module_count": len(module_scores),
        "total_module_count": len(settings.MODULE_WEIGHTS),
        "scoring_method": "Qwen-plus AI评分"
    }

    # 写入缓存
    with _cache_lock:
        _scoring_results_cache[task_id] = result

    return result


def _invalidate_scoring_cache(task_id: str):
    """使评分结果缓存失效"""
    with _cache_lock:
        _scoring_results_cache.pop(task_id, None)
    with _module_detail_lock:
        _module_detail_cache.pop(task_id, None)


@router.get("/results-summary/{task_id}", summary="获取评分摘要（轻量，秒返回）")
async def get_scoring_summary(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    轻量评分摘要（~1KB），只返回总分和各模块得分/权重/检查项数量。
    前端用于瞬间显示评分概览，详细信息在展开模块时按需加载。
    """
    # 缓存命中 → 从完整缓存提取摘要（零DB查询）
    with _cache_lock:
        full = _scoring_results_cache.get(task_id)
        if full:
            return {
                "task_id": full["task_id"],
                "project_name": full.get("project_name", ""),
                "total_score": full["total_score"],
                "modules": [
                    {
                        "module_name": m["module_name"],
                        "module_pct_score": m["module_pct_score"],
                        "weight_ratio": m["weight_ratio"],
                        "items_count": len(m.get("items", [])),
                        "record_id": m.get("record_id"),
                    }
                    for m in full.get("modules", [])
                ],
            }

    # 缓存未命中 → 从 DB 快速查询（SQL聚合，不拉明细）
    task = db.query(InspectionTask).filter(InspectionTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 单条 SQL 聚合：按模块分组求和
    rows = db.query(
        ScoringResult.module_name,
        func.sum(ScoringResult.weighted_score).label("raw_sum"),
        func.sum(ScoringResult.weight).label("weight_sum"),
        func.count(ScoringResult.id).label("cnt"),
    ).join(
        InspectionRecord, ScoringResult.record_id == InspectionRecord.record_id
    ).filter(
        InspectionRecord.task_id == task_id
    ).group_by(
        ScoringResult.module_name
    ).all()

    # 获取每个模块的 record_id
    record_map = {}
    records = db.query(InspectionRecord).filter(
        InspectionRecord.task_id == task_id
    ).all()
    for r in records:
        if r.module_name not in record_map:
            record_map[r.module_name] = r.record_id

    module_map = {r.module_name: {"raw_sum": float(r.raw_sum or 0), "weight_sum": float(r.weight_sum or 0), "cnt": r.cnt} for r in rows}

    module_summaries = []
    total_score = 0
    for module_name, module_weight in settings.MODULE_WEIGHTS.items():
        data = module_map.get(module_name)
        if not data:
            continue
        max_score = 5 * data["weight_sum"]
        pct = (data["raw_sum"] / max_score * 100) if max_score > 0 else 0
        total_score += pct * module_weight
        module_summaries.append({
            "module_name": module_name,
            "module_pct_score": round(pct, 2),
            "weight_ratio": module_weight,
            "items_count": data["cnt"],
            "record_id": record_map.get(module_name),
        })

    return {
        "task_id": task_id,
        "project_name": task.project.name if task.project else "",
        "total_score": round(total_score, 2),
        "modules": module_summaries,
    }


# 模块级详情缓存 (task_id -> {module_name -> items})
_module_detail_cache: dict = {}
_module_detail_lock = threading.Lock()


@router.get("/module-detail/{task_id}/{module_name}", summary="获取模块检查项详情")
async def get_module_detail(
    task_id: str,
    module_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取单个模块的检查项评分详情（按需加载，展开模块时调用）"""
    # 检查模块级缓存
    with _module_detail_lock:
        task_cache = _module_detail_cache.get(task_id)
        if task_cache and module_name in task_cache:
            return {"module_name": module_name, "items": task_cache[module_name]}

    # 从完整缓存提取
    with _cache_lock:
        full = _scoring_results_cache.get(task_id)
        if full:
            for m in full.get("modules", []):
                if m["module_name"] == module_name:
                    items = m.get("items", [])
                    # 存入模块缓存
                    with _module_detail_lock:
                        if task_id not in _module_detail_cache:
                            _module_detail_cache[task_id] = {}
                        _module_detail_cache[task_id][module_name] = items
                    return {"module_name": module_name, "items": items}

    # 查DB：只查该模块的数据
    results = db.query(ScoringResult).join(
        InspectionRecord, ScoringResult.record_id == InspectionRecord.record_id
    ).filter(
        InspectionRecord.task_id == task_id,
        ScoringResult.module_name == module_name,
    ).all()

    if not results:
        return {"module_name": module_name, "items": []}

    record_ids = list(set(r.record_id for r in results))

    # 查该模块的 issues 和 photos
    all_issues = db.query(Issue).filter(
        Issue.record_id.in_(record_ids),
        Issue.module_name == module_name,
    ).all()

    issue_ids = [i.issue_id for i in all_issues]
    all_photos = db.query(Photo).filter(
        Photo.issue_id.in_(issue_ids)
    ).all() if issue_ids else []

    photos_by_issue = {}
    for p in all_photos:
        if p.issue_id not in photos_by_issue:
            photos_by_issue[p.issue_id] = []
        photos_by_issue[p.issue_id].append({
            "photo_id": p.photo_id,
            "file_path": p.file_path,
            "file_name": p.file_name
        })

    issues_by_key = {}
    for issue in all_issues:
        key = (issue.record_id, issue.module_name, issue.item_id)
        if key not in issues_by_key:
            issues_by_key[key] = []
        issues_by_key[key].append({
            "issue_id": issue.issue_id,
            "description": issue.description or "",
            "severity": issue.severity or "一般",
            "location": issue.location or "",
            "photos": photos_by_issue.get(issue.issue_id, [])
        })

    items = []
    for r in results:
        item_key = (r.record_id, r.module_name, r.item_id)
        items.append({
            "scoring_id": r.scoring_id,
            "item_id": r.item_id,
            "item_name": r.item_name or "",
            "score": float(r.score),
            "weight": float(r.weight),
            "weighted_score": float(r.weighted_score),
            "check_standard": r.check_standard or "",
            "check_method": r.check_method or "",
            "scoring_rule": r.scoring_rule or "",
            "scoring_basis": r.scoring_basis or "",
            "is_skipped": r.is_skipped,
            "is_fallback": r.is_fallback or False,
            "is_edited": r.is_edited or False,
            "issues": issues_by_key.get(item_key, [])
        })

    # 缓存
    with _module_detail_lock:
        if task_id not in _module_detail_cache:
            _module_detail_cache[task_id] = {}
        _module_detail_cache[task_id][module_name] = items

    return {"module_name": module_name, "items": items}
async def get_scoring_results(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取评分结果（含检查项详细信息、问题点、问题照片）— 首次后自动缓存"""
    return _build_scoring_results(task_id, db)


@router.put("/items/{scoring_id}", summary="修改单项评分")
async def edit_score(
    scoring_id: str,
    request: ScoreEditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "site_supervisor", "inspector"]))
):
    """
    修改单个检查项的AI评分
    - 更新分数和加权得分
    - 标记为已编辑
    - 自动重算项目总分
    """
    result = db.query(ScoringResult).filter(ScoringResult.scoring_id == scoring_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="评分记录不存在")

    # 验证分数范围
    if request.score < 0 or request.score > 5:
        raise HTTPException(status_code=400, detail="分数必须在0-5之间")

    old_score = float(result.score)
    # 首次编辑才保存AI原始分数
    if not result.is_edited:
        result.original_score = old_score
    result.score = request.score
    result.weighted_score = request.score * float(result.weight)
    result.is_edited = True
    result.is_fallback = False  # 人工修正后清除降级标记
    result.edited_by = current_user.id
    result.edited_at = datetime.utcnow()

    if request.edit_reason:
        result.edit_reason = request.edit_reason
    if request.scoring_basis is not None:
        result.scoring_basis = request.scoring_basis
    if request.improvement_suggestion is not None:
        result.improvement_suggestion = request.improvement_suggestion

    db.commit()

    # 审计日志
    from core.audit import log_action
    log_action("scoring_edit", user_id=current_user.id, username=current_user.username,
                target_type="scoring", target_id=scoring_id,
                detail={"old_score": old_score, "new_score": request.score,
                        "item_id": result.item_id, "module_name": result.module_name,
                        "edit_reason": request.edit_reason})

    # 获取 task_id 并重算总分
    record = db.query(InspectionRecord).filter(
        InspectionRecord.record_id == result.record_id
    ).first()
    if record:
        _compute_and_save_total_score(record.task_id)
        _invalidate_scoring_cache(record.task_id)

    return {
        "message": "评分已更新",
        "scoring_id": scoring_id,
        "old_score": old_score,
        "new_score": request.score,
        "weighted_score": float(result.weighted_score),
        "is_edited": True
    }


@router.put("/modules/{task_id}/{module_name}/rescore", summary="重新评分某个模块")
async def rescore_module(
    task_id: str,
    module_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "site_supervisor"]))
):
    """重新评分某个模块（清除旧结果并重新AI评分）"""
    task = db.query(InspectionTask).filter(InspectionTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    record = db.query(InspectionRecord).filter(
        InspectionRecord.task_id == task_id,
        InspectionRecord.module_name == module_name,
        InspectionRecord.status == "completed"
    ).first()
    if not record:
        raise HTTPException(status_code=400, detail=f"模块 {module_name} 未完成检查")

    # 在后台线程中重新评分（先清除旧结果再评分）
    _invalidate_scoring_cache(task_id)

    def _rescore_single():
        import asyncio as _asyncio
        loop = _asyncio.new_event_loop()
        _asyncio.set_event_loop(loop)
        try:
            # 先清除旧结果
            db2 = SessionLocal()
            try:
                db2.query(ScoringResult).filter(
                    ScoringResult.record_id == record.record_id,
                    ScoringResult.module_name == module_name
                ).delete()
                db2.commit()
            finally:
                db2.close()

            from agents.scoring.nodes import score_module
            loop.run_until_complete(score_module({
                "task_id": task_id,
                "record_id": record.record_id,
                "module_name": module_name,
                "standard_type": task.standard_type or "diecheng",
            }))
            _compute_and_save_total_score(task_id)
            # 评分完成后再次清除缓存，确保前端获取最新数据
            _invalidate_scoring_cache(task_id)
        except Exception as e:
            logger.error(f"重新评分失败 {module_name}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            loop.close()

    t = threading.Thread(target=_rescore_single, daemon=True)
    t.start()

    return {
        "message": f"模块 {module_name} 重新评分已启动",
        "task_id": task_id,
        "module_name": module_name
    }


@router.get("/edit-analysis", summary="评分修改模式分析")
async def get_edit_analysis(
    months: int = 3,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "site_supervisor"]))
):
    """
    分析评分修改模式，用于AI评分纠偏
    - 按模块、修改原因分组统计
    - 计算AI评分偏差趋势
    """
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=months * 30)

    # 查询所有已编辑的评分记录
    edited = db.query(ScoringResult).filter(
        ScoringResult.is_edited == True,
        ScoringResult.edited_at >= cutoff
    ).all()

    if not edited:
        return {"total_edits": 0, "by_module": {}, "by_reason": {}, "avg_deviation": 0}

    # 按模块分组
    by_module = {}
    by_reason = {}
    total_deviation = 0
    deviation_count = 0

    for r in edited:
        # 按模块统计
        mod = r.module_name or "未知"
        if mod not in by_module:
            by_module[mod] = {"count": 0, "avg_deviation": 0, "deviations": []}
        by_module[mod]["count"] += 1

        # 按原因统计
        reason = r.edit_reason or "未分类"
        if reason not in by_reason:
            by_reason[reason] = 0
        by_reason[reason] += 1

        # 使用 original_score 计算实际偏差
        if r.original_score is not None:
            deviation = float(r.original_score) - float(r.score)
            total_deviation += deviation
            deviation_count += 1
            by_module[mod]["deviations"].append(deviation)

    # 计算各模块平均偏差
    for mod in by_module:
        devs = by_module[mod]["deviations"]
        by_module[mod]["avg_deviation"] = round(sum(devs) / len(devs), 2) if devs else 0
        del by_module[mod]["deviations"]  # 不返回原始列表

    avg_deviation = round(total_deviation / deviation_count, 2) if deviation_count > 0 else 0

    return {
        "total_edits": len(edited),
        "by_module": by_module,
        "by_reason": by_reason,
        "avg_deviation": avg_deviation,
        "period_months": months
    }


@router.get("/export/{task_id}", summary="导出评分结果Excel")
async def export_scoring_excel(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """导出评分结果为Excel文件"""
    task = db.query(InspectionTask).filter(InspectionTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 获取评分结果
    results = db.query(ScoringResult).join(
        InspectionRecord, ScoringResult.record_id == InspectionRecord.record_id
    ).filter(InspectionRecord.task_id == task_id).all()

    if not results:
        raise HTTPException(status_code=400, detail="暂无评分数据")

    # 获取 issues 和 photos
    record_ids = list(set(r.record_id for r in results))
    all_issues = db.query(Issue).filter(Issue.record_id.in_(record_ids)).all() if record_ids else []
    issue_ids = [i.issue_id for i in all_issues]
    all_photos = db.query(Photo).filter(Photo.issue_id.in_(issue_ids)).all() if issue_ids else []

    photos_by_issue = {}
    photos_with_path = {}  # issue_id -> [(file_path, file_name)]
    for p in all_photos:
        if p.issue_id not in photos_by_issue:
            photos_by_issue[p.issue_id] = []
            photos_with_path[p.issue_id] = []
        photos_by_issue[p.issue_id].append(p.file_name or "")
        photos_with_path[p.issue_id].append((p.file_path, p.file_name or ""))

    # 构建 item_key -> photo file_paths 映射（用于嵌入图片）
    photos_by_item_key = {}
    for issue in all_issues:
        key = (issue.record_id, issue.module_name, issue.item_id)
        if key not in photos_by_item_key:
            photos_by_item_key[key] = []
        for fp, fn in photos_with_path.get(issue.issue_id, []):
            if os.path.exists(fp):
                photos_by_item_key[key].append(fp)

    issues_by_key = {}
    for issue in all_issues:
        key = (issue.record_id, issue.module_name, issue.item_id)
        if key not in issues_by_key:
            issues_by_key[key] = []
        issue_text = issue.description or ""
        if issue.severity:
            issue_text += f" [{issue.severity}]"
        if issue.location:
            issue_text += f" @ {issue.location}"
        photo_names = photos_by_issue.get(issue.issue_id, [])
        if photo_names:
            issue_text += f" (照片: {', '.join(photo_names)})"
        issues_by_key[key].append(issue_text)

    # 按模块分组
    modules_data = {}
    for r in results:
        if r.module_name not in modules_data:
            modules_data[r.module_name] = []
        modules_data[r.module_name].append(r)

    # 创建 Excel
    wb = openpyxl.Workbook()

    # 样式定义
    header_font = Font(name='微软雅黑', bold=True, size=11, color='FFFFFF')
    header_fill = PatternFill(start_color='1A1F3C', end_color='1A1F3C', fill_type='solid')
    title_font = Font(name='微软雅黑', bold=True, size=14)
    cell_font = Font(name='微软雅黑', size=10)
    center_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
    left_align = Alignment(vertical='center', wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    # 第一个 Sheet: 汇总
    ws_summary = wb.active
    ws_summary.title = "评分汇总"
    ws_summary.merge_cells('A1:H1')
    ws_summary['A1'].value = f"AI评分结果汇总 - {task.project.name if task.project else ''}"
    ws_summary['A1'].font = title_font
    ws_summary['A1'].alignment = Alignment(horizontal='center')

    summary_headers = ['模块名称', '权重', '模块得分(百分制)', '加权贡献', '检查项数', '满分项数', '扣分项数']
    for col, h in enumerate(summary_headers, 1):
        cell = ws_summary.cell(row=3, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = thin_border

    row_idx = 4
    for module_name, module_weight in settings.MODULE_WEIGHTS.items():
        mod_results = modules_data.get(module_name, [])
        if not mod_results:
            continue
        raw_sum = sum(float(r.weighted_score) for r in mod_results)
        weight_sum = sum(float(r.weight) for r in mod_results)
        max_score = 5 * weight_sum if weight_sum > 0 else 1
        module_pct = (raw_sum / max_score * 100) if max_score > 0 else 0
        full_count = sum(1 for r in mod_results if float(r.score) >= 5 and not r.is_skipped)
        deduct_count = sum(1 for r in mod_results if float(r.score) < 5 and not r.is_skipped)

        row_data = [
            module_name,
            f"{module_weight * 100:.0f}%",
            round(module_pct, 2),
            round(module_pct * module_weight, 2),
            len(mod_results),
            full_count,
            deduct_count
        ]
        for col, val in enumerate(row_data, 1):
            cell = ws_summary.cell(row=row_idx, column=col, value=val)
            cell.font = cell_font
            cell.alignment = center_align
            cell.border = thin_border
        row_idx += 1

    # 设置列宽
    for col, width in [(1, 16), (2, 10), (3, 16), (4, 14), (5, 12), (6, 12), (7, 12)]:
        ws_summary.column_dimensions[openpyxl.utils.get_column_letter(col)].width = width

    # 每个模块一个 Sheet
    for module_name, mod_results in modules_data.items():
        ws = wb.create_sheet(title=module_name[:31])

        # 表头
        item_headers = ['检查项编号', '检查项名称', '检查标准', '检查方法', '评分规则', '权重',
                        'AI得分(0-5)', '加权得分', '评分依据', '问题点', '问题照片']
        for col, h in enumerate(item_headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = thin_border

        row_idx = 2
        for r in mod_results:
            item_key = (r.record_id, r.module_name, r.item_id)
            item_issues = issues_by_key.get(item_key, [])
            issues_text = "\n".join(item_issues) if item_issues else ""

            row_data = [
                r.item_id,
                r.item_name or "",
                r.check_standard or "",
                r.check_method or "",
                r.scoring_rule or "",
                float(r.weight),
                float(r.score),
                float(r.weighted_score),
                r.scoring_basis or "",
                issues_text
            ]
            for col, val in enumerate(row_data, 1):
                cell = ws.cell(row=row_idx, column=col, value=val)
                cell.font = cell_font
                cell.alignment = left_align
                cell.border = thin_border

            # 嵌入问题照片到第11列
            item_photos = photos_by_item_key.get(item_key, [])
            if item_photos:
                photo_col_letter = 'K'
                for pi, photo_path in enumerate(item_photos[:3]):  # 最多3张照片
                    try:
                        from openpyxl.drawing.image import Image as XlImage
                        img = XlImage(photo_path)
                        img.width = 120
                        img.height = 90
                        # 第一张放在当前行，后续放在同一列偏移
                        img_cell = f"{photo_col_letter}{row_idx}"
                        ws.add_image(img, img_cell)
                    except Exception as e:
                        # 如果嵌入失败，写入文件名
                        ws.cell(row=row_idx, column=11, value=os.path.basename(photo_path))
                # 调整行高以容纳照片
                ws.row_dimensions[row_idx].height = 75

            row_idx += 1

        # 列宽
        for col, width in [(1, 14), (2, 20), (3, 30), (4, 20), (5, 16),
                           (6, 10), (7, 12), (8, 12), (9, 30), (10, 30), (11, 20)]:
            ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = width

    # 导出
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    project_name = task.project.name if task.project else "unknown"
    filename = f"AI评分结果_{project_name}_{task.check_date}.xlsx"

    from urllib.parse import quote
    encoded_filename = quote(filename)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=\"scoring_result.xlsx\"; filename*=UTF-8''{encoded_filename}"
        }
    )


# 保留旧函数的兼容入口（inspection.py 的旧调用可能引用）
def auto_start_scoring(task_id: str):
    """兼容入口：使用 LangGraph 对所有已完成的模块启动并发评分"""
    import asyncio as _asyncio

    def _run():
        loop = _asyncio.new_event_loop()
        _asyncio.set_event_loop(loop)
        try:
            from agents.scoring import build_scoring_graph
            graph = build_scoring_graph()
            loop.run_until_complete(graph.ainvoke({
                "task_id": task_id,
                "records": [],
                "standard_type": "diecheng",
                "scoring_results": [],
                "completed_modules": [],
                "errors": [],
            }))
        except Exception as e:
            logger.error(f"Auto-Scoring 异常: {e}")
        finally:
            loop.close()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    logger.info(f"LangGraph 评分已启动: {task_id}")


def _start_module_scoring_thread(task_id: str, module_name: str, record_id: str):
    """在后台线程中启动单个模块评分（供外部调用，用于中间模块完成时）"""
    t = threading.Thread(
        target=trigger_single_module_scoring,
        args=(task_id, module_name, record_id),
        daemon=True
    )
    t.start()


# ==================== RAG 和评分记忆 ====================
def _build_memory_context(
    task_id: str,
    project_id: int,
    module_name: str,
    problem_items: list = None
) -> str:
    """
    构建记忆上下文（RAG + 历史评分参考）

    Args:
        task_id: 任务ID
        project_id: 项目ID
        module_name: 当前模块名称
        problem_items: 有问题的检查项列表

    Returns:
        格式化的记忆上下文
    """
    from typing import List, Dict, Any

    parts = []

    # 1. 获取短记忆上下文（本次会话内的评分记忆）
    short_memory_text = ShortMemory.build_memory_prompt(task_id, module_name)
    if short_memory_text:
        parts.append(short_memory_text)

    # 2. 获取长记忆上下文（跨项目的历史评分经验）
    if project_id:
        long_memory_text = get_memory_context_for_scoring(project_id, module_name)
        if long_memory_text:
            parts.append(long_memory_text)

    # 3. 获取历史评分参考（RAG检索相似评分案例）
    if project_id and problem_items:
        scoring_refs = []
        for item in problem_items[:10]:  # 最多处理10个问题项
            item_id = item.get("item_id", "")
            item_name = item.get("item_name", "")
            if item_id and item_name:
                context = build_scoring_context(
                    project_id=project_id,
                    module_name=module_name,
                    item_id=item_id,
                    item_name=item_name,
                    limit=3  # 每项参考3条
                )
                if context:
                    scoring_refs.append(f"【{item_id}】{context}")

        if scoring_refs:
            parts.append("\n".join(scoring_refs))

    result = "\n".join(parts) if parts else ""
    if result:
        logger.info(f"记忆上下文构建成功，长度: {len(result)} 字符")
    return result


# inspection.py 通过此名导入（用于单个模块完成但不是最后一个模块时）
trigger_single_module_scoring_compat = _start_module_scoring_thread


# ==================== Human-in-the-Loop 审核门控 ====================

class ScoreReviewItem(BaseModel):
    result_id: str
    corrected_score: float
    review_note: str = ""

class BatchReviewRequest(BaseModel):
    reviews: List[ScoreReviewItem]


@router.post("/tasks/{task_id}/batch-review", summary="批量审核低置信度评分")
async def batch_review_scores(
    task_id: str,
    request: BatchReviewRequest,
    db: Session = Depends(get_db),
    current_user=Depends(check_role(["admin", "inspector"]))
):
    """
    批量审核低置信度评分项
    审核完成后自动恢复编排器流程（继续生成报告）
    """
    from models.models import ScoringResult

    reviewed_count = 0
    for review in request.reviews:
        result = db.query(ScoringResult).filter(
            ScoringResult.result_id == review.result_id
        ).first()
        if result:
            result.score = review.corrected_score
            result.human_reviewed = True
            result.human_reviewed_by = current_user.id
            result.human_reviewed_at = datetime.utcnow()
            result.is_edited = True
            result.edit_reason = review.review_note or "人工审核修正"
            reviewed_count += 1

    db.commit()

    # SSE 通知
    try:
        from core.event_bus import event_bus
        await event_bus.publish(f"task:{task_id}", {
            "type": "review_completed",
            "reviewed_count": reviewed_count,
        })
    except Exception:
        pass

    return {
        "status": "success",
        "reviewed_count": reviewed_count,
        "message": f"已审核 {reviewed_count} 项评分",
    }


@router.get("/tasks/{task_id}/review-queue", summary="获取待审核评分列表")
async def get_review_queue(
    task_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(check_role(["admin", "inspector", "site_supervisor"]))
):
    """获取某任务中所有需要人工审核的低置信度评分"""
    from models.models import ScoringResult

    results = db.query(ScoringResult).filter(
        ScoringResult.task_id == task_id,
        ScoringResult.needs_human_review == True,
        ScoringResult.human_reviewed == False,
    ).all()

    items = []
    for r in results:
        items.append({
            "result_id": r.result_id,
            "module_name": r.module_name,
            "item_id": r.item_id,
            "item_name": r.item_name,
            "score": float(r.score or 0),
            "confidence_score": float(r.confidence_score or 0),
            "scoring_basis": r.scoring_basis or "",
        })

    return {"total": len(items), "items": items}


@router.get("/review-queue", summary="获取全局评分复核列表")
async def get_global_review_queue(
    page: int = 1,
    page_size: int = 20,
    tab: str = "pending",
    module_name: str = None,
    db: Session = Depends(get_db),
    current_user=Depends(check_role(["admin", "inspector", "site_supervisor"]))
):
    """全局评分复核列表，支持分页和筛选"""
    from models.models import ScoringResult, InspectionRecord, InspectionTask

    query = db.query(ScoringResult).join(
        InspectionRecord, ScoringResult.record_id == InspectionRecord.record_id
    ).join(
        InspectionTask, InspectionRecord.task_id == InspectionTask.task_id
    )

    # Tab filtering
    if tab == "pending":
        query = query.filter(
            ScoringResult.needs_human_review == True,
            ScoringResult.human_reviewed == False,
        )
    elif tab == "reviewed":
        query = query.filter(ScoringResult.human_reviewed == True)
    elif tab == "edited":
        query = query.filter(ScoringResult.is_edited == True)

    # Module filter
    if module_name:
        query = query.filter(ScoringResult.module_name == module_name)

    # Stats
    total = query.count()
    pending_count = db.query(ScoringResult).filter(
        ScoringResult.needs_human_review == True,
        ScoringResult.human_reviewed == False,
    ).count()
    reviewed_count = db.query(ScoringResult).filter(
        ScoringResult.human_reviewed == True,
    ).count()
    edited_count = db.query(ScoringResult).filter(
        ScoringResult.is_edited == True,
    ).count()
    # 低置信度占比（置信度 < 0.8）
    total_with_confidence = db.query(ScoringResult).filter(
        ScoringResult.confidence_score != None
    ).count()
    low_confidence_count = db.query(ScoringResult).filter(
        ScoringResult.confidence_score < 0.8
    ).count()
    low_confidence_rate = round(low_confidence_count / total_with_confidence * 100, 1) if total_with_confidence > 0 else 0

    # Paginate
    results = query.order_by(ScoringResult.scored_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for r in results:
        rec = r.record
        task = rec.task if rec else None
        items.append({
            "scoring_id": r.scoring_id,
            "result_id": r.id,
            "task_id": task.task_id if task else "",
            "project_name": task.project.name if task and task.project else "",
            "check_date": task.check_date if task else "",
            "module_name": r.module_name,
            "item_id": r.item_id,
            "item_name": r.item_name or "",
            "score": float(r.score or 0),
            "confidence_score": float(r.confidence_score or 0),
            "scoring_basis": r.scoring_basis or "",
            "is_edited": r.is_edited,
            "human_reviewed": r.human_reviewed,
        })

    return {
        "items": items,
        "total": total,
        "stats": {
            "pending_count": pending_count,
            "reviewed_count": reviewed_count,
            "edited_count": edited_count,
            "low_confidence_rate": low_confidence_rate,
            # 保留旧字段名，兼容其他调用方
            "pending": pending_count,
            "reviewed": reviewed_count,
            "edited": edited_count,
        }
    }
