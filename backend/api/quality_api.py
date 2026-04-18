"""
品质检查相关API
包含偏见检测、边缘案例、评估指标等接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from database import get_db
from core.bias_detector import BiasDetector
from core.edge_case_detector import EdgeCaseDetector, EdgeCaseType
from core.metrics_collector import MetricsCollector
from api.deps import get_current_user, check_role

router = APIRouter(tags=["品质检查"])


# ==================== 偏见检测API ====================

class BiasAlertResponse(BaseModel):
    detection_id: str
    dimension_type: str
    dimension_value: str
    total_samples: int
    ai_mean_score: float
    human_mean_score: float
    deviation_rate: float
    is_alert: bool
    alert_level: Optional[str]
    detected_at: str


class BiasSummaryResponse(BaseModel):
    period_days: int
    module_bias: dict
    inspector_bias: dict
    active_alerts: int


@router.get("/bias/alerts", response_model=List[BiasAlertResponse])
def get_bias_alerts(
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user)
):
    """获取当前活跃的偏见告警列表"""
    detector = BiasDetector()
    alerts = detector.get_active_alerts()[:limit]
    return [
        BiasAlertResponse(
            detection_id=a.detection_id,
            dimension_type=a.dimension_type,
            dimension_value=a.dimension_value,
            total_samples=a.total_samples,
            ai_mean_score=float(a.ai_mean_score or 0),
            human_mean_score=float(a.human_mean_score or 0),
            deviation_rate=float(a.deviation_rate or 0),
            is_alert=a.is_alert,
            alert_level=a.alert_level,
            detected_at=a.detected_at.strftime("%Y-%m-%d %H:%M:%S") if a.detected_at else "",
        )
        for a in alerts
    ]


@router.get("/bias/summary", response_model=BiasSummaryResponse)
def get_bias_summary(
    period_days: int = Query(30, ge=1, le=365),
    current_user=Depends(get_current_user)
):
    """获取偏见检测摘要"""
    detector = BiasDetector()
    return detector.get_bias_summary(period_days)


@router.post("/bias/detect")
def trigger_bias_detection(
    period_days: int = Query(30, ge=1, le=365),
    current_user=Depends(check_role(["admin", "inspector"]))
):
    """手动触发偏见检测"""
    detector = BiasDetector()
    results = detector.detect_all_biases(period_days)
    return {
        "status": "completed",
        "message": f"检测完成，发现{len(results)}条记录",
        "detections": len(results),
        "alerts": sum(1 for r in results if r.is_alert),
    }


@router.get("/bias/trend/{dimension_type}/{dimension_value}")
def get_bias_trend(
    dimension_type: str,
    dimension_value: str,
    months: int = Query(6, ge=1, le=12),
    current_user=Depends(get_current_user)
):
    """获取偏见趋势数据"""
    if dimension_type not in ["module", "inspector"]:
        raise HTTPException(400, "dimension_type必须是module或inspector")

    detector = BiasDetector()
    trend = detector.get_bias_trend(dimension_type, dimension_value, months)
    return {"dimension_type": dimension_type, "dimension_value": dimension_value, "trend": trend}


# ==================== 边缘案例API ====================

class EdgeCaseResponse(BaseModel):
    case_id: str
    case_type: str
    case_type_display: str
    module_name: Optional[str]
    item_id: Optional[str]
    title: str
    description: Optional[str]
    typical_input: Optional[str]
    expected_score_range: Optional[str]
    occurrence_count: int
    hit_count: int
    miss_count: int
    hit_rate: float
    review_status: str
    resolution_status: str
    is_active: bool
    created_at: str


class EdgeCaseStatsResponse(BaseModel):
    total_active_cases: int
    pending_review: int
    approved: int
    by_type: List[dict]


@router.get("/edge-case/stats", response_model=EdgeCaseStatsResponse)
def get_edge_case_stats(current_user=Depends(get_current_user)):
    """获取边缘案例统计"""
    detector = EdgeCaseDetector()
    stats = detector.get_case_stats()
    return EdgeCaseStatsResponse(**stats)


@router.get("/edge-case/pending", response_model=List[EdgeCaseResponse])
def get_pending_review_cases(
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(get_current_user)
):
    """获取待审核的边缘案例"""
    detector = EdgeCaseDetector()
    cases = detector.get_pending_review_cases(limit)
    return [
        EdgeCaseResponse(
            case_id=c.case_id,
            case_type=c.case_type,
            case_type_display=EdgeCaseType.display_name(c.case_type),
            module_name=c.module_name,
            item_id=c.item_id,
            title=c.title,
            description=c.description,
            typical_input=c.typical_input,
            expected_score_range=c.expected_score_range,
            occurrence_count=c.occurrence_count,
            hit_count=c.hit_count or 0,
            miss_count=c.miss_count or 0,
            hit_rate=float(c.hit_rate or 0),
            review_status=c.review_status,
            resolution_status=c.resolution_status,
            is_active=c.is_active,
            created_at=c.created_at.strftime("%Y-%m-%d %H:%M:%S") if c.created_at else "",
        )
        for c in cases
    ]


@router.post("/edge-case/{case_id}/approve")
def approve_edge_case(
    case_id: str, reviewer_id: int, resolution_note: Optional[str] = None,
    current_user=Depends(check_role(["admin", "inspector"]))
):
    """审核通过边缘案例"""
    detector = EdgeCaseDetector()
    success = detector.approve_case(case_id, reviewer_id, resolution_note)
    if not success:
        raise HTTPException(404, "边缘案例不存在")
    return {"status": "success", "message": "审核通过"}


@router.post("/edge-case/{case_id}/reject")
def reject_edge_case(
    case_id: str, reviewer_id: int, reason: str,
    current_user=Depends(check_role(["admin", "inspector"]))
):
    """驳回边缘案例"""
    if not reason:
        raise HTTPException(400, "驳回原因不能为空")

    detector = EdgeCaseDetector()
    success = detector.reject_case(case_id, reviewer_id, reason)
    if not success:
        raise HTTPException(404, "边缘案例不存在")
    return {"status": "success", "message": "已驳回"}


@router.get("/edge-case/types")
def get_edge_case_types(current_user=Depends(get_current_user)):
    """获取边缘案例类型列表"""
    return [
        {"type": t, "display": EdgeCaseType.display_name(t)}
        for t in EdgeCaseType.all_types()
    ]


# ==================== 评估指标API ====================

class RealtimeStatsResponse(BaseModel):
    today: dict
    pending: dict
    alerts: dict


@router.get("/metrics/realtime", response_model=RealtimeStatsResponse)
def get_realtime_stats(current_user=Depends(get_current_user)):
    """获取实时统计数据"""
    collector = MetricsCollector()
    stats = collector.get_realtime_stats()
    return RealtimeStatsResponse(**stats)


@router.get("/metrics/trend")
def get_metrics_trend(
    months: int = Query(3, ge=1, le=12),
    current_user=Depends(get_current_user)
):
    """获取指标趋势"""
    collector = MetricsCollector()
    trend = collector.get_metrics_trend(months)
    return {"trend": trend}


@router.get("/metrics/latest")
def get_latest_metrics(current_user=Depends(get_current_user)):
    """获取最新指标记录"""
    collector = MetricsCollector()
    record = collector.get_latest_metrics()
    if not record:
        return {"message": "暂无指标记录"}
    return {
        "record_id": record.record_id,
        "period_start": record.period_start,
        "period_end": record.period_end,
        "total_scored": record.total_scored,
        "total_edited": record.total_edited,
        "consistency_rate": float(record.consistency_rate or 0),
        "accuracy_rate": float(record.accuracy_rate or 0) if record.accuracy_rate else None,
        "high_confidence_count": record.high_confidence_count,
        "medium_confidence_count": record.medium_confidence_count,
        "low_confidence_count": record.low_confidence_count,
        "max_module_deviation": float(record.max_module_deviation or 0),
        "max_inspector_deviation": float(record.max_inspector_deviation or 0),
        "active_bias_alerts": record.active_bias_alerts,
        "edge_cases_detected": record.edge_cases_detected,
        "edge_cases_hit_rate": float(record.edge_cases_hit_rate or 0),
        "avg_response_time_ms": record.avg_response_time_ms,
        "fallback_count": record.fallback_count,
        "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S") if record.created_at else "",
    }


@router.post("/metrics/collect")
def trigger_metrics_collection(
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
    golden_dataset_accuracy: Optional[float] = None,
    current_user=Depends(check_role(["admin", "inspector"]))
):
    """手动触发指标收集"""
    collector = MetricsCollector()
    try:
        if period_start:
            start = period_start
        else:
            from datetime import timedelta
            start = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        if period_end:
            end = period_end
        else:
            end = datetime.now().strftime("%Y-%m-%d")

        record = collector.save_metrics_record(start, end, golden_dataset_accuracy)
        return {
            "status": "success",
            "record_id": record.record_id,
            "message": f"指标已记录，周期: {start} 至 {end}",
        }
    except Exception as e:
        raise HTTPException(500, f"指标收集失败: {str(e)}")


# ==================== 技能编译 & 自我改进 API ====================

@router.post("/compile-rules")
async def trigger_rule_compilation(
    module_name: Optional[str] = None,
    current_user=Depends(check_role(["admin", "inspector"]))
):
    """手动触发评分规则编译（技能编译）"""
    try:
        from core.rule_compiler import run_compilation
        rules = await run_compilation(module_name)
        return {
            "status": "success",
            "compiled_count": len(rules),
            "message": f"编译完成，生成 {len(rules)} 条规则",
        }
    except Exception as e:
        raise HTTPException(500, f"规则编译失败: {str(e)}")


@router.get("/scoring-rules")
def get_scoring_rules(
    module_name: Optional[str] = None,
    current_user=Depends(get_current_user)
):
    """查询编译后的评分规则"""
    from database import SessionLocal
    from models.models import ScoringRule
    db = SessionLocal()
    try:
        query = db.query(ScoringRule).filter(ScoringRule.is_active == True)
        if module_name:
            query = query.filter(ScoringRule.module_name == module_name)
        rules = query.order_by(ScoringRule.source_case_count.desc()).limit(50).all()
        return {
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "module_name": r.module_name,
                    "rule_text": r.rule_text,
                    "score_directive": r.score_directive,
                    "issue_keyword": r.issue_keyword,
                    "source_case_count": r.source_case_count,
                    "support_rate": float(r.support_rate or 0),
                    "avg_ai_deviation": float(r.avg_ai_deviation or 0),
                    "is_verified": r.is_verified,
                    "compiled_at": r.compiled_at.isoformat() if r.compiled_at else None,
                }
                for r in rules
            ]
        }
    finally:
        db.close()


@router.post("/curate-memories")
def trigger_memory_curation(
    project_id: Optional[int] = None,
    current_user=Depends(check_role(["admin", "inspector"]))
):
    """手动触发记忆策展"""
    try:
        from core.memory_curator import run_curation
        result = run_curation(project_id)
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(500, f"记忆策展失败: {str(e)}")


@router.post("/self-improve")
def trigger_self_improvement(
    current_user=Depends(check_role(["admin", "inspector"]))
):
    """手动触发自我改进循环"""
    try:
        from core.self_improver import run_improvement
        result = run_improvement()
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(500, f"自我改进失败: {str(e)}")


@router.get("/scoring-directives")
def get_scoring_directives(current_user=Depends(get_current_user)):
    """查询活跃的评分修正指令"""
    from core.self_improver import SelfImprover
    improver = SelfImprover()
    return {"directives": improver.get_all_active_directives()}


@router.put("/scoring-directives/{directive_id}/toggle")
def toggle_scoring_directive(
    directive_id: str, active: bool = True,
    current_user=Depends(check_role(["admin"]))
):
    """启用/禁用修正指令"""
    from database import SessionLocal
    from models.models import ScoringDirective
    db = SessionLocal()
    try:
        d = db.query(ScoringDirective).filter(
            ScoringDirective.directive_id == directive_id
        ).first()
        if not d:
            raise HTTPException(404, "指令不存在")
        d.is_active = active
        d.updated_at = datetime.utcnow()
        db.commit()
        return {"status": "success", "directive_id": directive_id, "is_active": active}
    finally:
        db.close()