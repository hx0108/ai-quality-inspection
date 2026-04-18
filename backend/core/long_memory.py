"""
长记忆服务
跨检查周期、项目记住关键信息，持久化存储
"""
from typing import List, Dict, Optional, Any
from datetime import datetime
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from database import SessionLocal
from models.models import ProjectMemory, Project, ScoringResult, Issue
import uuid
import json
import hashlib

# 记忆类型枚举
class MemoryType:
    RECURRING_ISSUE = "recurring_issue"      # 反复出现的问题
    SCORE_PATTERN = "score_pattern"          # 得分模式
    BIAS_NOTE = "bias_note"                  # 偏见备注
    IMPROVEMENT_TREND = "improvement_trend"  # 改进趋势
    # 新增（Hermes 策展记忆）
    SCORING_RULE = "scoring_rule"            # 编译后的评分规则
    CROSS_PROJECT = "cross_project"          # 跨项目通用模式
    INSIGHT = "analysis_insight"             # 分析Agent写入的洞察


class LongMemory:
    """
    长记忆管理器
    用于跨检查周期记住关键信息
    """

    # 记忆置信度阈值：低于此值的记忆不推荐使用
    CONFIDENCE_THRESHOLD = 0.6

    @classmethod
    def add_memory(
        cls,
        project_id: int,
        memory_type: str,
        content: Dict,
        summary: str,
        module_name: str = None,
        item_id: str = None,
        severity: str = None,
        task_id: str = None,
        confidence: float = 0.8,
    ) -> ProjectMemory:
        """
        添加新记忆

        Args:
            project_id: 项目ID
            memory_type: 记忆类型
            content: 记忆内容（字典）
            summary: 摘要（用于展示）
            module_name: 关联模块
            item_id: 关联检查项
            severity: 关联严重程度
            task_id: 来源任务
            confidence: 置信度

        Returns:
            创建的记忆对象
        """
        db = SessionLocal()
        try:
            memory = ProjectMemory(
                memory_id=f"MEM-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
                project_id=project_id,
                task_id=task_id,
                memory_type=memory_type,
                content=json.dumps(content, ensure_ascii=False),
                summary=summary,
                module_name=module_name,
                item_id=item_id,
                severity=severity,
                confidence=confidence,
            )
            db.add(memory)
            db.commit()
            db.refresh(memory)
            return memory
        finally:
            db.close()

    @classmethod
    def get_project_memories(
        cls,
        project_id: int,
        memory_type: str = None,
        module_name: str = None,
        min_confidence: float = None,
        limit: int = 20,
    ) -> List[ProjectMemory]:
        """
        获取项目的记忆

        Args:
            project_id: 项目ID
            memory_type: 记忆类型过滤
            module_name: 模块过滤
            min_confidence: 最低置信度
            limit: 返回数量限制

        Returns:
            记忆列表
        """
        if min_confidence is None:
            min_confidence = cls.CONFIDENCE_THRESHOLD

        db = SessionLocal()
        try:
            query = db.query(ProjectMemory).filter(
                ProjectMemory.project_id == project_id,
                ProjectMemory.is_active == True,
                ProjectMemory.confidence >= min_confidence,
            )

            if memory_type:
                query = query.filter(ProjectMemory.memory_type == memory_type)

            if module_name:
                query = query.filter(ProjectMemory.module_name == module_name)

            memories = query.order_by(
                desc(ProjectMemory.confidence),
                desc(ProjectMemory.occurrence_count),
            ).limit(limit).all()

            # 更新访问统计
            for m in memories:
                m.access_count += 1
                m.last_accessed = datetime.utcnow()
            db.commit()

            return memories
        finally:
            db.close()

    @classmethod
    def update_memory_confidence(
        cls,
        memory_id: str,
        delta: float,
    ) -> bool:
        """
        更新记忆置信度（基于反馈）

        Args:
            memory_id: 记忆ID
            delta: 置信度变化（正负）

        Returns:
            是否成功
        """
        db = SessionLocal()
        try:
            memory = db.query(ProjectMemory).filter(
                ProjectMemory.memory_id == memory_id
            ).first()

            if not memory:
                return False

            memory.confidence = max(0.0, min(1.0, float(memory.confidence) + delta))
            memory.updated_at = datetime.utcnow()
            db.commit()
            return True
        finally:
            db.close()

    @classmethod
    def increment_occurrence(cls, memory_id: str) -> bool:
        """
        增加记忆出现次数

        Args:
            memory_id: 记忆ID

        Returns:
            是否成功
        """
        db = SessionLocal()
        try:
            memory = db.query(ProjectMemory).filter(
                ProjectMemory.memory_id == memory_id
            ).first()

            if not memory:
                return False

            memory.occurrence_count += 1
            memory.last_accessed = datetime.utcnow()
            db.commit()
            return True
        finally:
            db.close()

    @classmethod
    def find_similar_memory(
        cls,
        project_id: int,
        memory_type: str,
        content_hash: str,
    ) -> Optional[ProjectMemory]:
        """
        查找相似记忆（用于去重或合并）

        Args:
            project_id: 项目ID
            memory_type: 记忆类型
            content_hash: 内容哈希

        Returns:
            相似记忆或None
        """
        db = SessionLocal()
        try:
            # 查找同类型、同项目的记忆
            memories = db.query(ProjectMemory).filter(
                ProjectMemory.project_id == project_id,
                ProjectMemory.memory_type == memory_type,
                ProjectMemory.is_active == True,
            ).all()

            for m in memories:
                # 比较内容哈希（简化实现）
                m_content = json.loads(m.content)
                if str(m_content.get("hash", "")) == content_hash:
                    return m

            return None
        finally:
            db.close()

    @classmethod
    def get_cross_project_memories(
        cls,
        module_name: str = None,
        min_confidence: float = 0.7,
        limit: int = 3,
    ) -> List[ProjectMemory]:
        """
        获取跨项目通用记忆（project_id=NULL 的记忆）

        Args:
            module_name: 模块过滤
            min_confidence: 最低置信度
            limit: 返回数量

        Returns:
            跨项目记忆列表
        """
        db = SessionLocal()
        try:
            query = db.query(ProjectMemory).filter(
                ProjectMemory.project_id == None,  # NULL 表示跨项目
                ProjectMemory.is_active == True,
                ProjectMemory.confidence >= min_confidence,
                ProjectMemory.memory_type == MemoryType.CROSS_PROJECT,
            )

            if module_name:
                query = query.filter(ProjectMemory.module_name == module_name)

            memories = query.order_by(
                desc(ProjectMemory.confidence),
                desc(ProjectMemory.occurrence_count),
            ).limit(limit).all()

            for m in memories:
                m.access_count += 1
                m.last_accessed = datetime.utcnow()
            db.commit()

            return memories
        finally:
            db.close()

    @classmethod
    def build_memory_context(
        cls,
        project_id: int,
        module_name: str = None,
        item_id: str = None,
    ) -> str:
        """
        构建记忆上下文字符串（用于LLM Prompt）

        包含三层记忆：
        1. 项目级记忆（原有）
        2. 跨项目通用记忆（新增）
        3. 分析洞察（新增）

        Args:
            project_id: 项目ID
            module_name: 当前模块（用于过滤）
            item_id: 当前检查项（用于过滤）

        Returns:
            格式化的记忆上下文
        """
        memories = cls.get_project_memories(
            project_id=project_id,
            module_name=module_name,
            limit=5,
        )

        # 新增：跨项目通用记忆
        cross_memories = cls.get_cross_project_memories(module_name, limit=3)

        if not memories and not cross_memories:
            return ""

        lines = ["\n\n【历史记忆参考】"]

        # 项目级记忆
        if memories:
            lines.append("\n### 项目专属记忆")

            by_type = {}
            for m in memories:
                if m.memory_type not in by_type:
                    by_type[m.memory_type] = []
                by_type[m.memory_type].append(m)

            # 输出反复出现的问题
            if MemoryType.RECURRING_ISSUE in by_type:
                lines.append("- 反复出现的问题:")
                for m in by_type[MemoryType.RECURRING_ISSUE][:3]:
                    content = json.loads(m.content)
                    lines.append(f"  • {content.get('description', '')[:50]}（出现{m.occurrence_count}次）")

            # 输出得分模式
            if MemoryType.SCORE_PATTERN in by_type:
                lines.append("- 得分模式:")
                for m in by_type[MemoryType.SCORE_PATTERN][:2]:
                    lines.append(f"  • {m.summary}")

            # 输出偏见备注
            if MemoryType.BIAS_NOTE in by_type:
                lines.append("- 评分注意事项:")
                for m in by_type[MemoryType.BIAS_NOTE][:2]:
                    lines.append(f"  • {m.summary}")

            # 输出分析洞察（新增）
            if MemoryType.INSIGHT in by_type:
                lines.append("- 历史分析洞察:")
                for m in by_type[MemoryType.INSIGHT][:2]:
                    lines.append(f"  • {m.summary}")

        # 跨项目通用记忆（新增）
        if cross_memories:
            lines.append("\n### 跨项目通用经验")
            for m in cross_memories:
                lines.append(f"  • [{m.module_name or '通用'}] {m.summary}（{m.occurrence_count}个项目验证）")

        return "\n".join(lines)

    @classmethod
    def extract_and_save_recurring_issues(
        cls,
        project_id: int,
        task_id: str,
    ) -> List[ProjectMemory]:
        """
        从当前任务中提取反复出现的问题并保存

        Args:
            project_id: 项目ID
            task_id: 任务ID

        Returns:
            新增/更新的记忆列表
        """
        db = SessionLocal()
        try:
            # 查找该项目过去的问题记录
            # 通过检查记录关联查询
            from models.models import InspectionRecord, Report

            # 获取该项目的历史报告
            historical_reports = db.query(Report).join(
                InspectionRecord, Report.task_id == InspectionRecord.task_id
            ).filter(
                InspectionRecord.project_id == project_id,
                Report.task_id != task_id,  # 排除当前任务
            ).order_by(desc(Report.generated_at)).limit(10).all()

            if not historical_reports:
                return []

            # 统计问题模式
            # 这里简化实现，实际需要解析报告内容
            # 更好的方式是直接分析历史评分结果

            # 查找历史评分中反复出现的问题描述
            recent_tasks = [r.task_id for r in historical_reports[:5]]

            issues = db.query(
                Issue.description,
                Issue.module_name,
                Issue.severity,
                func.count(Issue.id).label("count"),
            ).join(
                InspectionRecord, Issue.record_id == InspectionRecord.record_id
            ).filter(
                InspectionRecord.project_id == project_id,
                InspectionRecord.task_id.in_(recent_tasks),
                Issue.description.isnot(None),
                Issue.description != "",
            ).group_by(
                Issue.description,
                Issue.module_name,
                Issue.severity,
            ).having(
                func.count(Issue.id) >= 2  # 出现2次以上
            ).order_by(
                desc("count")
            ).limit(5).all()

            saved_memories = []
            for issue in issues:
                desc_text = issue.description[:100] if issue.description else ""

                # 检查是否已存在相似记忆
                content_hash = hashlib.sha256(desc_text.encode("utf-8")).hexdigest()[:32]
                existing = cls.find_similar_memory(
                    project_id,
                    MemoryType.RECURRING_ISSUE,
                    content_hash,
                )

                if existing:
                    # 增加出现次数
                    cls.increment_occurrence(existing.memory_id)
                    existing.last_accessed = datetime.utcnow()
                    db.commit()
                    saved_memories.append(existing)
                else:
                    # 创建新记忆
                    memory = cls.add_memory(
                        project_id=project_id,
                        memory_type=MemoryType.RECURRING_ISSUE,
                        content={
                            "description": desc_text,
                            "modules": [issue.module_name],
                            "hash": content_hash,
                        },
                        summary=f"{desc_text[:30]}...（出现{issue.count}次）",
                        module_name=issue.module_name,
                        severity=issue.severity,
                        task_id=task_id,
                        confidence=min(0.9, 0.5 + issue.count * 0.1),  # 出现越多置信度越高
                    )
                    saved_memories.append(memory)

            return saved_memories
        finally:
            db.close()

    @classmethod
    def get_memory_stats(cls, project_id: int) -> Dict:
        """
        获取项目记忆统计

        Args:
            project_id: 项目ID

        Returns:
            统计信息
        """
        db = SessionLocal()
        try:
            stats = db.query(
                ProjectMemory.memory_type,
                func.count(ProjectMemory.id).label("count"),
                func.sum(ProjectMemory.occurrence_count).label("total_occurrences"),
                func.avg(ProjectMemory.confidence).label("avg_confidence"),
            ).filter(
                ProjectMemory.project_id == project_id,
                ProjectMemory.is_active == True,
            ).group_by(ProjectMemory.memory_type).all()

            return {
                "total_memories": sum(s.count for s in stats),
                "by_type": {
                    s.memory_type: {
                        "count": s.count,
                        "total_occurrences": s.total_occurrences or 0,
                        "avg_confidence": float(s.avg_confidence or 0),
                    }
                    for s in stats
                },
            }
        finally:
            db.close()


def get_memory_context_for_scoring(
    project_id: int,
    module_name: str = None,
) -> str:
    """
    获取评分用的记忆上下文（便捷函数）

    Args:
        project_id: 项目ID
        module_name: 当前模块

    Returns:
        格式化的上下文字符串
    """
    return LongMemory.build_memory_context(project_id, module_name)