"""
检查引导 Agent
为检查员提供AI辅助的检查重点、历史参考和拍照建议

数据来源:
  - 长期记忆 (long_memory): 该项目的反复出现问题、跨项目共性问题
  - 评分记忆 (scoring_memory): 历史评分参考案例
  - 检查模板 (tasks.py): 标准检查项、检查标准、评分规则
  - 上次评分结果: 上次扣分项
"""
from typing import List, Dict, Any, Optional
from database import SessionLocal
from models.models import (
    InspectionTask, InspectionRecord, ScoringResult,
    Issue, Project
)
from config import settings
from core.logger import get_logger

logger = get_logger("guide_agent")


def get_focus_items(project_id: int, module_name: str, limit: int = 10) -> Dict[str, Any]:
    """
    获取某模块的检查重点关注项

    返回:
      - focus_items: 重点关注检查项列表（基于历史扣分和反复出现问题）
      - history_summary: 该模块的历史问题统计
      - tips: AI检查提示
    """
    db = SessionLocal()
    try:
        result = {
            "module_name": module_name,
            "focus_items": [],
            "history_summary": {},
            "tips": []
        }

        # 1. 从长期记忆获取该项目的反复出现问题
        recurring_issues = _get_recurring_issues(db, project_id, module_name)
        if recurring_issues:
            result["tips"].append({
                "type": "recurring",
                "message": f"该项目 {module_name} 存在 {len(recurring_issues)} 个反复出现问题",
                "items": recurring_issues[:5]
            })

        # 2. 获取上次检查的扣分项
        last_deducted = _get_last_deducted_items(db, project_id, module_name)
        if last_deducted:
            result["focus_items"].extend(last_deducted[:5])
            result["tips"].append({
                "type": "last_check",
                "message": f"上次检查有 {len(last_deducted)} 个扣分项，请重点复查",
                "items": [{"item_id": d["item_id"], "item_name": d["item_name"],
                           "last_score": d["last_score"]} for d in last_deducted[:3]]
            })

        # 3. 从长期记忆获取跨项目共性问题
        cross_project = _get_cross_project_issues(db, module_name)
        if cross_project:
            result["tips"].append({
                "type": "cross_project",
                "message": f"其他项目中该模块常见 {len(cross_project)} 类问题",
                "items": cross_project[:3]
            })

        # 4. 获取历史评分趋势
        trend = _get_module_score_trend(db, project_id, module_name)
        if trend:
            result["history_summary"] = trend

        # 5. 如果没有重点关注项，从模板中提取高频权重项
        if not result["focus_items"]:
            template_focus = _get_high_weight_items(module_name)
            if template_focus:
                result["focus_items"] = template_focus
                result["tips"].append({
                    "type": "template",
                    "message": "无历史数据，建议按权重从高到低检查",
                    "items": [{"item_id": t["item_id"], "item_name": t["item_name"],
                               "weight": t["weight"]} for t in template_focus[:3]]
                })

        return result

    except Exception as e:
        logger.error(f"获取检查引导失败: {e}")
        return {"module_name": module_name, "focus_items": [], "history_summary": {}, "tips": []}
    finally:
        db.close()


def get_similar_cases(item_id: str, item_name: str, module_name: str,
                      description: str = "", limit: int = 5) -> List[Dict[str, Any]]:
    """
    获取相似历史案例（检查员输入问题时实时推荐）

    基于 RAG 引擎搜索相似评分案例
    """
    try:
        from core.scoring_memory import build_scoring_context
        # 使用评分记忆引擎搜索相似案例
        context = build_scoring_context(
            project_id=0,  # 跨项目搜索
            module_name=module_name,
            item_id=item_id,
            item_name=item_name,
            limit=limit
        )
        if context:
            return [{"source": "scoring_memory", "context": context}]
    except Exception as e:
        logger.warning(f"相似案例搜索失败: {e}")

    return []


def get_photo_tips(item_id: str, module_name: str) -> Dict[str, Any]:
    """
    获取拍照建议（基于整改验证经验）

    返回:
      - suggested_angles: 建议拍摄角度/内容
      - common_rejection_reasons: 整改验证中常见的照片驳回原因
      - min_photos: 建议最少照片数量
    """
    db = SessionLocal()
    try:
        result = {
            "item_id": item_id,
            "module_name": module_name,
            "suggested_angles": [],
            "common_rejection_reasons": [],
            "min_photos": 1
        }

        # 从长期记忆中获取该类型问题的整改验证经验
        from core.long_memory import LongMemory, MemoryType
        memory = LongMemory()

        memories = memory.get_project_memories(
            project_id=None,  # 跨项目
            memory_type=MemoryType.IMPROVEMENT_TREND,
            module_name=module_name,
            limit=5
        )

        rejection_reasons = set()
        for m in memories:
            content = m.content if hasattr(m, 'content') else str(m)
            if "驳回" in content or "表面处理" in content or "临时遮挡" in content:
                rejection_reasons.add(content[:80])

        if rejection_reasons:
            result["common_rejection_reasons"] = list(rejection_reasons)[:3]

        # 根据模块类型给出通用拍照建议
        module_tips = _get_module_photo_defaults(module_name)
        result["suggested_angles"] = module_tips.get("angles", ["整体环境照", "问题特写"])
        result["min_photos"] = module_tips.get("min_photos", 2)

        return result

    except Exception as e:
        logger.error(f"获取拍照建议失败: {e}")
        return {
            "item_id": item_id, "module_name": module_name,
            "suggested_angles": ["整体环境照", "问题特写"],
            "common_rejection_reasons": [], "min_photos": 2
        }
    finally:
        db.close()


