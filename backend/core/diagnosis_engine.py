"""
AI评分诊断引擎（P1：确定性归因，不含LLM）

职责：
1. 检测异常（基于阈值的确定性规则）
2. 根因归因（统计聚类 + 模式分类，确定性）
3. 落地诊断结果到 diagnosis_results 表

设计原则（CLAUDE.md #7）：模型是裁判不是操作员。
本引擎全部用确定性代码：阈值判断、SQL聚合、规则映射。LLM根因解释留给P2。
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, case, text
from models.models import ScoringResult
from core.logger import get_logger

logger = get_logger("diagnosis_engine")


# ==================== 表结构（自包含，幂等创建）====================
def ensure_diagnosis_table(db: Session):
    """确保 diagnosis_results 表存在（幂等，安全）。"""
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS diagnosis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            diagnosis_id VARCHAR(50) UNIQUE,
            module_name VARCHAR(50),
            rule_id VARCHAR(50),
            problem TEXT,
            severity VARCHAR(10),
            pattern VARCHAR(20),
            root_cause TEXT,
            evidence_json TEXT,
            status VARCHAR(20) DEFAULT 'active',
            period_start VARCHAR(10),
            period_end VARCHAR(10),
            created_at DATETIME
        )
    """))
    # P2: 增加 LLM 根因和改进建议列（幂等）
    try:
        db.execute(text("ALTER TABLE diagnosis_results ADD COLUMN llm_root_cause TEXT"))
    except Exception:
        pass
    try:
        db.execute(text("ALTER TABLE diagnosis_results ADD COLUMN suggestion_json TEXT"))
    except Exception:
        pass
    db.commit()


# ==================== Step 1: 计算各模块指标 ====================
def _compute_module_metrics(db: Session, since: datetime):
    """计算每个模块的核心指标（一致性率、降级率、编辑率、平均置信度等）。"""
    rows = db.query(
        ScoringResult.module_name,
        func.count(ScoringResult.id).label("total"),
        func.sum(case((ScoringResult.is_edited == True, 1), else_=0)).label("edited"),
        func.sum(case((ScoringResult.is_fallback == True, 1), else_=0)).label("fallback"),
        func.avg(ScoringResult.confidence_score).label("avg_conf"),
        func.sum(case((ScoringResult.confidence_score < 0.6, 1), else_=0)).label("low_conf"),
    ).filter(
        ScoringResult.scored_at >= since
    ).group_by(ScoringResult.module_name).all()

    metrics = []
    for r in rows:
        total = r.total or 0
        if total == 0:
            continue
        edited = r.edited or 0
        fallback = r.fallback or 0
        low_conf = r.low_conf or 0
        metrics.append({
            "module_name": r.module_name,
            "total": total,
            "edited": edited,
            "consistency_rate": round((1 - edited / total) * 100, 1),
            "edit_rate": round(edited / total * 100, 1),
            "fallback_rate": round(fallback / total * 100, 1),
            "avg_confidence": round(float(r.avg_conf or 0), 2),
            "low_conf_ratio": round(low_conf / total, 2),
        })
    return metrics


# ==================== Step 2: 异常检测（相对离群 + 绝对底线）====================
def _detect_anomalies(metrics):
    """
    对每个模块检测异常。
    采用双重策略：
    1. 相对离群：某模块比所有模块的均值差很多（即使绝对值不差，也是相对短板）
    2. 绝对底线：硬性质量红线（如一致性<85%）
    """
    if not metrics:
        return []

    # 计算各指标的均值（用于相对离群判定）
    import statistics
    edit_rates = [m["edit_rate"] for m in metrics]
    fallback_rates = [m["fallback_rate"] for m in metrics]
    low_conf_ratios = [m["low_conf_ratio"] for m in metrics]
    confidences = [m["avg_confidence"] for m in metrics]
    mean_edit = statistics.mean(edit_rates) if edit_rates else 0
    mean_fallback = statistics.mean(fallback_rates) if fallback_rates else 0
    mean_lowconf = statistics.mean(low_conf_ratios) if low_conf_ratios else 0

    anomalies = []
    for m in metrics:
        mod = m["module_name"]
        # 规则1：编辑率相对离群（比均值高2倍以上，且编辑次数≥3才有意义）
        if m["edit_rate"] > mean_edit * 2 and m["edited"] >= 3:
            ratio = round(m["edit_rate"] / mean_edit, 1) if mean_edit > 0 else 999
            anomalies.append({
                "module_name": mod,
                "rule_id": "MODULE_EDIT_RATE_HIGH",
                "problem": f"{mod}模块编辑率{m['edit_rate']}%，是平均水平({round(mean_edit,1)}%)的{ratio}倍，人工修改最频繁",
                "severity": "高" if ratio >= 5 else "中",
                "metrics": m,
            })
        # 规则1b：编辑率绝对底线
        elif m["consistency_rate"] < 85:
            anomalies.append({
                "module_name": mod,
                "rule_id": "MODULE_CONSISTENCY_LOW",
                "problem": f"{mod}模块一致性率仅{m['consistency_rate']}%，低于85%质量红线",
                "severity": "高",
                "metrics": m,
            })
        # 规则2：降级率相对离群
        if m["fallback_rate"] > mean_fallback * 2 and m["fallback_rate"] > 5:
            anomalies.append({
                "module_name": mod,
                "rule_id": "MODULE_FALLBACK_HIGH",
                "problem": f"{mod}模块降级率{m['fallback_rate']}%，AI评分不稳定（均值{round(mean_fallback,1)}%）",
                "severity": "中",
                "metrics": m,
            })
        # 规则3：低置信度相对离群
        if m["low_conf_ratio"] > mean_lowconf * 2 and m["low_conf_ratio"] > 0.1:
            anomalies.append({
                "module_name": mod,
                "rule_id": "LOW_CONFIDENCE_CLUSTER",
                "problem": f"{mod}模块低置信度评分占比{round(m['low_conf_ratio']*100)}%，AI常拿不准",
                "severity": "中",
                "metrics": m,
            })
        # 规则4：过度自信（高置信度 + 编辑率离群 = 盲目自信，最危险）
        if m["avg_confidence"] > 0.8 and m["edit_rate"] > mean_edit * 2 and m["edited"] >= 3:
            anomalies.append({
                "module_name": mod,
                "rule_id": "OVERCONFIDENT_BIAS",
                "problem": f"{mod}模块AI过度自信（置信{m['avg_confidence']}但编辑率{m['edit_rate']}%）",
                "severity": "高",
                "metrics": m,
            })
    return anomalies


