"""
Scoring Agent 节点函数
Agent 2 LangGraph Nodes

工作流: collect_records → fan-out(score_module × N) → fan-in → compute_total
"""
import uuid as _uuid
from datetime import datetime
from typing import List, Dict, Any

from database import SessionLocal
from models.models import InspectionTask, InspectionRecord, Issue, ScoringResult
from config import settings
from core.llm_client import QwenClient
from core.scoring_tracker import scoring_tracker
from core.scoring_memory import build_scoring_context
from core.long_memory import get_memory_context_for_scoring
from core.short_memory import ShortMemory
from core.logger import get_logger
from api.tasks import load_template_items

logger = get_logger("scoring_agent")


async def collect_records(state: dict) -> dict:
    """
    节点1: 收集待评分的检查记录
    查询已完成的 InspectionRecord，过滤掉已评分的模块
    """
    task_id = state["task_id"]
    logger.info(f"collect_records: {task_id}")

    # 初始化 tracker
    scoring_tracker.init_task(task_id)

    db = SessionLocal()
    try:
        task = db.query(InspectionTask).filter(InspectionTask.task_id == task_id).first()
        if not task:
            return {"errors": ["任务不存在"], "records": []}

        standard_type = task.standard_type or "diecheng"

        # 查询已完成的检查记录
        records = db.query(InspectionRecord).filter(
            InspectionRecord.task_id == task_id,
            InspectionRecord.status == "completed"
        ).all()

        if not records:
            return {"errors": ["没有已完成的检查记录"], "records": []}

        # 过滤已评分模块
        to_score = []
        for record in records:
            existing = db.query(ScoringResult).filter(
                ScoringResult.record_id == record.record_id
            ).count()
            if existing > 0:
                scoring_tracker.set_module_status(task_id, record.module_name, "completed")
            else:
                to_score.append({
                    "record_id": record.record_id,
                    "module_name": record.module_name
                })

        if not to_score:
            logger.info(f"所有模块已评分")

        logger.info(f"待评分: {len(to_score)} 个模块")

        return {
            "records": to_score,
            "standard_type": standard_type,
            "scoring_results": [],
            "completed_modules": [],
            "errors": []
        }

    except Exception as e:
        logger.error(f"collect_records 失败: {e}")
        return {"errors": [str(e)], "records": []}
    finally:
        db.close()


async def score_module(state: dict) -> dict:
    """
    节点2: 单模块评分（并行执行）
    通过 Send 传入单个模块的数据
    复用 _score_module_async() 核心逻辑
    """
    task_id = state["task_id"]
    record_id = state["record_id"]
    module_name = state["module_name"]
    standard_type = state.get("standard_type", "diecheng")

    logger.info(f"score_module: {module_name}")
    scoring_tracker.set_module_status(task_id, module_name, "scoring")

    # SSE 事件：模块开始评分
    try:
        from core.event_bus import event_bus
        await event_bus.publish(f"task:{task_id}", {
            "type": "scoring_progress",
            "module": module_name,
            "status": "scoring",
        })
    except Exception:
        pass

    db = SessionLocal()
    try:
        record = db.query(InspectionRecord).filter(
            InspectionRecord.record_id == record_id
        ).first()
        if not record:
            scoring_tracker.set_module_status(task_id, module_name, "failed", "记录不存在")
            return {"errors": [f"记录不存在: {record_id}"]}

        # 统一委托 score_module_core（支持蝶城/非蝶城/砺质，消除重复实现）
        from core.scoring_service import score_module_core
        result = await score_module_core(db, task_id, module_name, record_id,
                                         standard_type=standard_type, project_id=record.project_id)
        count = result.get("count", 0)
        errors = result.get("errors", [])

        if errors:
            logger.warning(f"评分存在问题: {module_name}: {errors}")

        scoring_tracker.set_module_status(task_id, module_name, "completed")
        logger.info(f"完成: {module_name} ({count}条)")

        # SSE 事件推送
        try:
            from core.event_bus import event_bus
            await event_bus.publish(f"task:{task_id}", {
                "type": "scoring_progress",
                "module": module_name,
                "status": "completed",
                "items_count": count,
            })
        except Exception:
            pass

        return {
            "scoring_results": [{"module_name": module_name, "count": count}],
            "completed_modules": [module_name]
        }

    except Exception as e:
        logger.error(f"评分失败 {module_name}: {e}")
        import traceback
        traceback.print_exc()
        scoring_tracker.set_module_status(task_id, module_name, "failed", str(e))

        # 保存默认分数（按 standard_type，支持砺质）
        try:
            from core.scoring_service import save_default_scores
            save_default_scores(db, task_id, module_name, record_id,
                               standard_type=standard_type, reason="评分失败，使用默认分数")
        except Exception as se:
            logger.error(f"保存默认分数失败: {se}")

        return {
            "scoring_results": [{"module_name": module_name, "count": 0}],
            "completed_modules": [module_name],
            "errors": [f"{module_name}: {str(e)}"]
        }
    finally:
        db.close()


