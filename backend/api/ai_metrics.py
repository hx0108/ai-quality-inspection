"""
AI效果评估 API
基于 scoring_results 实时计算评分一致性、置信度分布、偏差检测等指标
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer, case

from database import get_db, SessionLocal
from models.models import User, ScoringResult, LlmUsageLog
from api.deps import get_current_user, check_role

router = APIRouter()


@router.get("/overview", summary="AI效果评估总览")
async def get_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回AI评分核心效果指标"""
    # 总体统计
    stats = db.query(
        func.count(ScoringResult.id).label("total"),
        func.sum(case((ScoringResult.is_edited == True, 1), else_=0)).label("edited"),
        func.sum(case((ScoringResult.is_fallback == True, 1), else_=0)).label("fallback"),
        func.avg(ScoringResult.confidence_score).label("avg_confidence"),
    ).first()

    total = stats.total or 0
    edited = stats.edited or 0
    fallback = stats.fallback or 0
    consistency_rate = round((1 - edited / total) * 100, 1) if total > 0 else 100
    fallback_rate = round(fallback / total * 100, 1) if total > 0 else 0

    # 超时统计（从 LLM 日志）
    timeout_count = db.query(func.count(LlmUsageLog.id)).filter(
        LlmUsageLog.success == False
    ).scalar() or 0
    total_llm_calls = db.query(func.count(LlmUsageLog.id)).scalar() or 0
    timeout_rate = round(timeout_count / total_llm_calls * 100, 1) if total_llm_calls > 0 else 0

    # 人工复核积压
    review_backlog = db.query(func.count(ScoringResult.id)).filter(
        ScoringResult.needs_human_review == True,
        ScoringResult.human_reviewed == False,
    ).scalar() or 0

    # 边缘案例（低置信度评分）
    edge_cases = db.query(func.count(ScoringResult.id)).filter(
        ScoringResult.confidence_score.isnot(None),
        ScoringResult.confidence_score < 0.5,
    ).scalar() or 0

    # 效率提升：平均 AI 评分耗时 vs 人工评分估计（假设人工 5 分钟/项）
    avg_llm_ms = db.query(func.avg(LlmUsageLog.duration_ms)).filter(
        LlmUsageLog.call_type == "scoring"
    ).scalar() or 0
    human_min = 5 * 60 * 1000  # 5分钟 in ms
    efficiency = round(human_min / avg_llm_ms, 1) if avg_llm_ms > 0 else 0

    # 环比（与上月对比）
    now = datetime.utcnow()
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = this_month_start - timedelta(days=30)

    this_edited = db.query(func.count(ScoringResult.id)).filter(
        ScoringResult.scored_at >= this_month_start,
        ScoringResult.is_edited == True,
    ).scalar() or 0
    this_total = db.query(func.count(ScoringResult.id)).filter(
        ScoringResult.scored_at >= this_month_start,
    ).scalar() or 0
    last_edited = db.query(func.count(ScoringResult.id)).filter(
        ScoringResult.scored_at >= last_month_start,
        ScoringResult.scored_at < this_month_start,
        ScoringResult.is_edited == True,
    ).scalar() or 0
    last_total = db.query(func.count(ScoringResult.id)).filter(
        ScoringResult.scored_at >= last_month_start,
        ScoringResult.scored_at < this_month_start,
    ).scalar() or 0

    this_consistency = round((1 - this_edited / this_total) * 100, 1) if this_total > 0 else 100
    last_consistency = round((1 - last_edited / last_total) * 100, 1) if last_total > 0 else 100
    consistency_trend = round(this_consistency - last_consistency, 1)

    return {
        "consistency_rate": consistency_rate,
        "consistency_trend": consistency_trend,
        "fallback_rate": fallback_rate,
        "fallback_trend": 0,
        "timeout_rate": timeout_rate,
        "timeout_trend": 0,
        "human_review_backlog": review_backlog,
        "human_review_trend": 0,
        "edge_case_count": edge_cases,
        "edge_case_trend": 0,
        "efficiency_multiplier": efficiency,
        "avg_confidence": round(float(stats.avg_confidence or 0), 2),
    }