# ==================== Step 3: 根因归因（统计聚类 + 模式分类）====================
def _attribute(db: Session, anomaly, since: datetime):
    """对单个异常做根因归因：聚类修改热点 + 分类偏差模式。"""
    module = anomaly["module_name"]

    # 聚类：该模块被人工修改的评分项，按检查项分组
    edited_rows = db.query(
        ScoringResult.item_id,
        ScoringResult.item_name,
        func.count(ScoringResult.id).label("edit_count"),
        func.avg(ScoringResult.original_score - ScoringResult.score).label("bias_direction"),
        func.avg(ScoringResult.confidence_score).label("avg_conf"),
    ).filter(
        ScoringResult.module_name == module,
        ScoringResult.is_edited == True,
        ScoringResult.scored_at >= since,
    ).group_by(ScoringResult.item_id, ScoringResult.item_name).order_by(
        func.count(ScoringResult.id).desc()
    ).limit(5).all()

    hotspots = []
    for r in edited_rows:
        hotspots.append({
            "item_id": r.item_id,
            "item_name": r.item_name or "",
            "edit_count": r.edit_count,
            "bias_direction": round(float(r.bias_direction or 0), 2),
            "avg_confidence": round(float(r.avg_conf or 0), 2),
        })

    # 分类偏差模式（基于热点平均偏差方向 + 置信度）
    pattern = _classify_pattern(anomaly["metrics"], hotspots)

    # 确定性根因（P1用模板，P2接LLM）
    root_cause = _deterministic_root_cause(anomaly, hotspots, pattern)

    return {
        "module_name": module,
        "rule_id": anomaly["rule_id"],
        "problem": anomaly["problem"],
        "severity": anomaly["severity"],
        "pattern": pattern,
        "root_cause": root_cause,
        "evidence": {
            "module_metrics": anomaly["metrics"],
            "hotspots": hotspots,
            "sample_size": anomaly["metrics"]["total"],
        },
    }


def _classify_pattern(metrics, hotspots):
    """根据偏差方向和置信度分类偏差模式。"""
    if not hotspots:
        return "数据不足"
    avg_bias = sum(h["bias_direction"] for h in hotspots) / len(hotspots)
    avg_conf = sum(h["avg_confidence"] for h in hotspots) / len(hotspots)
    if avg_bias > 0.5 and avg_conf > 0.8:
        return "漏检型"      # AI自信地判合格，实际有问题
    if avg_bias < -0.5 and avg_conf > 0.8:
        return "过严型"      # AI自信地扣分，实际合格
    if avg_conf < 0.6:
        return "不确定型"    # AI自己拿不准
    if avg_conf > 0.85 and metrics["edit_rate"] > 10:
        return "盲目自信型"
    return "混合型"