def compute_total(state: dict) -> dict:
    """
    节点3: 计算项目总分
    计分模型按 task.standard_type 选择（蝶城/非蝶城=加权5分制；砺质=封顶+扣分）。
    """
    from core.scoring_aggregation import aggregate
    task_id = state["task_id"]
    logger.info(f"compute_total: {task_id}")

    db = SessionLocal()
    try:
        task = db.query(InspectionTask).filter(InspectionTask.task_id == task_id).first()
        if not task:
            return {"errors": ["任务不存在"]}
        standard_type = task.standard_type or "diecheng"

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

        # 统一计算（按 standard_type 自动选择计分模型）
        agg = aggregate(standard_type, modules_data)
        module_pct_map = agg["module_pct"]
        for r in results:
            if r.module_name in module_pct_map:
                r.module_pct_score = module_pct_map[r.module_name]

        task.total_score = agg["total"]
        db.commit()
        logger.info(f"项目总分({standard_type}): {task.total_score}")
        return {}

    except Exception as e:
        logger.error(f"compute_total 失败: {e}")
        return {"errors": [str(e)]}
    finally:
        db.close()


def _rule_based_fallback_scores(problem_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    基于规则的智能回退评分（当 AI 评分失败时使用）
    根据问题数量和严重程度给出合理的分数，而非笼统的"中等分数"
    """
    results = []
    for item in problem_items:
        issues = item.get("issues", [])
        issue_count = len(issues)

        # 按严重程度统计
        severity_map = {"严重": 0, "一般": 0, "轻微": 0}
        for issue in issues:
            sev = issue.get("severity", "一般")
            severity_map[sev] = severity_map.get(sev, 0) + 1

        # 基于严重程度和数量的扣分计算
        deduction = 0
        deduction_reasons = []

        if severity_map.get("严重", 0) > 0:
            deduction += severity_map["严重"] * 2.0
            deduction_reasons.append(f"{severity_map['严重']}个严重问题")
        if severity_map.get("一般", 0) > 0:
            deduction += severity_map["一般"] * 1.0
            deduction_reasons.append(f"{severity_map['一般']}个一般问题")
        if severity_map.get("轻微", 0) > 0:
            deduction += severity_map["轻微"] * 0.5
            deduction_reasons.append(f"{severity_map['轻微']}个轻微问题")

        # 最多扣5分
        deduction = min(5.0, deduction)
        score = max(0, round(5.0 - deduction, 1))

        basis_parts = "、".join(deduction_reasons) if deduction_reasons else "存在问题"
        scoring_basis = f"发现{basis_parts}，扣{deduction}分，得{score}分"

        # 根据严重程度生成改进建议
        suggestions = []
        if severity_map.get("严重", 0) > 0:
            suggestions.append("建议立即整改严重问题并提交复查")
        if severity_map.get("一般", 0) > 0:
            suggestions.append("建议制定整改计划并在规定期限内完成")
        if severity_map.get("轻微", 0) > 0:
            suggestions.append("建议日常巡检中关注并改善")

        results.append({
            "item_id": item.get("item_id"),
            "item_name": item.get("item_name", ""),
            "score": score,
            "scoring_basis": scoring_basis,
            "improvement_suggestion": "；".join(suggestions) if suggestions else "",
            "_weight": item.get("weight", 0.01),
            "_check_standard": item.get("check_standard", ""),
            "_check_method": item.get("check_method", ""),
            "_scoring_rule": item.get("scoring_rule", "")
        })

    return results


def _save_default_scores(db, task_id: str, module_name: str, record_id: str):
    """评分失败时保存默认分数"""
    try:
        db.query(ScoringResult).filter(
            ScoringResult.record_id == record_id,
            ScoringResult.module_name == module_name
        ).delete()
        db.commit()

        issues = db.query(Issue).filter(
            Issue.record_id == record_id,
            Issue.module_name == module_name
        ).all()
        issue_item_ids = set(i.item_id for i in issues)

        task = db.query(InspectionTask).filter(InspectionTask.task_id == task_id).first()
        standard_type = task.standard_type if task else "diecheng"
        template_items = load_template_items(module_name, standard_type)
        if not template_items:
            return

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
                scoring_basis="评分失败，使用默认分数",
                improvement_suggestion="",
                is_skipped=False
            )
            db.add(result)
        db.commit()
        logger.info(f"默认分数已保存: {module_name}")
    except Exception as e:
        logger.error(f"保存默认分数失败: {e}")


def _build_memory_context(
    task_id: str,
    project_id: int,
    module_name: str,
    problem_items: List[Dict[str, Any]] = None
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


def _update_memories_after_scoring(
    task_id: str,
    project_id: int,
    module_name: str,
    scoring_results: List[Dict[str, Any]],
    issues: List[Any]
):
    """
    评分完成后更新记忆

    Args:
        task_id: 任务ID
        project_id: 项目ID
        module_name: 模块名称
        scoring_results: 评分结果列表
        issues: 该模块的问题列表
    """
    try:
        from core import standards as stds
        # 计算模块得分（记忆上下文用；权威值得由 compute_total 通过 aggregate 计算）
        lizhi_cfg = stds.get_module_cfg("lizhi", module_name)
        if lizhi_cfg:  # 砺质模块
            raw = sum(float(r.get("weighted_score", 0)) for r in scoring_results) if scoring_results else 0.0
            if lizhi_cfg.get("role") == "deduction":
                module_pct_score = raw
            else:
                module_pct_score = min(raw, lizhi_cfg.get("max_score", 25))
        elif scoring_results:
            total_weighted = sum(float(r.get("weighted_score", 0)) for r in scoring_results)
            total_weight = sum(float(r.get("weight", 0.01)) for r in scoring_results)
            if total_weight > 0:
                module_pct_score = (total_weighted / (5 * total_weight)) * 100
            else:
                module_pct_score = 100.0
        else:
            module_pct_score = 0.0

        # 准备问题列表
        issue_list = []
        for issue in issues:
            issue_list.append({
                "description": issue.description if hasattr(issue, 'description') else str(issue),
                "severity": issue.severity if hasattr(issue, 'severity') else "一般"
            })

        # 更新短记忆
        ShortMemory.update_scoring_result(task_id, module_name, module_pct_score, issue_list)

        # 提取并保存反复出现的问题（长记忆）
        if project_id and len(issue_list) >= 2:
            try:
                from core.long_memory import LongMemory
                LongMemory.extract_and_save_recurring_issues(project_id, task_id)
            except Exception as e:
                logger.warning(f"长记忆更新失败: {e}")

        logger.debug(f"记忆已更新: {module_name}, 项目{project_id}, 得分{module_pct_score:.2f}")
    except Exception as e:
        logger.warning(f"更新记忆失败: {e}")
