"""
评分历史记忆模块
为AI评分提供历史相似案例参考

功能：
1. 检索同项目历史评分案例
2. 检索跨项目相似评分案例
3. 格式化输出用于Prompt注入
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import re

from models.models import ScoringResult, InspectionRecord, InspectionTask, Project
from database import SessionLocal
from core.logger import get_logger

logger = get_logger("scoring_memory")

# 检索结果数量
DEFAULT_LIMIT = 5


def get_scoring_references(
    project_id: int,
    module_name: str,
    item_id: str,
    item_name: str,
    limit: int = DEFAULT_LIMIT
) -> List[Dict]:
    """
    获取评分参考案例（核心检索函数）

    检索策略：
    1. 同项目 + 同模块 + 相似item_id（优先）
    2. 同项目 + 同模块 + 相似item_name
    3. 跨项目 + 同模块 + 相似item_id
    4. 跨项目 + 同模块 + 相似item_name

    Args:
        project_id: 当前项目ID
        module_name: 模块名称
        item_id: 检查项ID
        item_name: 检查项名称
        limit: 返回数量

    Returns:
        参考案例列表
    """
    db = SessionLocal()
    try:
        # 构建基础查询
        base_query = db.query(ScoringResult).join(
            InspectionRecord, ScoringResult.record_id == InspectionRecord.record_id
        ).join(
            InspectionTask, InspectionRecord.task_id == InspectionTask.task_id
        ).join(
            Project, InspectionTask.project_id == Project.id
        ).filter(
            ScoringResult.module_name == module_name
        )

        # 提取item_id的关键字（用于模糊匹配）
        item_id_keywords = _extract_keywords(item_id)

        results = []
        seen_scores = set()  # 去重

        # 策略1: 同项目 + 精确item_id匹配
        same_project = base_query.filter(
            InspectionTask.project_id == project_id
        ).all()

        for r in same_project:
            if _is_similar_item(r.item_id, item_id) or _is_similar_item(r.item_name, item_name):
                key = (r.item_id, r.score)
                if key not in seen_scores and len(results) < limit:
                    seen_scores.add(key)
                    results.append(_format_reference(r, same_project=True))

        # 策略2: 同项目 + 模糊item_name匹配
        if len(results) < limit:
            for r in same_project:
                if _keyword_overlap(r.item_name, item_name) and r.score not in [x['score'] for x in results]:
                    key = (r.item_id, r.score)
                    if key not in seen_scores and len(results) < limit:
                        seen_scores.add(key)
                        results.append(_format_reference(r, same_project=True))

        # 策略3: 跨项目 + 精确item_id匹配
        if len(results) < limit:
            cross_project = base_query.filter(
                InspectionTask.project_id != project_id
            ).all()

            for r in cross_project:
                if _is_similar_item(r.item_id, item_id):
                    key = (r.item_id, r.score)
                    if key not in seen_scores and len(results) < limit:
                        seen_scores.add(key)
                        results.append(_format_reference(r, same_project=False))

        # 策略4: 跨项目 + 模糊item_name匹配
        if len(results) < limit:
            for r in cross_project:
                if _keyword_overlap(r.item_name, item_name):
                    key = (r.item_id, r.score)
                    if key not in seen_scores and len(results) < limit:
                        seen_scores.add(key)
                        results.append(_format_reference(r, same_project=False))

        logger.debug(f"评分参考检索: 项目={project_id}, 模块={module_name}, 项={item_id}, 找到={len(results)}条")
        return results

    finally:
        db.close()


def build_scoring_context(
    project_id: int,
    module_name: str,
    item_id: str,
    item_name: str,
    limit: int = DEFAULT_LIMIT
) -> str:
    """
    构建评分上下文字符串（用于注入Prompt）

    Args:
        project_id: 当前项目ID
        module_name: 模块名称
        item_id: 检查项ID
        item_name: 检查项名称
        limit: 参考数量

    Returns:
        格式化的上下文字符串
    """
    references = get_scoring_references(
        project_id=project_id,
        module_name=module_name,
        item_id=item_id,
        item_name=item_name,
        limit=limit
    )

    if not references:
        return ""

    lines = ["\n\n【历史评分参考】（请保持评分一致性）"]
    for i, ref in enumerate(references, 1):
        project_tag = "[本项目]" if ref['is_same_project'] else "[其他项目]"
        lines.append(
            f"{i}. {project_tag} {ref['item_name'][:30]} | "
            f"问题:{ref['scoring_basis'][:40]} | "
            f"评分:{ref['score']}分"
        )

    return "\n".join(lines)


def _format_reference(scoring: ScoringResult, same_project: bool = False) -> Dict:
    """格式化参考案例"""
    return {
        "scoring_id": scoring.scoring_id,
        "item_id": scoring.item_id,
        "item_name": scoring.item_name,
        "score": scoring.score,
        "scoring_basis": scoring.scoring_basis or "",
        "module_name": scoring.module_name,
        "is_same_project": same_project,
        "project_name": scoring.record.task.project.name if scoring.record and scoring.record.task and scoring.record.task.project else ""
    }


def _extract_keywords(text: str) -> List[str]:
    """提取关键词（用于模糊匹配）"""
    if not text:
        return []

    # 移除常见前缀
    text = re.sub(r'^[A-Z]-\d+\s*', '', text)

    # 按中文字符分词（简单实现）
    keywords = []
    for char in text:
        if '\u4e00' <= char <= '\u9fff':  # 中文字符
            keywords.append(char)

    # 提取连续的中文词组
    chinese_words = re.findall(r'[\u4e00-\u9fff]{2,}', text)
    keywords.extend(chinese_words)

    return list(set(keywords))[:5]  # 最多5个关键词


def _is_similar_item(item_id1: str, item_id2: str) -> bool:
    """判断两个item_id是否相似"""
    if not item_id1 or not item_id2:
        return False

    # 去除前缀后比较
    id1 = re.sub(r'^[A-Z]-\d+\s*', '', item_id1)
    id2 = re.sub(r'^[A-Z]-\d+\s*', '', item_id2)

    # 精确匹配
    if id1 == id2:
        return True

    # 前缀匹配
    if id1.startswith(id2[:3]) or id2.startswith(id1[:3]):
        return True

    return False


def _keyword_overlap(text1: str, text2: str) -> float:
    """
    计算两个文本的关键词重叠度

    Returns:
        0.0 ~ 1.0 的重叠度
    """
    if not text1 or not text2:
        return 0.0

    keywords1 = set(_extract_keywords(text1))
    keywords2 = set(_extract_keywords(text2))

    if not keywords1 or not keywords2:
        return 0.0

    overlap = keywords1 & keywords2
    return len(overlap) / max(len(keywords1), len(keywords2))


def get_module_score_trend(
    project_id: int,
    module_name: str
) -> Dict:
    """
    获取项目某模块的历史评分趋势

    用于分析评分变化

    Returns:
        {"avg_score": float, "count": int, "trend": str}
    """
    db = SessionLocal()
    try:
        results = db.query(
            func.avg(ScoringResult.score).label('avg_score'),
            func.count(ScoringResult.id).label('count')
        ).join(
            InspectionRecord, ScoringResult.record_id == InspectionRecord.record_id
        ).join(
            InspectionTask, InspectionRecord.task_id == InspectionTask.task_id
        ).filter(
            InspectionTask.project_id == project_id,
            ScoringResult.module_name == module_name
        ).first()

        return {
            "avg_score": float(results.avg_score) if results and results.avg_score else 0,
            "count": results.count if results else 0,
            "trend": "stable"  # 简化实现
        }
    finally:
        db.close()