# ==================== 内部辅助函数 ====================

def _get_recurring_issues(db, project_id: int, module_name: str) -> List[Dict]:
    """从长期记忆获取反复出现问题"""
    try:
        from core.long_memory import LongMemory, MemoryType
        memory = LongMemory()
        memories = memory.get_project_memories(
            project_id=project_id,
            memory_type=MemoryType.RECURRING_ISSUE,
            module_name=module_name,
            limit=10
        )
        return [
            {
                "content": m.content[:100] if hasattr(m, 'content') else str(m)[:100],
                "occurrence_count": m.occurrence_count if hasattr(m, 'occurrence_count') else 1,
                "severity": m.severity if hasattr(m, 'severity') else "一般"
            }
            for m in memories
        ]
    except Exception:
        return []


def _get_last_deducted_items(db, project_id: int, module_name: str) -> List[Dict]:
    """获取上次检查的扣分项"""
    # 查找该项目最近一次任务的该模块评分结果
    last_task = db.query(InspectionTask).filter(
        InspectionTask.project_id == project_id
    ).order_by(InspectionTask.check_date.desc()).first()

    if not last_task:
        return []

    results = db.query(ScoringResult).join(
        InspectionRecord, ScoringResult.record_id == InspectionRecord.record_id
    ).filter(
        InspectionRecord.task_id == last_task.task_id,
        ScoringResult.module_name == module_name,
        ScoringResult.score < 5  # 只取扣分项
    ).all()

    return [
        {
            "item_id": r.item_id,
            "item_name": r.item_name,
            "last_score": float(r.score),
            "scoring_basis": r.scoring_basis[:80] if r.scoring_basis else "",
            "priority": "high" if float(r.score) <= 2 else "medium" if float(r.score) <= 3 else "low"
        }
        for r in sorted(results, key=lambda x: float(x.score))
    ]


def _get_cross_project_issues(db, module_name: str) -> List[Dict]:
    """获取跨项目共性问题"""
    try:
        from core.long_memory import LongMemory, MemoryType
        memory = LongMemory()
        memories = memory.get_cross_project_memories(
            memory_type=MemoryType.RECURRING_ISSUE,
            module_name=module_name,
            limit=5
        )
        return [
            {"content": m.content[:100] if hasattr(m, 'content') else str(m)[:100]}
            for m in memories
        ]
    except Exception:
        return []


def _get_module_score_trend(db, project_id: int, module_name: str) -> Dict:
    """获取模块评分趋势"""
    from core.scoring_memory import get_module_score_trend
    trend = get_module_score_trend(project_id, module_name)
    if trend and trend.get("count", 0) > 0:
        return {
            "avg_score": round(trend["avg_score"], 2),
            "check_count": trend["count"],
            "trend": "improving" if trend["avg_score"] >= 80 else "stable" if trend["avg_score"] >= 60 else "needs_attention"
        }
    return {}


def _get_high_weight_items(module_name: str) -> List[Dict]:
    """获取模板中高权重检查项（无历史数据时的默认建议）"""
    try:
        from api.tasks import load_template_items
        items = load_template_items(module_name, "diecheng")
        if not items:
            items = load_template_items(module_name, "feidiecheng")
        if not items:
            return []

        # 按权重排序，取前5个
        sorted_items = sorted(items, key=lambda x: float(x.get("weight", 0)), reverse=True)
        return [
            {
                "item_id": it["item_id"],
                "item_name": it["item_name"],
                "weight": float(it.get("weight", 0)),
                "check_standard": it.get("check_standard", "")[:60]
            }
            for it in sorted_items[:5]
        ]
    except Exception:
        return []


def _get_module_photo_defaults(module_name: str) -> Dict:
    """根据模块类型返回默认拍照建议"""
    defaults = {
        "客户服务": {"angles": ["服务台全景", "公告栏/宣传资料", "工作人员仪容仪表"], "min_photos": 2},
        "安全管理": {"angles": ["消防设施全景", "安全标识特写", "通道/出口畅通"], "min_photos": 3},
        "EHS及风险管理": {"angles": ["危险品存放区", "安全防护设施", "应急设备"], "min_photos": 3},
        "环境管理": {"angles": ["公共区域清洁状况", "绿化带状况", "垃圾收集点"], "min_photos": 2},
        "机电运维": {"angles": ["设备房全景", "仪表/运行参数", "维保记录"], "min_photos": 3},
        "设施维护": {"angles": ["设施整体状况", "损坏/磨损部位特写", "维修记录"], "min_photos": 2},
        "综合管理": {"angles": ["管理办公区域", "档案/资料", "制度上墙"], "min_photos": 2},
        "财务管理": {"angles": ["收费公示", "财务台账", "收支记录"], "min_photos": 2},
    }
    return defaults.get(module_name, {"angles": ["整体环境照", "问题特写"], "min_photos": 2})