def _deterministic_root_cause(anomaly, hotspots, pattern):
    """P1：用确定性模板生成根因（P2替换为LLM）。"""
    rule_id = anomaly["rule_id"]
    module = anomaly["module_name"]
    if not hotspots:
        return f"{module}模块指标异常，但近期无足够人工修改样本，建议持续观察。"
    top = hotspots[0]
    item_name = top["item_name"] or top["item_id"]
    if rule_id == "OVERCONFIDENT_BIAS":
        return f"AI对'{item_name}'等检查项过度自信（置信度高但被频繁修改），评分依据可能未覆盖该类问题的真实判定标准。"
    if pattern == "漏检型":
        return f"'{item_name}'检查项AI多次判合格但人工发现存在问题，评分规则可能未覆盖该类隐蔽缺陷。"
    if pattern == "过严型":
        return f"'{item_name}'检查项AI频繁扣分但人工判定合格，评分标准可能偏严，需校准扣分阈值。"
    if pattern == "不确定型":
        return f"AI对'{item_name}'等检查项置信度低，评分依据不充分，建议补充案例或细化评分规则。"
    return f"'{item_name}'检查项被人工修改{top['edit_count']}次，是{module}模块偏差的主要来源。"


# ==================== 主入口 ====================
async def run_diagnosis(db: Session, days: int = 30, use_llm: bool = True):
    """
    运行完整诊断流程：检测 → 归因 → (可选)LLM增强建议 → 存储。
    返回本周期诊断结果列表。
    """
    ensure_diagnosis_table(db)
    since = datetime.utcnow() - timedelta(days=days)
    period_end = datetime.utcnow().strftime("%Y-%m-%d")
    period_start = since.strftime("%Y-%m-%d")

    metrics = _compute_module_metrics(db, since)
    anomalies = _detect_anomalies(metrics)

    # 清除本周期旧诊断，重新生成
    db.execute(text(
        "DELETE FROM diagnosis_results WHERE period_start = :ps AND period_end = :pe"
    ), {"ps": period_start, "pe": period_end})

    import json
    results = []
    for idx, anomaly in enumerate(anomalies):
        attribution = _attribute(db, anomaly, since)

        # P2: LLM 增强根因 + 生成建议
        llm_root_cause = ""
        suggestion_json = ""
        if use_llm:
            try:
                from core.llm_client import DeepSeekClient
                DeepSeekClient.reset_client()
                client = DeepSeekClient()
                sug = await client.generate_diagnosis_suggestion(attribution)
                llm_root_cause = sug.get("root_cause", "") or attribution["root_cause"]
                suggestion_json = json.dumps(sug, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"LLM建议生成失败 {anomaly['module_name']}: {e}")
                llm_root_cause = attribution["root_cause"]

        diagnosis_id = f"DIAG-{period_end.replace('-', '')}-{anomaly['rule_id'][:4]}-{anomaly['module_name'][:2]}-{idx}"
        db.execute(text("""
            INSERT INTO diagnosis_results
                (diagnosis_id, module_name, rule_id, problem, severity, pattern, root_cause, evidence_json, status, period_start, period_end, created_at, llm_root_cause, suggestion_json)
            VALUES (:id, :mod, :rule, :prob, :sev, :pat, :root, :ev, 'active', :ps, :pe, :ca, :lrc, :sj)
        """), {
            "id": diagnosis_id,
            "mod": attribution["module_name"],
            "rule": attribution["rule_id"],
            "prob": attribution["problem"],
            "sev": attribution["severity"],
            "pat": attribution["pattern"],
            "root": attribution["root_cause"],
            "ev": json.dumps(attribution["evidence"], ensure_ascii=False),
            "ps": period_start,
            "pe": period_end,
            "ca": datetime.utcnow().isoformat(),
            "lrc": llm_root_cause,
            "sj": suggestion_json,
        })
        attribution["llm_root_cause"] = llm_root_cause
        attribution["suggestion"] = json.loads(suggestion_json) if suggestion_json else None
        results.append(attribution)

    db.commit()
    logger.info(f"诊断完成: {len(results)} 条异常 (周期 {period_start} ~ {period_end})")
    return results


def get_latest_diagnosis(db: Session, limit: int = 20):
    """获取最新周期的诊断结果（只读，供API展示）。"""
    ensure_diagnosis_table(db)
    rows = db.execute(text("""
        SELECT diagnosis_id, module_name, rule_id, problem, severity, pattern,
               root_cause, llm_root_cause, suggestion_json, evidence_json, period_start, period_end
        FROM diagnosis_results
        WHERE status = 'active'
        ORDER BY created_at DESC, severity DESC
        LIMIT :limit
    """), {"limit": limit}).fetchall()
    import json
    results = []
    for r in rows:
        try:
            evidence = json.loads(r.evidence_json) if r.evidence_json else {}
        except Exception:
            evidence = {}
        try:
            suggestion = json.loads(r.suggestion_json) if r.suggestion_json else None
        except Exception:
            suggestion = None
        results.append({
            "diagnosis_id": r.diagnosis_id,
            "module_name": r.module_name,
            "rule_id": r.rule_id,
            "problem": r.problem,
            "severity": r.severity,
            "pattern": r.pattern,
            "root_cause": r.root_cause,
            "llm_root_cause": r.llm_root_cause or "",
            "suggestion": suggestion,
            "evidence": evidence,
            "period": f"{r.period_start} ~ {r.period_end}",
        })
    return results
