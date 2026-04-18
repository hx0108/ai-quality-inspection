"""
自我改进引擎（Self-Improvement Loop）
基于偏差检测自动生成评分修正指令，注入到评分Prompt中
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from sqlalchemy import func, desc, and_
from database import SessionLocal
from models.models import (
    ScoringResult, ScoringDirective, BiasDetection,
    InspectionRecord, InspectionTask,
)
from core.logger import get_logger

logger = get_logger("self_improver")

# 改进配置
IMPROVEMENT_CONFIG = {
    "min_samples": 10,                # 最少修正样本才触发
    "deviation_threshold": 0.3,       # 平均偏差超过0.3分才触发
    "max_directive_per_module": 3,    # 每模块最多3条修正指令
    "validation_interval_days": 14,   # 14天后验证效果
    "auto_disable_on_worsen": True,   # 偏差加剧时自动禁用
    "lookback_days": 30,              # 分析回溯天数
}


class SelfImprover:
    """
    自我改进引擎

    闭环流程：
    检测偏差 → 生成修正指令 → 注入评分Prompt → 验证效果 → 调整/禁用
    """

    def run_improvement_cycle(self):
        """执行一轮完整的自我改进循环"""
        # 1. 从活跃告警生成新指令
        new_count = self._generate_from_alerts()

        # 2. 验证已有指令的效果
        validated = self._validate_existing_directives()

        logger.info(
            f"自我改进循环完成: 新增指令={new_count}, 验证={validated}"
        )

        return {"new_directives": new_count, "validated": validated}

    def _generate_from_alerts(self) -> int:
        """从偏差告警生成修正指令"""
        db = SessionLocal()
        try:
            # 查找活跃的模块级告警
            alerts = db.query(BiasDetection).filter(
                BiasDetection.dimension_type == "module",
                BiasDetection.is_alert == True,
            ).order_by(desc(BiasDetection.detected_at)).all()

            if not alerts:
                return 0

            created = 0
            for alert in alerts:
                module_name = alert.dimension_value

                # 检查该模块是否已有活跃指令
                existing_count = db.query(ScoringDirective).filter(
                    ScoringDirective.module_name == module_name,
                    ScoringDirective.is_active == True,
                ).count()

                if existing_count >= IMPROVEMENT_CONFIG["max_directive_per_module"]:
                    continue

                # 分析该模块的详细修正数据
                directive = self._analyze_module_bias(db, module_name, alert)
                if directive:
                    db.add(directive)
                    created += 1

            db.commit()
            return created

        except Exception as e:
            db.rollback()
            logger.error(f"生成修正指令失败: {e}")
            return 0
        finally:
            db.close()

    def _analyze_module_bias(self, db, module_name: str, alert: BiasDetection) -> Optional[ScoringDirective]:
        """分析模块偏差并生成修正指令"""
        window = datetime.utcnow() - timedelta(days=IMPROVEMENT_CONFIG["lookback_days"])

        # 查询该模块最近的人工修正详情
        edits = db.query(
            ScoringResult.item_id,
            ScoringResult.item_name,
            ScoringResult.original_score,
            ScoringResult.score,
            ScoringResult.edit_reason,
            func.count(ScoringResult.id).label("cnt"),
        ).filter(
            ScoringResult.module_name == module_name,
            ScoringResult.is_edited == True,
            ScoringResult.original_score != None,
            ScoringResult.edited_at >= window,
        ).group_by(
            ScoringResult.item_id,
            ScoringResult.item_name,
            ScoringResult.original_score,
            ScoringResult.score,
            ScoringResult.edit_reason,
        ).order_by(desc("cnt")).limit(20).all()

        if len(edits) < IMPROVEMENT_CONFIG["min_samples"]:
            return None

        # 统计偏差
        total_delta = sum(float(e.original_score) - float(e.score) for e in edits)
        avg_delta = total_delta / len(edits)

        if abs(avg_delta) < IMPROVEMENT_CONFIG["deviation_threshold"]:
            return None

        # 分析偏差方向
        direction = "lower" if avg_delta > 0 else "higher"  # AI偏高需下调 / AI偏低需上调
        direction_text = "偏高" if avg_delta > 0 else "偏低"

        # 找出偏差最大的子类（按 edit_reason 分组）
        reason_groups = {}
        for e in edits:
            reason = e.edit_reason or "未分类"
            if reason not in reason_groups:
                reason_groups[reason] = {"count": 0, "delta_sum": 0}
            reason_groups[reason]["count"] += e.cnt
            reason_groups[reason]["delta_sum"] += float(e.original_score) - float(e.score)

        # 找主要偏差原因
        top_reason = max(reason_groups.items(), key=lambda x: abs(x[1]["delta_sum"]))
        trigger_condition = f"{module_name} AND ({top_reason[0]})"

        # 构建修正指令文本
        magnitude = round(abs(avg_delta), 1)
        directive_text = (
            f"【系统自检修正】{module_name}模块AI评分近期系统性{direction_text}约{magnitude}分"
            f"（基于{len(edits)}条人工修正分析）。"
        )

        # 针对具体子类的建议
        if direction == "lower":
            directive_text += f"请对该模块涉及「{top_reason[0]}」的检查项更严格评分，建议多扣{magnitude * 0.5:.1f}分。"
        else:
            directive_text += f"请对该模块涉及「{top_reason[0]}」的检查项适当放宽，建议少扣{magnitude * 0.5:.1f}分。"

        # 检查是否已存在相似指令
        existing = db.query(ScoringDirective).filter(
            ScoringDirective.module_name == module_name,
            ScoringDirective.direction == direction,
            ScoringDirective.is_active == True,
        ).first()

        if existing:
            # 更新已有指令
            existing.directive_text = directive_text
            existing.magnitude = magnitude
            existing.pre_deviation = alert.deviation_rate
            existing.sample_count = len(edits)
            existing.source_alert_id = alert.detection_id
            existing.updated_at = datetime.utcnow()
            return None  # 已更新，不新建

        # 创建新指令
        today = datetime.now().strftime("%Y%m%d")
        return ScoringDirective(
            directive_id=f"DIR-{today}-{uuid.uuid4().hex[:6].upper()}",
            module_name=module_name,
            trigger_condition=trigger_condition,
            directive_text=directive_text,
            direction=direction,
            magnitude=magnitude,
            pre_deviation=alert.deviation_rate,
            source_alert_id=alert.detection_id,
            sample_count=len(edits),
            confidence=0.5,
        )

    def _validate_existing_directives(self) -> int:
        """验证已有修正指令的效果"""
        db = SessionLocal()
        try:
            interval = IMPROVEMENT_CONFIG["validation_interval_days"]
            cutoff = datetime.utcnow() - timedelta(days=interval)

            # 查找已生效超过14天、尚未验证的指令
            directives = db.query(ScoringDirective).filter(
                ScoringDirective.is_active == True,
                ScoringDirective.validation_status == "pending",
                ScoringDirective.created_at <= cutoff,
            ).all()

            validated = 0
            for d in directives:
                # 对比启用前后的偏差
                # 启用后：最近14天的修正偏差
                recent_window = datetime.utcnow() - timedelta(days=interval)
                recent_edits = db.query(
                    func.avg(
                        func.abs(ScoringResult.original_score - ScoringResult.score)
                    ).label("avg_deviation"),
                    func.count(ScoringResult.id).label("cnt"),
                ).filter(
                    ScoringResult.module_name == d.module_name,
                    ScoringResult.is_edited == True,
                    ScoringResult.original_score != None,
                    ScoringResult.edited_at >= recent_window,
                ).first()

                if not recent_edits or recent_edits.cnt < 5:
                    continue  # 样本不足，跳过

                post_deviation = float(recent_edits.avg_deviation or 0)
                pre_deviation = float(d.pre_deviation or 0)

                d.post_deviation = post_deviation
                d.validated_at = datetime.utcnow()

                # 计算改善百分比
                if pre_deviation > 0:
                    improvement = ((pre_deviation - post_deviation) / pre_deviation) * 100
                    d.improvement_pct = round(improvement, 2)

                    if improvement > 20:
                        d.validation_status = "improved"
                        d.confidence = min(0.95, float(d.confidence or 0.5) + 0.2)
                        logger.info(f"指令有效: {d.module_name}, 改善{improvement:.1f}%")
                    elif improvement > 0:
                        d.validation_status = "unchanged"
                        d.confidence = min(0.9, float(d.confidence or 0.5) + 0.1)
                    else:
                        d.validation_status = "worsened"
                        if IMPROVEMENT_CONFIG["auto_disable_on_worsen"]:
                            d.is_active = False
                            logger.warning(f"指令恶化已禁用: {d.module_name}")
                else:
                    d.validation_status = "unchanged"

                d.updated_at = datetime.utcnow()
                validated += 1

            db.commit()
            return validated

        except Exception as e:
            db.rollback()
            logger.error(f"验证指令失败: {e}")
            return 0
        finally:
            db.close()

    def get_directives_for_prompt(self, module_name: str) -> str:
        """
        获取注入评分Prompt的修正指令

        Args:
            module_name: 当前评分模块

        Returns:
            修正指令文本，无活跃指令时返回空字符串
        """
        db = SessionLocal()
        try:
            directives = db.query(ScoringDirective).filter(
                ScoringDirective.module_name == module_name,
                ScoringDirective.is_active == True,
            ).order_by(
                desc(ScoringDirective.confidence),
                desc(ScoringDirective.sample_count),
            ).limit(IMPROVEMENT_CONFIG["max_directive_per_module"]).all()

            if not directives:
                return ""

            lines = []
            for d in directives:
                lines.append(d.directive_text)

            return "\n".join(lines)

        finally:
            db.close()

    def get_all_active_directives(self) -> List[Dict]:
        """获取所有活跃修正指令（管理界面用）"""
        db = SessionLocal()
        try:
            directives = db.query(ScoringDirective).filter(
                ScoringDirective.is_active == True,
            ).order_by(desc(ScoringDirective.created_at)).all()

            return [
                {
                    "directive_id": d.directive_id,
                    "module_name": d.module_name,
                    "directive_text": d.directive_text,
                    "direction": d.direction,
                    "magnitude": float(d.magnitude or 0),
                    "sample_count": d.sample_count,
                    "validation_status": d.validation_status,
                    "confidence": float(d.confidence or 0.5),
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                    "validated_at": d.validated_at.isoformat() if d.validated_at else None,
                    "improvement_pct": float(d.improvement_pct or 0),
                }
                for d in directives
            ]
        finally:
            db.close()


# 模块级便捷函数
_improver = SelfImprover()


def get_scoring_directives_text(module_name: str) -> str:
    """便捷函数：获取修正指令文本"""
    return _improver.get_directives_for_prompt(module_name)


def run_improvement() -> Dict:
    """便捷函数：执行自我改进循环"""
    return _improver.run_improvement_cycle()
