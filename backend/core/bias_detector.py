"""
偏见检测服务
检测AI评分与人工评分之间的偏差
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import func
from database import SessionLocal
from models.models import ScoringResult, BiasDetection, User
import uuid

# 告警阈值配置
MODULE_DEVIATION_THRESHOLD = 15.0   # 模块级偏差 >15% 告警
INSPECTOR_DEVIATION_THRESHOLD = 20.0  # 检查员偏差 >20% 告警
MIN_SAMPLES_FOR_DETECTION = 10     # 最少样本数才进行检测


class BiasDetector:
    """偏见检测器"""

    DEVIATION_THRESHOLDS = {
        "module": MODULE_DEVIATION_THRESHOLD,
        "inspector": INSPECTOR_DEVIATION_THRESHOLD,
    }

    def detect_all_biases(self, period_days: int = 30) -> List[BiasDetection]:
        """执行全量偏见检测"""
        results = []
        results.extend(self.detect_module_biases(period_days))
        results.extend(self.detect_inspector_biases(period_days))
        return results

    def detect_module_biases(self, period_days: int = 30) -> List[BiasDetection]:
        """检测模块级偏见"""
        db = SessionLocal()
        try:
            # 计算日期范围
            start_date = datetime.utcnow() - timedelta(days=period_days)

            # 查询过去N天有人工修正的评分记录，按模块聚合
            edited_records = db.query(
                ScoringResult.module_name,
                func.count(ScoringResult.id).label("total"),
                func.avg(ScoringResult.original_score).label("ai_mean"),
                func.avg(ScoringResult.score).label("human_mean"),
            ).filter(
                ScoringResult.is_edited == True,
                ScoringResult.original_score != None,
                ScoringResult.edited_at >= start_date,
            ).group_by(
                ScoringResult.module_name
            ).having(
                func.count(ScoringResult.id) >= MIN_SAMPLES_FOR_DETECTION
            ).all()

            detections = []
            for row in edited_records:
                ai_mean = float(row.ai_mean)
                human_mean = float(row.human_mean)
                deviation = abs(ai_mean - human_mean) / human_mean * 100 if human_mean > 0 else 0
                is_alert = deviation > self.DEVIATION_THRESHOLDS["module"]

                detection = BiasDetection(
                    detection_id=f"BIA-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
                    dimension_type="module",
                    dimension_value=row.module_name,
                    total_samples=row.total,
                    ai_mean_score=ai_mean,
                    human_mean_score=human_mean,
                    deviation_rate=deviation,
                    is_alert=is_alert,
                    alert_level="critical" if deviation > 25 else "warning" if is_alert else None,
                    alert_threshold=self.DEVIATION_THRESHOLDS["module"],
                    analysis_period_start=start_date.strftime("%Y-%m-%d"),
                    analysis_period_end=datetime.now().strftime("%Y-%m-%d"),
                )
                detections.append(detection)
                db.add(detection)

            db.commit()
            return detections
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    def detect_inspector_biases(self, period_days: int = 30) -> List[BiasDetection]:
        """检测检查员级偏见"""
        db = SessionLocal()
        try:
            # 计算日期范围
            start_date = datetime.utcnow() - timedelta(days=period_days)

            # 按检查员聚合人工修正数据
            edited_records = db.query(
                ScoringResult.edited_by,
                func.count(ScoringResult.id).label("total"),
                func.avg(ScoringResult.original_score).label("ai_mean"),
                func.avg(ScoringResult.score).label("human_mean"),
            ).filter(
                ScoringResult.is_edited == True,
                ScoringResult.original_score != None,
                ScoringResult.edited_by != None,
                ScoringResult.edited_at >= start_date,
            ).group_by(
                ScoringResult.edited_by
            ).having(
                func.count(ScoringResult.id) >= MIN_SAMPLES_FOR_DETECTION
            ).all()

            # 获取用户名称映射
            user_ids = [r.edited_by for r in edited_records]
            users = db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
            user_names = {u.id: u.real_name for u in users}

            detections = []
            for row in edited_records:
                ai_mean = float(row.ai_mean)
                human_mean = float(row.human_mean)
                deviation = abs(ai_mean - human_mean) / human_mean * 100 if human_mean > 0 else 0
                is_alert = deviation > self.DEVIATION_THRESHOLDS["inspector"]

                dimension_value = user_names.get(row.edited_by, f"user_{row.edited_by}")

                detection = BiasDetection(
                    detection_id=f"BIA-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
                    dimension_type="inspector",
                    dimension_value=dimension_value,
                    total_samples=row.total,
                    ai_mean_score=ai_mean,
                    human_mean_score=human_mean,
                    deviation_rate=deviation,
                    is_alert=is_alert,
                    alert_level="critical" if deviation > 30 else "warning" if is_alert else None,
                    alert_threshold=self.DEVIATION_THRESHOLDS["inspector"],
                    analysis_period_start=start_date.strftime("%Y-%m-%d"),
                    analysis_period_end=datetime.now().strftime("%Y-%m-%d"),
                )
                detections.append(detection)
                db.add(detection)

            db.commit()
            return detections
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    def get_active_alerts(self) -> List[BiasDetection]:
        """获取当前活跃的告警"""
        db = SessionLocal()
        try:
            return db.query(BiasDetection).filter(
                BiasDetection.is_alert == True
            ).order_by(
                BiasDetection.detected_at.desc()
            ).limit(20).all()
        finally:
            db.close()

    def get_bias_summary(self, period_days: int = 30) -> Dict:
        """获取偏见检测摘要"""
        db = SessionLocal()
        try:
            start_date = datetime.utcnow() - timedelta(days=period_days)

            # 模块级统计
            module_detections = db.query(
                func.count(BiasDetection.id).label("total"),
                func.max(BiasDetection.deviation_rate).label("max_deviation"),
            ).filter(
                BiasDetection.dimension_type == "module",
                BiasDetection.detected_at >= start_date,
            ).first()

            # 检查员级统计
            inspector_detections = db.query(
                func.count(BiasDetection.id).label("total"),
                func.max(BiasDetection.deviation_rate).label("max_deviation"),
            ).filter(
                BiasDetection.dimension_type == "inspector",
                BiasDetection.detected_at >= start_date,
            ).first()

            # 活跃告警数
            active_alerts = db.query(func.count(BiasDetection.id)).filter(
                BiasDetection.is_alert == True,
                BiasDetection.detected_at >= start_date,
            ).scalar()

            return {
                "period_days": period_days,
                "module_bias": {
                    "detection_count": module_detections.total or 0,
                    "max_deviation": float(module_detections.max_deviation or 0),
                },
                "inspector_bias": {
                    "detection_count": inspector_detections.total or 0,
                    "max_deviation": float(inspector_detections.max_deviation or 0),
                },
                "active_alerts": active_alerts or 0,
            }
        finally:
            db.close()

    def get_bias_trend(self, dimension_type: str, dimension_value: str, months: int = 6) -> List[Dict]:
        """获取偏见趋势数据"""
        db = SessionLocal()
        try:
            start_date = datetime.utcnow() - timedelta(days=months * 30)

            detections = db.query(BiasDetection).filter(
                BiasDetection.dimension_type == dimension_type,
                BiasDetection.dimension_value == dimension_value,
                BiasDetection.detected_at >= start_date,
            ).order_by(BiasDetection.detected_at.asc()).all()

            return [
                {
                    "date": d.detected_at.strftime("%Y-%m-%d"),
                    "deviation_rate": float(d.deviation_rate or 0),
                    "is_alert": d.is_alert,
                }
                for d in detections
            ]
        finally:
            db.close()


def run_async_detection(period_days: int = 30):
    """异步触发偏见检测（供后台任务调用）"""
    detector = BiasDetector()
    try:
        results = detector.detect_all_biases(period_days)
        return {
            "status": "completed",
            "detections": len(results),
            "alerts": sum(1 for r in results if r.is_alert),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}