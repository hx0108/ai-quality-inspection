"""
统一评分服务
供 api/scoring.py 和 agents/scoring/nodes.py 共同调用，消除逻辑重复
"""
import uuid as _uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from models.models import InspectionRecord, Issue, ScoringResult
from config import settings
from core.llm_client import QwenClient
from core.logger import get_logger
from api.tasks import load_template_items
from core.short_memory import ShortMemory
from core.long_memory import LongMemory, get_memory_context_for_scoring

logger = get_logger("scoring_service")

# 置信度阈值
CONFIDENCE_THRESHOLD = 0.8  # 低于此值需要人工复核


async def score_module_core(
    db: Session,
    task_id: str,
    module_name: str,
    record_id: str,
    standard_type: str = "diecheng",
    project_id: int = None,
) -> Dict[str, Any]:
    """
    统一的模块评分核心逻辑

    Args:
        db: 数据库会话
        task_id: 任务ID
        module_name: 模块名称
        record_id: 检查记录ID
        standard_type: 标准类型
        project_id: 项目ID（用于长记忆检索）

    Returns:
        {"results": [...], "module_name": str, "count": int, "errors": [...]}
    """
    # 1. 清除该模块的旧评分结果
    deleted = db.query(ScoringResult).filter(
        ScoringResult.record_id == record_id,
        ScoringResult.module_name == module_name
    ).delete()
    if deleted > 0:
        logger.info(f"清除旧评分: {module_name} ({deleted}条)")
        db.commit()

    # 2. 获取该模块的问题
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

    # 3. 从模板获取检查项
    template_items = load_template_items(module_name, standard_type)
    if not template_items:
        logger.warning(f"无模板数据: {module_name}")
        return {"results": [], "module_name": module_name, "count": 0, "errors": [f"无模板数据: {module_name}"]}

    # 4. 分离合格项 / 有问题项 / 扣分项
    is_lizhi = (standard_type == "lizhi")
    qualified_items = []
    problem_items = []
    deduction_items = []  # 砺质扣分项（其他场所5S，旧标准为BI及5S）：确定性计分，不走AI

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
            "max_score": item.get("max_score", 5),
            "is_deduction": item.get("is_deduction", False),
            "issues": item_issues,
            "is_skipped": False
        }

        if is_lizhi and entry["is_deduction"]:
            deduction_items.append(entry)
        elif not item_issues:
            qualified_items.append(entry)
        else:
            problem_items.append(entry)

    logger.info(f"{module_name}: 合格{len(qualified_items)}项, 有问题{len(problem_items)}项, 扣分{len(deduction_items)}项")

    # 5. 合格项直接满分（砺质=该项max_score；蝶城/非蝶城=5）
    results = []
    for item in qualified_items:
        full = item["max_score"] if is_lizhi else 5
        basis = f"检查合格，无问题发现，给予满分{full}分" if is_lizhi else "检查合格，无问题发现，给予满分5分"
        results.append({
            "item_id": item["item_id"],
            "item_name": item["item_name"],
            "score": full,
            "scoring_basis": basis,
            "improvement_suggestion": ""
        })

    # 5b. 扣分项（砺质扣分模块）：确定性规则 score = -(问题数 × 单位扣分)
    for item in deduction_items:
        issue_count = len(item["issues"])
        per = item["max_score"] or 3
        score = -(issue_count * per)
        results.append({
            "item_id": item["item_id"],
            "item_name": item["item_name"],
            "score": score,
            "scoring_basis": f"发现{issue_count}处不合格，每处扣{per}分，共扣{issue_count * per}分",
            "improvement_suggestion": ""
        })

    # 6. 有问题项调用AI评分（注入记忆上下文）
    if problem_items and settings.DASHSCOPE_API_KEY:
        llm = QwenClient()

        # 构建记忆上下文
        memory_context = _build_memory_context(task_id, project_id, module_name, problem_items)

        logger.info(f"AI评分: {module_name} ({len(problem_items)}项)")
        ai_results = await llm.score_module(module_name, problem_items, memory_context=memory_context, standard_type=standard_type)
        logger.info(f"AI返回: {module_name} ({len(ai_results)}项)")
        results.extend(ai_results)
    elif problem_items:
        # 无API Key，使用简单规则评分
        for item in problem_items:
            issue_count = len(item["issues"])
            if is_lizhi:
                score = max(0, item["max_score"] - issue_count)
            else:
                score = max(0, 5 - issue_count)
            results.append({
                "item_id": item["item_id"],
                "item_name": item["item_name"],
                "score": score,
                "scoring_basis": f"发现{issue_count}个问题，扣{issue_count}分",
                "improvement_suggestion": ""
            })

    # 7. 合并所有检查项
    all_items = qualified_items + problem_items + deduction_items

    # 8. 保存评分结果到DB
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

        # 计算置信度并判断是否需要人工复核
        confidence_score = item_result.get("confidence_score", _calculate_confidence(item_result, original_item))
        needs_review = confidence_score < CONFIDENCE_THRESHOLD if confidence_score else False

        # 砺质：weighted_score 直接等于原始分值（无权重概念）；其它标准维持 score×weight
        if is_lizhi:
            weighted_score = score
        else:
            weighted_score = score * weight

        result = ScoringResult(
            scoring_id=scoring_id,
            record_id=record_id,
            module_name=module_name,
            item_id=item_id,
            item_name=item_name,
            score=score,
            weight=weight,
            weighted_score=weighted_score,
            scoring_basis=item_result.get("scoring_basis", ""),
            improvement_suggestion=item_result.get("improvement_suggestion", ""),
            check_standard=check_standard,
            check_method=check_method,
            scoring_rule=scoring_rule,
            is_skipped=item_result.get("is_skipped", False),
            confidence_score=confidence_score,
            needs_human_review=needs_review,
        )
        db.add(result)

        if (i + 1) % batch_size == 0:
            db.commit()

    db.commit()
    logger.info(f"完成: {module_name} ({len(results)}条)")

    return {
        "results": results,
        "module_name": module_name,
        "count": len(results),
        "errors": []
    }


