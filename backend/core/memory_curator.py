"""
记忆策展器（Agent-Curated Memory）
主动管理长记忆的生命周期：清理、发现、跨项目迁移
"""
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict

from sqlalchemy import func, desc, and_
from database import SessionLocal
from models.models import ProjectMemory, ScoringResult, Issue, InspectionRecord, InspectionTask, Project
from core.logger import get_logger

logger = get_logger("memory_curator")

# 策展配置
CURATE_CONFIG = {
    # 清理
    "stale_days": 90,               # 超过90天未访问视为过期
    "low_confidence_threshold": 0.5, # 低置信度阈值
    "single_occurrence_days": 60,    # 单次出现超过60天视为无效
    # 跨项目迁移
    "min_projects_for_promote": 3,   # 至少在3个项目中出现才迁移
    "min_confidence_for_promote": 0.7, # 迁移最低置信度
    # 发现
    "bias_deviation_threshold": 0.3, # 偏差趋势阈值
    "issue_escalation_window": 90,   # 问题恶化回溯窗口（天）
}


class MemoryCurator:
    """
    记忆策展器

    三大职责：
    1. 清理：淘汰过期/低价值记忆
    2. 发现：主动发现新的评分模式
    3. 迁移：将高质量项目记忆提升为跨项目通用记忆
    """

    def curate_all(self, project_id: int = None):
        """
        执行全量策展

        Args:
            project_id: 指定项目，None 表示全部项目
        """
        cleaned = self._cleanup_stale(project_id)
        discovered = self._discover_patterns(project_id)
        promoted = self._promote_cross_project()

        logger.info(
            f"策展完成: 清理={cleaned}条, 发现={discovered}条, 迁移={promoted}条"
        )

        return {
            "cleaned": cleaned,
            "discovered": discovered,
            "promoted": promoted,
        }

    # ==================== 清理 ====================

    def _cleanup_stale(self, project_id: int = None) -> int:
        """
        清理过期/低价值记忆

        规则：
        - 超过90天未被访问 且 confidence < 0.5 → 禁用
        - occurrence_count=1 且创建超过60天 → 禁用
        """
        db = SessionLocal()
        try:
            stale_cutoff = datetime.utcnow() - timedelta(days=CURATE_CONFIG["stale_days"])
            single_cutoff = datetime.utcnow() - timedelta(days=CURATE_CONFIG["single_occurrence_days"])
            low_conf = CURATE_CONFIG["low_confidence_threshold"]

            query = db.query(ProjectMemory).filter(ProjectMemory.is_active == True)

            if project_id:
                query = query.filter(ProjectMemory.project_id == project_id)

            all_memories = query.all()
            disabled = 0

            for m in all_memories:
                should_disable = False

                # 规则1：长期未访问 + 低置信度
                if (m.last_accessed and m.last_accessed < stale_cutoff
                        and float(m.confidence or 0) < low_conf):
                    should_disable = True

                # 规则2：单次出现 + 超过60天
                if (m.occurrence_count <= 1
                        and m.created_at and m.created_at < single_cutoff):
                    should_disable = True

                # 规则3：置信度降至极低（< 0.3）
                if float(m.confidence or 0) < 0.3:
                    should_disable = True

                if should_disable:
                    m.is_active = False
                    m.updated_at = datetime.utcnow()
                    disabled += 1

            db.commit()
            if disabled > 0:
                logger.info(f"清理过期记忆: {disabled} 条")
            return disabled

        except Exception as e:
            db.rollback()
            logger.error(f"清理失败: {e}")
            return 0
        finally:
            db.close()

    # ==================== 发现 ====================

    def _discover_patterns(self, project_id: int = None) -> int:
        """
        主动发现新的记忆模式

        1. 评分偏差趋势：某模块 AI 评分一致性下降 → 写入 bias_note
        2. 问题恶化：某问题从轻微升级为严重 → 写入 improvement_trend
        """
        db = SessionLocal()
        try:
            discovered = 0

            # 发现1：评分偏差趋势
            discovered += self._discover_bias_trends(db, project_id)

            # 发现2：问题严重程度恶化
            discovered += self._discover_issue_escalation(db, project_id)

            return discovered

        finally:
            db.close()

    def _discover_bias_trends(self, db, project_id: int = None) -> int:
        """发现评分偏差趋势"""
        try:
            window = datetime.utcnow() - timedelta(days=30)

            # 按模块统计最近30天的修正偏差
            query = db.query(
                ScoringResult.module_name,
                func.count(ScoringResult.id).label("edit_count"),
                func.avg(
                    func.abs(ScoringResult.original_score - ScoringResult.score)
                ).label("avg_deviation"),
            ).filter(
                ScoringResult.is_edited == True,
                ScoringResult.original_score != None,
                ScoringResult.edited_at >= window,
            )

            if project_id:
                query = query.join(
                    InspectionRecord, ScoringResult.record_id == InspectionRecord.record_id
                ).filter(InspectionRecord.project_id == project_id)

            results = query.group_by(ScoringResult.module_name).having(
                func.count(ScoringResult.id) >= 3
            ).all()

            discovered = 0
            for row in results:
                avg_dev = float(row.avg_deviation or 0)
                if avg_dev < CURATE_CONFIG["bias_deviation_threshold"]:
                    continue

                # 检查是否已存在相同偏差记忆
                existing = db.query(ProjectMemory).filter(
                    ProjectMemory.memory_type == "bias_note",
                    ProjectMemory.module_name == row.module_name,
                    ProjectMemory.is_active == True,
                ).first()

                if existing:
                    # 更新已有记忆
                    content = json.loads(existing.content)
                    content["avg_deviation"] = round(avg_dev, 2)
                    content["edit_count"] = row.edit_count
                    content["updated_at"] = datetime.utcnow().isoformat()
                    existing.content = json.dumps(content, ensure_ascii=False)
                    existing.confidence = min(0.95, float(existing.confidence or 0.7) + 0.05)
                    existing.updated_at = datetime.utcnow()
                else:
                    # 创建新偏差记忆
                    pid = project_id or 0
                    if pid == 0:
                        # 找该模块修正记录最多的项目
                        top_project = db.query(
                            InspectionRecord.project_id,
                            func.count(ScoringResult.id).label("cnt"),
                        ).join(
                            ScoringResult, InspectionRecord.record_id == ScoringResult.record_id
                        ).filter(
                            ScoringResult.module_name == row.module_name,
                            ScoringResult.is_edited == True,
                            InspectionRecord.project_id != None,
                        ).group_by(
                            InspectionRecord.project_id
                        ).order_by(desc("cnt")).first()
                        pid = top_project.project_id if top_project else 0

                    if pid:
                        memory = ProjectMemory(
                            memory_id=f"MEM-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
                            project_id=pid,
                            memory_type="bias_note",
                            content=json.dumps({
                                "module_name": row.module_name,
                                "avg_deviation": round(avg_dev, 2),
                                "edit_count": row.edit_count,
                                "note": f"{row.module_name}模块AI评分偏差达{avg_dev:.1f}分，需注意评分准确性",
                            }, ensure_ascii=False),
                            summary=f"{row.module_name}模块AI偏差{avg_dev:.1f}分",
                            module_name=row.module_name,
                            confidence=0.7,
                        )
                        db.add(memory)
                        discovered += 1

            db.commit()
            return discovered

        except Exception as e:
            db.rollback()
            logger.error(f"发现偏差趋势失败: {e}")
            return 0

    def _discover_issue_escalation(self, db, project_id: int = None) -> int:
        """发现问题严重程度恶化趋势"""
        try:
            window = datetime.utcnow() - timedelta(days=CURATE_CONFIG["issue_escalation_window"])

            # 查找同一项目同一模块中，同一问题描述从轻微升级为严重的案例
            query = db.query(
                Issue.description,
                Issue.module_name,
                InspectionRecord.project_id,
                func.min(
                    func.case(
                        [(Issue.severity == "轻微", 1),
                         (Issue.severity == "一般", 2),
                         (Issue.severity == "严重", 3)],
                        else_=0
                    )
                ).label("min_severity"),
                func.max(
                    func.case(
                        [(Issue.severity == "轻微", 1),
                         (Issue.severity == "一般", 2),
                         (Issue.severity == "严重", 3)],
                        else_=0
                    )
                ).label("max_severity"),
                func.count(Issue.id).label("count"),
            ).join(
                InspectionRecord, Issue.record_id == InspectionRecord.record_id
            ).filter(
                Issue.description != None,
                Issue.description != "",
                Issue.created_at >= window,
            )

            if project_id:
                query = query.filter(InspectionRecord.project_id == project_id)

            results = query.group_by(
                Issue.description,
                Issue.module_name,
                InspectionRecord.project_id,
            ).having(
                func.max(
                    func.case(
                        [(Issue.severity == "轻微", 1),
                         (Issue.severity == "一般", 2),
                         (Issue.severity == "严重", 3)],
                        else_=0
                    )
                ) >
                func.min(
                    func.case(
                        [(Issue.severity == "轻微", 1),
                         (Issue.severity == "一般", 2),
                         (Issue.severity == "严重", 3)],
                        else_=0
                    )
                )
            ).limit(10).all()

            discovered = 0
            for row in results:
                desc_text = (row.description or "")[:100]
                severity_map = {1: "轻微", 2: "一般", 3: "严重"}

                memory = ProjectMemory(
                    memory_id=f"MEM-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
                    project_id=row.project_id,
                    memory_type="improvement_trend",
                    content=json.dumps({
                        "description": desc_text,
                        "from_severity": severity_map.get(row.min_severity, "轻微"),
                        "to_severity": severity_map.get(row.max_severity, "严重"),
                        "trend": "恶化",
                        "count": row.count,
                    }, ensure_ascii=False),
                    summary=f"{row.module_name}: {desc_text[:30]}... 问题恶化趋势",
                    module_name=row.module_name,
                    confidence=0.75,
                )
                db.add(memory)
                discovered += 1

            db.commit()
            return discovered

        except Exception as e:
            db.rollback()
            logger.error(f"发现问题恶化失败: {e}")
            return 0

    # ==================== 跨项目迁移 ====================

    def _promote_cross_project(self) -> int:
        """将高质量项目记忆提升为跨项目通用记忆"""
        db = SessionLocal()
        try:
            # 查找在多个项目中独立出现的记忆（按 summary 去重）
            min_projects = CURATE_CONFIG["min_projects_for_promote"]
            min_conf = CURATE_CONFIG["min_confidence_for_promote"]

            # 按 summary 分组，找出现 >= N 次的
            candidates = db.query(
                ProjectMemory.summary,
                func.count(func.distinct(ProjectMemory.project_id)).label("project_count"),
                func.avg(ProjectMemory.confidence).label("avg_confidence"),
                func.sum(ProjectMemory.occurrence_count).label("total_occurrences"),
            ).filter(
                ProjectMemory.is_active == True,
                ProjectMemory.summary != None,
                ProjectMemory.summary != "",
                # 排除已经是跨项目的
                ProjectMemory.project_id != None,
            ).group_by(
                ProjectMemory.summary,
            ).having(
                func.count(func.distinct(ProjectMemory.project_id)) >= min_projects,
                func.avg(ProjectMemory.confidence) >= min_conf,
            ).limit(20).all()

            promoted = 0
            for row in candidates:
                # 检查是否已存在跨项目记忆
                existing = db.query(ProjectMemory).filter(
                    ProjectMemory.project_id == None,  # 跨项目记忆 project_id=NULL
                    ProjectMemory.summary == row.summary,
                    ProjectMemory.memory_type == "cross_project",
                    ProjectMemory.is_active == True,
                ).first()

                if existing:
                    # 更新已有跨项目记忆
                    existing.occurrence_count += int(row.total_occurrences or 0)
                    existing.confidence = min(0.95, float(row.avg_confidence or 0.7) + 0.05)
                    existing.updated_at = datetime.utcnow()
                    continue

                # 获取原始记忆的详细信息
                source = db.query(ProjectMemory).filter(
                    ProjectMemory.summary == row.summary,
                    ProjectMemory.is_active == True,
                ).first()

                if not source:
                    continue

                # 创建跨项目记忆
                memory = ProjectMemory(
                    memory_id=f"MEM-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
                    project_id=None,  # NULL 表示跨项目通用
                    memory_type="cross_project",
                    content=source.content,
                    summary=source.summary,
                    module_name=source.module_name,
                    confidence=float(row.avg_confidence or 0.7),
                    occurrence_count=int(row.total_occurrences or 1),
                )
                db.add(memory)
                promoted += 1

            db.commit()
            if promoted > 0:
                logger.info(f"跨项目记忆迁移: {promoted} 条")
            return promoted

        except Exception as e:
            db.rollback()
            logger.error(f"跨项目迁移失败: {e}")
            return 0
        finally:
            db.close()


# 模块级便捷函数
_curator = MemoryCurator()


def run_curation(project_id: int = None) -> Dict:
    """便捷函数：执行记忆策展"""
    return _curator.curate_all(project_id)
