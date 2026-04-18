"""
AI评估指标收集服务
计算并记录AI品质的各项评估指标
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import func
from database import SessionLocal
from models.models import (
    ScoringResult, LlmUsageLog, BiasDetection,
    EdgeCaseLibrary, AIMetrics, TaskProgress
)
import uuid


class MetricsCollector:
    """AI指标收集器"""

    def calculate_period_metrics(
        self,
        period_start: str,
        period_end: str,
        golden_dataset_accuracy: Optional[float] = None,
    ) -> Dict:
        """
        计算指定周期的完整指标

        Args:
            period_start: 开始日期 YYYY-MM-DD
            period_end: 结束日期 YYYY-MM-DD
            golden_dataset_accuracy: Golden Dataset测试准确率(可选)

        Returns:
            完整指标字典
        """
        db = SessionLocal()
        try:
            # 1. 准确性指标
            total_scored = db.query(ScoringResult).filter(
                ScoringResult.scored_at >= period_start,
                ScoringResult.scored_at <= period_end,
            ).count()

            total_edited = db.query(ScoringResult).filter(
                ScoringResult.is_edited == True,
                ScoringResult.scored_at >= period_start,
                ScoringResult.scored_at <= period_end,
            ).count()

            consistency_rate = (1 - total_edited / total_scored) * 100 if total_scored > 0 else 100

            # 2. 置信度分布
            high_conf = db.query(func.count(ScoringResult.id)).filter(
                ScoringResult.confidence_score >= 0.8,
                ScoringResult.scored_at >= period_start,
                ScoringResult.scored_at <= period_end,
            ).scalar() or 0

            medium_conf = db.query(func.count(ScoringResult.id)).filter(
                ScoringResult.confidence_score >= 0.5,
                ScoringResult.confidence_score < 0.8,
                ScoringResult.scored_at >= period_start,
                ScoringResult.scored_at <= period_end,
            ).scalar() or 0

            low_conf = db.query(func.count(ScoringResult.id)).filter(
                ScoringResult.confidence_score < 0.5,
                ScoringResult.scored_at >= period_start,
                ScoringResult.scored_at <= period_end,
            ).scalar() or 0

            # 3. 性能指标
            perf_stats = db.query(
                func.avg(LlmUsageLog.duration_ms).label("avg_duration"),
                func.count(LlmUsageLog.id).filter(
                    LlmUsageLog.duration_ms > 45000  # 超时阈值45秒
                ).label("timeout_count"),
            ).filter(
                LlmUsageLog.timestamp >= period_start,
                LlmUsageLog.timestamp <= period_end,
                LlmUsageLog.call_type == "scoring",
            ).first()

            avg_response_time = int(perf_stats.avg_duration or 0) if perf_stats else 0

            # 4. 降级次数
            fallback_count = db.query(func.count(ScoringResult.id)).filter(
                ScoringResult.is_fallback == True,
                ScoringResult.scored_at >= period_start,
                ScoringResult.scored_at <= period_end,
            ).scalar() or 0

            # 5. 偏见指标
            module_bias = db.query(
                func.max(BiasDetection.deviation_rate)
            ).filter(
                BiasDetection.dimension_type == "module",
                BiasDetection.detected_at >= period_start,
            ).scalar() or 0

            inspector_bias = db.query(
                func.max(BiasDetection.deviation_rate)
            ).filter(
                BiasDetection.dimension_type == "inspector",
                BiasDetection.detected_at >= period_start,
            ).scalar() or 0

            active_bias_alerts = db.query(func.count(BiasDetection.id)).filter(
                BiasDetection.is_alert == True,
            ).scalar() or 0

            # 6. 边缘案例统计
            edge_cases = db.query(func.count(EdgeCaseLibrary.id)).filter(
                EdgeCaseLibrary.is_active == True,
            ).scalar() or 0

            edge_occurrences = db.query(
                func.sum(EdgeCaseLibrary.occurrence_count)
            ).filter(
                EdgeCaseLibrary.is_active == True,
            ).scalar() or 0

            edge_hits = db.query(
                func.sum(EdgeCaseLibrary.hit_count)
            ).filter(
                EdgeCaseLibrary.is_active == True,
            ).scalar() or 0

            edge_hit_rate = (edge_hits / edge_occurrences * 100) if edge_occurrences > 0 else 0

            return {
                "period_start": period_start,
                "period_end": period_end,
                # 准确性
                "total_scored": total_scored,
                "total_edited": total_edited,
                "consistency_rate": round(float(consistency_rate), 2),
                "accuracy_rate": golden_dataset_accuracy,
                # 置信度分布
                "high_confidence_count": high_conf,
                "medium_confidence_count": medium_conf,
                "low_confidence_count": low_conf,
                # 性能
                "avg_response_time_ms": avg_response_time,
                "timeout_count": perf_stats.timeout_count if perf_stats else 0,
                "fallback_count": fallback_count,
                # 偏见
                "max_module_deviation": float(module_bias or 0),
                "max_inspector_deviation": float(inspector_bias or 0),
                "active_bias_alerts": active_bias_alerts,
                # 边缘案例
                "edge_cases_detected": edge_cases,
                "edge_cases_hit_rate": round(edge_hit_rate, 2),
            }
        finally:
            db.close()

    def save_metrics_record(
        self,
        period_start: str,
        period_end: str,
        golden_dataset_accuracy: Optional[float] = None,
    ) -> AIMetrics:
        """保存指标记录到数据库"""
        metrics = self.calculate_period_metrics(
            period_start, period_end, golden_dataset_accuracy
        )

        db = SessionLocal()
        try:
            record = AIMetrics(
                record_id=f"MET-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
                period_start=period_start,
                period_end=period_end,
                total_scored=metrics["total_scored"],
                total_edited=metrics["total_edited"],
                consistency_rate=metrics["consistency_rate"],
                accuracy_rate=golden_dataset_accuracy,
                high_confidence_count=metrics["high_confidence_count"],
                medium_confidence_count=metrics["medium_confidence_count"],
                low_confidence_count=metrics["low_confidence_count"],
                avg_response_time_ms=metrics["avg_response_time_ms"],
                timeout_count=metrics["timeout_count"],
                fallback_count=metrics["fallback_count"],
                max_module_deviation=metrics["max_module_deviation"],
                max_inspector_deviation=metrics["max_inspector_deviation"],
                active_bias_alerts=metrics["active_bias_alerts"],
                edge_cases_detected=metrics["edge_cases_detected"],
                edge_cases_hit_rate=metrics["edge_cases_hit_rate"],
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return record
        finally:
            db.close()

    def get_latest_metrics(self) -> Optional[AIMetrics]:
        """获取最新的指标记录"""
        db = SessionLocal()
        try:
            return db.query(AIMetrics).order_by(
                AIMetrics.created_at.desc()
            ).first()
        finally:
            db.close()

    def get_metrics_trend(self, months: int = 3) -> List[Dict]:
        """获取指标趋势"""
        db = SessionLocal()
        try:
            start_date = datetime.now() - timedelta(days=months * 30)

            records = db.query(AIMetrics).filter(
                AIMetrics.created_at >= start_date,
            ).order_by(AIMetrics.created_at.asc()).all()

            return [
                {
                    "date": r.created_at.strftime("%Y-%m-%d"),
                    "consistency_rate": float(r.consistency_rate or 0),
                    "accuracy_rate": float(r.accuracy_rate or 0),
                    "active_bias_alerts": r.active_bias_alerts,
                    "total_scored": r.total_scored,
                    "fallback_count": r.fallback_count,
                }
                for r in records
            ]
        finally:
            db.close()

    def get_realtime_stats(self) -> Dict:
        """
        获取实时统计数据（不保存到数据库）
        用于仪表盘实时展示
        """
        db = SessionLocal()
        try:
            # 今日统计
            today = datetime.now().strftime("%Y-%m-%d")
            today_start = f"{today} 00:00:00"
            today_end = f"{today} 23:59:59"

            today_scored = db.query(func.count(ScoringResult.id)).filter(
                ScoringResult.scored_at >= today_start,
                ScoringResult.scored_at <= today_end,
            ).scalar() or 0

            today_edited = db.query(func.count(ScoringResult.id)).filter(
                ScoringResult.is_edited == True,
                ScoringResult.edited_at >= today_start,
                ScoringResult.edited_at <= today_end,
            ).scalar() or 0

            # 需人工复核数
            needs_review = db.query(func.count(ScoringResult.id)).filter(
                ScoringResult.needs_human_review == True,
                ScoringResult.human_reviewed == False,
            ).scalar() or 0

            # 边缘案例待审核数
            edge_pending = db.query(func.count(EdgeCaseLibrary.id)).filter(
                EdgeCaseLibrary.review_status == "pending_review",
                EdgeCaseLibrary.is_active == True,
            ).scalar() or 0

            # 偏见告警数
            bias_alerts = db.query(func.count(BiasDetection.id)).filter(
                BiasDetection.is_alert == True,
            ).scalar() or 0

            return {
                "today": {
                    "scored": today_scored,
                    "edited": today_edited,
                    "consistency_rate": round((1 - today_edited / today_scored) * 100, 1) if today_scored > 0 else 100,
                },
                "pending": {
                    "human_review": needs_review,
                    "edge_case_review": edge_pending,
                },
                "alerts": {
                    "bias_alerts": bias_alerts,
                },
            }
        finally:
            db.close()


def run_metrics_collection(
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
    golden_dataset_accuracy: Optional[float] = None,
) -> Dict:
    """
    执行指标收集任务（供定时任务调用）
    """
    if period_start is None:
        period_start = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    if period_end is None:
        period_end = datetime.now().strftime("%Y-%m-%d")

    collector = MetricsCollector()
    try:
        record = collector.save_metrics_record(period_start, period_end, golden_dataset_accuracy)
        return {
            "status": "success",
            "record_id": record.record_id,
            "metrics": collector.calculate_period_metrics(period_start, period_end),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}