@router.get("/trend", summary="一致性率趋势")
async def get_trend(
    days: int = Query(default=30, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回近N天的一致性率、降级率、平均置信度趋势"""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    daily = db.query(
        func.date(ScoringResult.scored_at).label("date"),
        func.count(ScoringResult.id).label("total"),
        func.sum(case((ScoringResult.is_edited == True, 1), else_=0)).label("edited"),
        func.sum(case((ScoringResult.is_fallback == True, 1), else_=0)).label("fallback"),
        func.avg(ScoringResult.confidence_score).label("avg_confidence"),
    ).filter(
        ScoringResult.scored_at >= start_date,
    ).group_by(
        func.date(ScoringResult.scored_at),
    ).order_by("date").all()

    trend = []
    for r in daily:
        total = r.total or 0
        edited = r.edited or 0
        fallback = r.fallback or 0
        trend.append({
            "date": str(r.date),
            "consistency_rate": round((1 - edited / total) * 100, 1) if total > 0 else 100,
            "fallback_rate": round(fallback / total * 100, 1) if total > 0 else 0,
            "avg_confidence": round(float(r.avg_confidence or 0), 2),
            "total_scored": total,
        })

    return {"trend": trend, "days": days}


@router.get("/module-stats", summary="各模块评分统计")
async def get_module_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回各模块的评分一致性、置信度、修改率等"""
    from api.tasks import MODULE_NAMES

    modules = db.query(
        ScoringResult.module_name,
        func.count(ScoringResult.id).label("total"),
        func.avg(ScoringResult.score).label("avg_score"),
        func.avg(ScoringResult.confidence_score).label("avg_confidence"),
        func.sum(case((ScoringResult.is_edited == True, 1), else_=0)).label("edited"),
        func.sum(case((ScoringResult.is_fallback == True, 1), else_=0)).label("fallback"),
    ).group_by(ScoringResult.module_name).all()

    result = []
    for m in modules:
        total = m.total or 0
        edited = m.edited or 0
        fallback = m.fallback or 0
        result.append({
            "module_name": m.module_name,
            "total_scored": total,
            "consistency_rate": round((1 - edited / total) * 100, 1) if total > 0 else 100,
            "avg_score": round(float(m.avg_score or 0), 1),
            "avg_confidence": round(float(m.avg_confidence or 0), 2),
            "edit_rate": round(edited / total * 100, 1) if total > 0 else 0,
            "fallback_rate": round(fallback / total * 100, 1) if total > 0 else 0,
        })

    # Ensure all 8 modules appear
    existing = {m["module_name"] for m in result}
    for name in MODULE_NAMES:
        if name not in existing:
            result.append({
                "module_name": name,
                "total_scored": 0,
                "consistency_rate": 100,
                "avg_score": 0,
                "avg_confidence": 0,
                "edit_rate": 0,
                "fallback_rate": 0,
            })

    return {"modules": sorted(result, key=lambda x: x["total_scored"], reverse=True)}


@router.get("/confidence-calibration", summary="置信度校准数据")
async def get_confidence_calibration(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回置信度分布和校准数据"""
    # 置信度分布
    high = db.query(func.count(ScoringResult.id)).filter(
        ScoringResult.confidence_score >= 0.8
    ).scalar() or 0
    medium = db.query(func.count(ScoringResult.id)).filter(
        ScoringResult.confidence_score >= 0.5,
        ScoringResult.confidence_score < 0.8,
    ).scalar() or 0
    low = db.query(func.count(ScoringResult.id)).filter(
        ScoringResult.confidence_score < 0.5,
        ScoringResult.confidence_score > 0,
    ).scalar() or 0
    no_conf = db.query(func.count(ScoringResult.id)).filter(
        ScoringResult.confidence_score.is_(None),
    ).scalar() or 0

    # 置信度分桶校准
    buckets = [
        ("0-0.2", 0, 0.2),
        ("0.2-0.4", 0.2, 0.4),
        ("0.4-0.6", 0.4, 0.6),
        ("0.6-0.8", 0.6, 0.8),
        ("0.8-1.0", 0.8, 1.01),
    ]
    calibration = []
    for label, lo, hi in buckets:
        count = db.query(func.count(ScoringResult.id)).filter(
            ScoringResult.confidence_score >= lo,
            ScoringResult.confidence_score < hi,
        ).scalar() or 0
        # 该桶中被编辑的比例（越低说明AI越准）
        edited = db.query(func.count(ScoringResult.id)).filter(
            ScoringResult.confidence_score >= lo,
            ScoringResult.confidence_score < hi,
            ScoringResult.is_edited == True,
        ).scalar() or 0
        calibration.append({
            "bucket": label,
            "count": count,
            "actual_consistency_rate": round((1 - edited / count) * 100, 1) if count > 0 else 0,
        })

    return {
        "distribution": {"high": high, "medium": medium, "low": low},
        "calibration": calibration,
    }


@router.get("/bias-and-edges", summary="偏差检测与边缘案例")
async def get_bias_and_edges(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回模块偏差、检查员偏差和边缘案例"""
    # 模块偏差：各模块的编辑率偏差
    modules = db.query(
        ScoringResult.module_name,
        func.count(ScoringResult.id).label("total"),
        func.sum(case((ScoringResult.is_edited == True, 1), else_=0)).label("edited"),
    ).group_by(ScoringResult.module_name).all()

    overall_edit_rate = 0
    total_all = sum(m.total or 0 for m in modules)
    total_edited = sum(m.edited or 0 for m in modules)
    if total_all > 0:
        overall_edit_rate = total_edited / total_all

    module_deviations = []
    for m in modules:
        total = m.total or 0
        edited = m.edited or 0
        mod_rate = edited / total if total > 0 else 0
        deviation = round(abs(mod_rate - overall_edit_rate) * 100, 1)
        module_deviations.append({
            "module_name": m.module_name,
            "edit_rate": round(mod_rate * 100, 1),
            "deviation": deviation,
        })
    module_deviations.sort(key=lambda x: x["deviation"], reverse=True)

    # 边缘案例：低置信度评分项
    edge_items = db.query(
        ScoringResult.item_name,
        ScoringResult.module_name,
        func.count(ScoringResult.id).label("occurrence_count"),
        func.sum(case((ScoringResult.is_edited == True, 1), else_=0)).label("hit_count"),
        func.avg(ScoringResult.confidence_score).label("avg_conf"),
    ).filter(
        ScoringResult.confidence_score.isnot(None),
        ScoringResult.confidence_score < 0.6,
    ).group_by(
        ScoringResult.item_name,
        ScoringResult.module_name,
    ).order_by(func.count(ScoringResult.id).desc()).limit(10).all()

    edge_cases = []
    for i, e in enumerate(edge_items):
        occ = e.occurrence_count or 0
        hit = e.hit_count or 0
        edge_cases.append({
            "case_id": f"EDGE-{i+1:03d}",
            "title": e.item_name or "未知项",
            "module_name": e.module_name,
            "occurrence_count": occ,
            "hit_count": hit,
            "hit_rate": round(hit / occ * 100, 1) if occ > 0 else 0,
            "review_status": "pending",
        })

    return {
        "bias": {
            "module_deviations": module_deviations,
            "inspector_deviations": [],
        },
        "edge_cases": edge_cases,
    }


# ==================== 智能诊断（P1：确定性归因）====================

@router.get("/diagnosis", summary="获取AI评分智能诊断结果")
async def get_diagnosis(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取最新诊断周期的问题+根因+证据（只读）。若无结果则返回空列表。"""
    from core.diagnosis_engine import get_latest_diagnosis
    results = get_latest_diagnosis(db, limit=limit)
    # 按严重度排序展示
    sev_order = {"高": 0, "中": 1, "低": 2}
    results.sort(key=lambda x: (sev_order.get(x["severity"], 9), x["module_name"]))
    return {"total": len(results), "items": results, "period": results[0]["period"] if results else None}


@router.post("/diagnosis/run", summary="手动触发诊断（管理员）")
async def run_diagnosis(
    days: int = Query(30, ge=1, le=365),
    use_llm: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role(["admin"])),
):
    """手动触发一次诊断（重新检测+归因+LLM建议）。默认分析最近30天数据。"""
    from core.diagnosis_engine import run_diagnosis as _run
    results = await _run(db, days=days, use_llm=use_llm)
    return {
        "message": f"诊断完成，发现 {len(results)} 条异常",
        "total": len(results),
        "items": [
            {
                "module_name": r["module_name"],
                "severity": r["severity"],
                "problem": r["problem"],
                "pattern": r["pattern"],
                "root_cause": r.get("llm_root_cause") or r["root_cause"],
                "suggestion": r.get("suggestion"),
            }
            for r in results
        ],
    }