def save_default_scores(
    db: Session,
    task_id: str,
    module_name: str,
    record_id: str,
    standard_type: str = "diecheng",
    reason: str = "评分失败，使用默认分数"
):
    """
    评分失败/超时时保存默认分数
    问题项给3.0分，合格项给5.0分
    """
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

        template_items = load_template_items(module_name, standard_type)
        if not template_items:
            return

        is_lizhi = (standard_type == "lizhi")
        for item in template_items:
            max_score = item.get("max_score", 5)
            is_deduction = item.get("is_deduction", False)
            if is_lizhi:
                if is_deduction:
                    # 扣分项降级：默认不扣（0），由人工复核
                    score = 0
                elif item["item_id"] in issue_item_ids:
                    score = round(max_score * 0.6, 1)  # 有问题给60%分
                else:
                    score = max_score  # 合格满分
            else:
                score = 3.0 if item["item_id"] in issue_item_ids else 5.0
            weight = item.get("weight", 0.01)
            weighted_score = score if is_lizhi else score * weight
            scoring_id = f"SCR-{_uuid.uuid4().hex[:12]}"
            result = ScoringResult(
                scoring_id=scoring_id,
                record_id=record_id,
                module_name=module_name,
                item_id=item["item_id"],
                item_name=item.get("item_name", ""),
                score=score,
                weight=weight,
                weighted_score=weighted_score,
                scoring_basis=reason,
                improvement_suggestion="",
                is_skipped=False,
                is_fallback=True,  # 标记为降级默认分数
                confidence_score=0.3,  # 降级分数置信度低
                needs_human_review=True,  # 需要人工复核
            )
            db.add(result)
        db.commit()
        logger.info(f"默认分数已保存: {module_name}")
    except Exception as e:
        logger.error(f"保存默认分数失败: {e}")


