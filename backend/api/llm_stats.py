"""
LLM用量监控 API
提供详细的LLM调用监控、统计和分析
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, Integer

from database import get_db
from models.models import User, LlmUsageLog
from api.deps import get_current_user

router = APIRouter()


@router.get("/overview", summary="LLM用量总览")
async def get_llm_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """返回LLM用量的核心统计数据"""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_stats = db.query(
        func.sum(LlmUsageLog.total_tokens).label("total_tokens"),
        func.sum(LlmUsageLog.prompt_tokens).label("prompt_tokens"),
        func.sum(LlmUsageLog.completion_tokens).label("completion_tokens"),
        func.count(LlmUsageLog.id).label("total_calls"),
        func.avg(LlmUsageLog.duration_ms).label("avg_duration_ms"),
        func.sum(func.cast(LlmUsageLog.success, Integer)).label("success_count"),
    ).first()

    month_avg_duration = db.query(
        func.avg(LlmUsageLog.duration_ms).label("avg_duration_ms"),
    ).filter(LlmUsageLog.timestamp >= month_start).first()

    month_success = db.query(
        func.count(LlmUsageLog.id).label("total_calls"),
        func.sum(func.cast(LlmUsageLog.success, Integer)).label("success_count"),
    ).filter(LlmUsageLog.timestamp >= month_start).first()

    today_stats = db.query(
        func.sum(LlmUsageLog.total_tokens).label("total_tokens"),
        func.count(LlmUsageLog.id).label("call_count"),
    ).filter(LlmUsageLog.timestamp >= today_start).first()

    month_stats = db.query(
        func.sum(LlmUsageLog.total_tokens).label("total_tokens"),
        func.count(LlmUsageLog.id).label("call_count"),
    ).filter(LlmUsageLog.timestamp >= month_start).first()

    by_model = db.query(
        LlmUsageLog.model_name,
        func.count(LlmUsageLog.id).label("call_count"),
        func.sum(LlmUsageLog.total_tokens).label("total_tokens"),
        func.sum(LlmUsageLog.prompt_tokens).label("prompt_tokens"),
        func.sum(LlmUsageLog.completion_tokens).label("completion_tokens"),
        func.sum(LlmUsageLog.input_cache_hit_tokens).label("cache_hit_tokens"),
        func.sum(LlmUsageLog.input_cache_miss_tokens).label("cache_miss_tokens"),
        func.avg(LlmUsageLog.duration_ms).label("avg_duration_ms"),
        func.sum(func.cast(LlmUsageLog.success, Integer)).label("success_count"),
    ).group_by(LlmUsageLog.model_name).all()

    by_type = db.query(
        LlmUsageLog.call_type,
        func.count(LlmUsageLog.id).label("call_count"),
        func.sum(LlmUsageLog.total_tokens).label("total_tokens"),
        func.avg(LlmUsageLog.duration_ms).label("avg_duration_ms"),
        func.sum(func.cast(LlmUsageLog.success, Integer)).label("success_count"),
    ).group_by(LlmUsageLog.call_type).all()

    return {
        "total": {
            "all_calls": total_stats.total_calls or 0,
            "all_tokens": total_stats.total_tokens or 0,
            "prompt_tokens": total_stats.prompt_tokens or 0,
            "completion_tokens": total_stats.completion_tokens or 0,
            "avg_duration_ms": round(float(total_stats.avg_duration_ms or 0), 1),
            "success_rate": round(total_stats.success_count / total_stats.total_calls * 100, 1) if total_stats.total_calls and total_stats.total_calls > 0 else 100,
        },
        "month_avg_duration_ms": round(float(month_avg_duration.avg_duration_ms or 0), 1),
        "month_success_rate": round(month_success.success_count / month_success.total_calls * 100, 1) if month_success.total_calls and month_success.total_calls > 0 else 100,
        "today": {
            "calls": today_stats.call_count or 0,
            "tokens": today_stats.total_tokens or 0,
        },
        "month": {
            "calls": month_stats.call_count or 0,
            "tokens": month_stats.total_tokens or 0,
        },
        "by_model": [
            {
                "model": r.model_name,
                "calls": r.call_count,
                "tokens": r.total_tokens or 0,
                "prompt_tokens": r.prompt_tokens or 0,
                "completion_tokens": r.completion_tokens or 0,
                "cache_hit_tokens": r.cache_hit_tokens or 0,
                "cache_miss_tokens": r.cache_miss_tokens or 0,
                "avg_duration_ms": round(float(r.avg_duration_ms or 0), 1),
                "success_rate": round(r.success_count / r.call_count * 100, 1) if r.call_count > 0 else 0,
            }
            for r in by_model
        ],
        "by_type": [
            {
                "type": r.call_type,
                "calls": r.call_count,
                "tokens": r.total_tokens or 0,
                "avg_duration_ms": round(float(r.avg_duration_ms or 0), 1),
                "success_rate": round(r.success_count / r.call_count * 100, 1) if r.call_count and r.call_count > 0 else 100,
            }
            for r in by_type
        ],
        "last_month": {
            "calls": _last_month_calls(db),
        },
    }


def _last_month_calls(db):
    """获取上月同期调用次数（用于环比计算）"""
    now = datetime.utcnow()
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # 上月同期
    if now.month == 1:
        last_month_start = now.replace(year=now.year - 1, month=12, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        last_month_start = now.replace(month=now.month - 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    # 上月同等天数
    days_this_month = (now - this_month_start).days + 1
    last_month_end = last_month_start + timedelta(days=days_this_month)

    result = db.query(
        func.count(LlmUsageLog.id).label("call_count"),
        func.sum(LlmUsageLog.total_tokens).label("total_tokens"),
        func.avg(LlmUsageLog.duration_ms).label("avg_duration_ms"),
    ).filter(
        LlmUsageLog.timestamp >= last_month_start,
        LlmUsageLog.timestamp < last_month_end,
    ).first()

    return {
        "calls": result.call_count or 0,
        "tokens": result.total_tokens or 0,
        "avg_duration_ms": round(float(result.avg_duration_ms or 0), 1),
    }


@router.get("/trend", summary="LLM用量趋势")
async def get_llm_trend(
    days: int = Query(default=30, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """返回近N天的LLM用量每日趋势"""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    daily_stats = db.query(
        func.date(LlmUsageLog.timestamp).label("date"),
        LlmUsageLog.model_name,
        func.count(LlmUsageLog.id).label("call_count"),
        func.sum(LlmUsageLog.total_tokens).label("total_tokens"),
        func.sum(LlmUsageLog.prompt_tokens).label("prompt_tokens"),
        func.sum(LlmUsageLog.completion_tokens).label("completion_tokens"),
        func.avg(LlmUsageLog.duration_ms).label("avg_duration_ms"),
        func.sum(func.cast(LlmUsageLog.success, Integer)).label("success_count"),
    ).filter(
        LlmUsageLog.timestamp >= start_date
    ).group_by(
        func.date(LlmUsageLog.timestamp),
        LlmUsageLog.model_name
    ).order_by("date").all()

    daily_map = {}
    for r in daily_stats:
        date_str = str(r.date)
        if date_str not in daily_map:
            daily_map[date_str] = {
                "date": date_str,
                "total_calls": 0,
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "success_count": 0,
                "total_duration_ms": 0,
                "by_model": {},
            }
        daily_map[date_str]["total_calls"] += r.call_count
        daily_map[date_str]["total_tokens"] += r.total_tokens or 0
        daily_map[date_str]["prompt_tokens"] += r.prompt_tokens or 0
        daily_map[date_str]["completion_tokens"] += r.completion_tokens or 0
        daily_map[date_str]["success_count"] += r.success_count or 0
        daily_map[date_str]["total_duration_ms"] += (r.avg_duration_ms or 0) * r.call_count
        daily_map[date_str]["by_model"][r.model_name] = {
            "calls": r.call_count,
            "tokens": r.total_tokens or 0,
            "avg_duration_ms": round(float(r.avg_duration_ms or 0), 1),
        }

    trend = sorted(daily_map.values(), key=lambda x: x["date"])
    for item in trend:
        if item["total_calls"] > 0:
            item["avg_duration_ms"] = round(item["total_duration_ms"] / item["total_calls"], 1)
            item["success_rate"] = round(item["success_count"] / item["total_calls"] * 100, 1)
        else:
            item["avg_duration_ms"] = 0
            item["success_rate"] = 100
        # Clean up internal fields
        item.pop("success_count", None)
        item.pop("total_duration_ms", None)

    return {"trend": trend, "days": days}


@router.get("/records", summary="LLM调用记录列表")
async def get_llm_records(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    model: Optional[str] = None,
    call_type: Optional[str] = None,
    success: Optional[bool] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """分页查询LLM调用记录"""
    query = db.query(LlmUsageLog)

    if model:
        query = query.filter(LlmUsageLog.model_name == model)
    if call_type:
        query = query.filter(LlmUsageLog.call_type == call_type)
    if success is not None:
        query = query.filter(LlmUsageLog.success == success)
    if start_date:
        query = query.filter(func.date(LlmUsageLog.timestamp) >= start_date)
    if end_date:
        query = query.filter(func.date(LlmUsageLog.timestamp) <= end_date)

    total = query.count()

    records = query.order_by(
        LlmUsageLog.timestamp.desc()
    ).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "records": [
            {
                "id": r.id,
                "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M:%S") if r.timestamp else "",
                "model_name": r.model_name,
                "call_type": r.call_type,
                "prompt_tokens": r.prompt_tokens or 0,
                "completion_tokens": r.completion_tokens or 0,
                "total_tokens": r.total_tokens or 0,
                "input_cache_hit_tokens": r.input_cache_hit_tokens or 0,
                "input_cache_miss_tokens": r.input_cache_miss_tokens or 0,
                "duration_ms": r.duration_ms or 0,
                "task_id": r.task_id,
                "success": r.success,
            }
            for r in records
        ]
    }


@router.get("/models", summary="LLM模型列表")
async def get_llm_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """返回所有使用过的LLM模型列表"""
    models = db.query(
        LlmUsageLog.model_name,
        func.count(LlmUsageLog.id).label("call_count"),
        func.sum(LlmUsageLog.total_tokens).label("total_tokens"),
        func.max(LlmUsageLog.timestamp).label("last_used"),
    ).group_by(LlmUsageLog.model_name).all()

    return {
        "models": [
            {
                "name": r.model_name,
                "call_count": r.call_count,
                "total_tokens": r.total_tokens or 0,
                "last_used": r.last_used.strftime("%Y-%m-%d %H:%M:%S") if r.last_used else "",
            }
            for r in models
        ]
    }


@router.get("/cost-estimate", summary="LLM费用估算")
async def get_llm_cost_estimate(
    days: int = Query(default=30, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    估算近N天的LLM调用费用（基于各模型官方定价，精准三档计费）

    DeepSeek 模型使用三档定价：
      1. input_cache_hit_tokens  (¥0.0002/千tokens，90%折扣)
      2. input_cache_miss_tokens  (¥0.002/千tokens)
      3. output_tokens = completion_tokens (¥0.003/千tokens)

    其他模型使用两档定价：
      1. prompt_tokens × prompt_price
      2. completion_tokens × completion_price
    """
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    model_stats = db.query(
        LlmUsageLog.model_name,
        func.sum(LlmUsageLog.prompt_tokens).label("prompt_tokens"),
        func.sum(LlmUsageLog.completion_tokens).label("completion_tokens"),
        func.sum(LlmUsageLog.input_cache_hit_tokens).label("cache_hit_tokens"),
        func.sum(LlmUsageLog.input_cache_miss_tokens).label("cache_miss_tokens"),
        func.count(LlmUsageLog.id).label("call_count"),
        func.avg(LlmUsageLog.duration_ms).label("avg_duration_ms"),
        func.sum(func.cast(LlmUsageLog.success, Integer)).label("success_count"),
    ).filter(
        LlmUsageLog.timestamp >= start_date
    ).group_by(LlmUsageLog.model_name).all()

    # ============================================================
    # 各模型官方定价 (元/千tokens)
    # 通义千问: https://bailian.console.aliyun.com/
    # DeepSeek: https://api-docs.deepseek.com/
    # ============================================================
    # DeepSeek 三档定价（精准）：
    #   input_cache_hit:   ¥0.0002/千tokens (1/10折扣)
    #   input_cache_miss:  ¥0.002/千tokens   (标准价)
    #   output:            ¥0.003/千tokens
    # ============================================================
    PRICING = {
        "qwen-plus": {
            "name": "通义千问Plus",
            "mode": "two_tier",
            "prompt_price": 0.004,
            "completion_price": 0.012,
        },
        "qwen-vl-plus": {
            "name": "通义千问VL-Plus",
            "mode": "two_tier",
            "prompt_price": 0.008,
            "completion_price": 0.02,
        },
        "qwen-max": {
            "name": "通义千问Max",
            "mode": "two_tier",
            "prompt_price": 0.12,
            "completion_price": 0.36,
        },
        "deepseek-chat": {
            "name": "DeepSeek-V3",
            "mode": "three_tier",
            "cache_hit_price": 0.0002,     # ¥0.0002/千tokens
            "cache_miss_price": 0.002,      # ¥0.002/千tokens
            "output_price": 0.003,         # ¥0.003/千tokens
        },
        "deepseek-reasoner": {
            "name": "DeepSeek-R1",
            "mode": "three_tier",
            "cache_hit_price": 0.0002,
            "cache_miss_price": 0.002,
            "output_price": 0.003,
        },
        "default": {
            "name": "其他模型",
            "mode": "two_tier",
            "prompt_price": 0.01,
            "completion_price": 0.03,
        },
    }

    items = []
    total_estimate = 0.0

    for r in model_stats:
        model_key = r.model_name if r.model_name in PRICING else "default"
        pricing = PRICING[model_key]

        if pricing["mode"] == "three_tier":
            # DeepSeek 三档精准计费
            cache_hit = r.cache_hit_tokens or 0
            cache_miss = r.cache_miss_tokens or 0
            # cache_hit + cache_miss 应该等于 prompt_tokens（DeepSeek返回的合并值）
            # 如果历史数据没有细分，用 prompt_tokens × 0.8 估算 cache_miss
            if cache_miss == 0 and cache_hit == 0:
                cache_miss = int((r.prompt_tokens or 0) * 0.8)
                cache_hit = (r.prompt_tokens or 0) - cache_miss

            cache_hit_cost = cache_hit / 1000 * pricing["cache_hit_price"]
            cache_miss_cost = cache_miss / 1000 * pricing["cache_miss_price"]
            output_cost = (r.completion_tokens or 0) / 1000 * pricing["output_price"]
            cost = cache_hit_cost + cache_miss_cost + output_cost
            prompt_cost = cache_hit_cost + cache_miss_cost
            completion_cost = output_cost

            item = {
                "model": r.model_name,
                "model_name_cn": pricing["name"],
                "prompt_tokens": r.prompt_tokens or 0,
                "completion_tokens": r.completion_tokens or 0,
                "cache_hit_tokens": cache_hit,
                "cache_miss_tokens": cache_miss,
                "call_count": r.call_count,
                "success_rate": round(r.success_count / r.call_count * 100, 1) if r.call_count and r.call_count > 0 else 100,
                "avg_duration_ms": round(float(r.avg_duration_ms or 0), 1),
                "cache_hit_cost": round(cache_hit_cost, 4),
                "cache_miss_cost": round(cache_miss_cost, 4),
                "output_cost": round(output_cost, 4),
                "prompt_cost": round(prompt_cost, 4),
                "completion_cost": round(completion_cost, 4),
                "total_cost": round(cost, 4),
                "pricing_mode": "three_tier",
            }
        else:
            # 其他模型两档计费
            prompt_cost = (r.prompt_tokens or 0) / 1000 * pricing["prompt_price"]
            completion_cost = (r.completion_tokens or 0) / 1000 * pricing["completion_price"]
            cost = prompt_cost + completion_cost

            item = {
                "model": r.model_name,
                "model_name_cn": pricing["name"],
                "prompt_tokens": r.prompt_tokens or 0,
                "completion_tokens": r.completion_tokens or 0,
                "call_count": r.call_count,
                "success_rate": round(r.success_count / r.call_count * 100, 1) if r.call_count and r.call_count > 0 else 100,
                "avg_duration_ms": round(float(r.avg_duration_ms or 0), 1),
                "prompt_cost": round(prompt_cost, 4),
                "completion_cost": round(completion_cost, 4),
                "total_cost": round(cost, 4),
                "pricing_mode": "two_tier",
            }

        items.append(item)
        total_estimate += cost

    items.sort(key=lambda x: x["total_cost"], reverse=True)

    return {
        "period_days": days,
        "total_estimate": round(total_estimate, 2),
        "currency": "元（人民币）",
        "models": items,
    }


@router.get("/duration-distribution", summary="LLM耗时分布")
async def get_llm_duration_distribution(
    days: int = Query(default=30, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """返回近N天LLM调用的耗时分布（分桶统计）"""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    durations = db.query(
        LlmUsageLog.duration_ms,
    ).filter(
        LlmUsageLog.timestamp >= start_date,
        LlmUsageLog.duration_ms.isnot(None),
    ).all()

    # 定义耗时分桶
    bucket_defs = [
        ("<1s", lambda d: d < 1000),
        ("1-3s", lambda d: 1000 <= d < 3000),
        ("3-5s", lambda d: 3000 <= d < 5000),
        ("5-10s", lambda d: 5000 <= d < 10000),
        ("10-30s", lambda d: 10000 <= d < 30000),
        ("30-60s", lambda d: 30000 <= d < 60000),
        (">60s", lambda d: d >= 60000),
    ]

    buckets = [{"label": label, "count": 0} for label, _ in bucket_defs]

    for row in durations:
        d = row.duration_ms or 0
        for i, (_, matcher) in enumerate(bucket_defs):
            if matcher(d):
                buckets[i]["count"] += 1
                break

    return {"buckets": buckets, "days": days}