def _calculate_confidence(item_result: Dict, original_item: Dict) -> float:
    """
    计算评分置信度

    置信度影响因素：
    1. 问题数量：问题过多（如>5个）降低置信度
    2. 边界分数：3.5, 4.5, 2.5等边界分数降低置信度
    3. 有问题但分数很高（如>=4.5）降低置信度
    4. 评分依据长度过短降低置信度

    Returns:
        置信度值 0.0-1.0
    """
    base_confidence = 0.9

    score = item_result.get("score", 5)
    issues = original_item.get("issues", [])
    scoring_basis = item_result.get("scoring_basis", "")

    # 问题数量过多，降低置信度
    if len(issues) > 5:
        base_confidence -= 0.15
    elif len(issues) > 3:
        base_confidence -= 0.1

    # 边界分数降低置信度
    boundary_scores = [3.5, 4.5, 2.5, 1.5]
    if score in boundary_scores:
        base_confidence -= 0.1

    # 有问题但分数很高，异常检测
    if issues and score >= 4.5:
        base_confidence -= 0.15

    # 有问题但分数很低但只有轻微问题
    if issues and score <= 1.5 and not any(
        issue.get("severity") == "严重" for issue in issues
    ):
        base_confidence -= 0.15

    # 评分依据长度过短
    if len(scoring_basis) < 20:
        base_confidence -= 0.1
    elif len(scoring_basis) < 40:
        base_confidence -= 0.05

    return max(0.5, min(1.0, base_confidence))


def _build_memory_context(
    task_id: str,
    project_id: int,
    module_name: str,
    problem_items: List[Dict] = None
) -> str:
    """
    构建记忆上下文字符串

    Args:
        task_id: 任务ID
        project_id: 项目ID
        module_name: 当前模块名称
        problem_items: 有问题的检查项列表（用于查找历史参考）

    Returns:
        格式化的记忆上下文；任何异常都返回空串，绝不阻断评分。
        （记忆上下文是增强项，DB 锁或检索失败时降级为无记忆评分）
    """
    from core.scoring_memory import build_scoring_context

    parts = []
    try:
        # 1. 获取短记忆上下文
        short_memory_text = ShortMemory.build_memory_prompt(task_id, module_name)
        if short_memory_text:
            parts.append(short_memory_text)

        # 2. 获取长记忆上下文
        if project_id:
            long_memory_text = get_memory_context_for_scoring(project_id, module_name)
            if long_memory_text:
                parts.append(long_memory_text)

        # 3. 获取历史评分参考（对每个problem_item查找相似历史案例）
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
    except Exception as e:
        # 记忆上下文检索/写入失败（常见：SQLite "database is locked"，
        # 因当前 db session 持有读事务、记忆子系统另开会话写 project_memories 访问统计）
        # 绝不让增强项阻断评分——降级为无记忆评分。
        logger.warning(f"构建记忆上下文失败，降级为无记忆评分: {module_name} - {e}")
        return ""

    return "\n".join(parts) if parts else ""


def update_memories_after_scoring(
    task_id: str,
    project_id: int,
    module_name: str,
    module_score: float,
    issues: List[Dict],
) -> None:
    """
    评分完成后更新记忆

    Args:
        task_id: 任务ID
        project_id: 项目ID
        module_name: 模块名称
        module_score: 模块百分制得分
        issues: 该模块的问题列表
    """
    try:
        # 1. 更新短记忆
        ShortMemory.update_scoring_result(task_id, module_name, module_score, issues)

        # 2. 提取并保存反复出现的问题（长记忆）
        if project_id and issues:
            # 只有问题数>=2时才认为是反复出现
            if len(issues) >= 2:
                LongMemory.extract_and_save_recurring_issues(project_id, task_id)

        logger.debug(f"记忆已更新: {module_name}, 项目{project_id}, 得分{module_score}")
    except Exception as e:
        logger.warning(f"更新记忆失败: {e}")
