"""
边缘案例检测与处理服务
支持人工审核后再入知识库
"""
import re
import json
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy import func
from database import SessionLocal
from models.models import EdgeCaseLibrary, ScoringResult
import uuid


class EdgeCaseType:
    """边缘案例类型枚举"""
    BLURRY_PHOTO = "blurry_photo"                    # 照片模糊
    MISSING_DESCRIPTION = "missing_description"      # 描述缺失
    MULTIPLE_ISSUES = "multiple_issues"             # 多问题混杂
    CONFLICTING_INFO = "conflicting_info"           # 信息矛盾
    RARE_VIOLATION = "rare_violation"              # 罕见违规
    AMBIGUOUS_SEVERITY = "ambiguous_severity"       # 严重程度模糊
    TIMING_ISSUE = "timing_issue"                  # 时效性问题
    BOUNDARY_SCORE = "boundary_score"              # 边界分数（3.5/4.5等）
    LANGUAGE_BARRIER = "language_barrier"         # 描述语言障碍
    PARTIAL_COMPLIANCE = "partial_compliance"       # 部分合规
    SEASONAL_ISSUE = "seasonal_issue"              # 季节性问题
    UNKNOWN_CATEGORY = "unknown_category"          # 未知类型

    @classmethod
    def all_types(cls) -> List[str]:
        return [
            cls.BLURRY_PHOTO, cls.MISSING_DESCRIPTION, cls.MULTIPLE_ISSUES,
            cls.CONFLICTING_INFO, cls.RARE_VIOLATION, cls.AMBIGUOUS_SEVERITY,
            cls.TIMING_ISSUE, cls.BOUNDARY_SCORE, cls.LANGUAGE_BARRIER,
            cls.PARTIAL_COMPLIANCE, cls.SEASONAL_ISSUE, cls.UNKNOWN_CATEGORY,
        ]

    @classmethod
    def display_name(cls, case_type: str) -> str:
        names = {
            cls.BLURRY_PHOTO: "照片模糊",
            cls.MISSING_DESCRIPTION: "描述缺失",
            cls.MULTIPLE_ISSUES: "多问题混杂",
            cls.CONFLICTING_INFO: "信息矛盾",
            cls.RARE_VIOLATION: "罕见违规类型",
            cls.AMBIGUOUS_SEVERITY: "严重程度模糊",
            cls.TIMING_ISSUE: "时效性问题",
            cls.BOUNDARY_SCORE: "边界分数",
            cls.LANGUAGE_BARRIER: "描述语言障碍",
            cls.PARTIAL_COMPLIANCE: "部分合规",
            cls.SEASONAL_ISSUE: "季节性问题",
            cls.UNKNOWN_CATEGORY: "未知类型",
        }
        return names.get(case_type, case_type)


class EdgeCaseDetector:
    """边缘案例检测器"""

    # 边缘案例检测规则
    DETECTION_RULES = {
        EdgeCaseType.MISSING_DESCRIPTION: lambda x: len(x) < 10 if x else True,
        EdgeCaseType.MULTIPLE_ISSUES: lambda x: "；" in x and len(x.split("；")) > 3,
        EdgeCaseType.PARTIAL_COMPLIANCE: lambda x: "部分" in x or "不完全" in x,
        EdgeCaseType.BOUNDARY_SCORE: lambda x: x in ["3.5", "4.5", "2.5", "3.0", "4.0", "1.5"],
        EdgeCaseType.BLURRY_PHOTO: lambda x: "模糊" in x or "看不清" in x or "不清楚" in x,
        EdgeCaseType.CONFLICTING_INFO: lambda x: bool(re.search(r"[矛盾冲突不一致]", x)),
    }

    def detect_edge_case_type(self, issues_text: str, score: float) -> Optional[str]:
        """
        检测边缘案例类型
        Returns: case_type 或 None
        """
        # 按优先级检测
        for case_type, check_func in self.DETECTION_RULES.items():
            if check_func(issues_text):
                return case_type

        # 边界分数单独检测
        score_str = str(score)
        if score_str in ["3.5", "4.5", "2.5", "1.5"]:
            return EdgeCaseType.BOUNDARY_SCORE

        return None

    def detect_from_item(self, item_data: Dict, score: float) -> Optional[str]:
        """从检查项数据中检测边缘案例类型"""
        issues_text = ""
        if item_data.get("issues"):
            issue_descriptions = []
            for issue in item_data["issues"]:
                desc = issue.get("description", "")
                if desc:
                    issue_descriptions.append(desc)
            issues_text = "；".join(issue_descriptions)

        return self.detect_edge_case_type(issues_text, score)

    def record_auto_capture(
        self,
        case_type: str,
        item_data: Dict,
        score: float,
        ai_handled_correctly: bool,
    ) -> EdgeCaseLibrary:
        """
        记录自动捕获的边缘案例（需人工审核）
        默认状态为 pending_review
        """
        db = SessionLocal()
        try:
            # 检查是否已存在相同类型的活跃案例
            existing = db.query(EdgeCaseLibrary).filter(
                EdgeCaseLibrary.case_type == case_type,
                EdgeCaseLibrary.is_active == True,
                EdgeCaseLibrary.review_status == "approved",
            ).first()

            if existing:
                # 更新已有案例统计
                existing.occurrence_count += 1
                existing.last_occurrence = datetime.utcnow()
                if ai_handled_correctly:
                    existing.hit_count += 1
                else:
                    existing.miss_count += 1
                if existing.occurrence_count > 0:
                    existing.hit_rate = existing.hit_count / existing.occurrence_count * 100
                db.commit()
                return existing
            else:
                # 创建新案例（待审核状态）
                case = EdgeCaseLibrary(
                    case_id=f"EC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
                    case_type=case_type,
                    module_name=item_data.get("module_name"),
                    item_id=item_data.get("item_id"),
                    title=f"自动捕获: {EdgeCaseType.display_name(case_type)}",
                    description=f"由评分系统自动创建，AI处理{'正确' if ai_handled_correctly else '可能不当'}",
                    typical_input=json.dumps(item_data, ensure_ascii=False, indent=2),
                    expected_score_range=self._infer_expected_range(case_type, score),
                    occurrence_count=1,
                    hit_count=1 if ai_handled_correctly else 0,
                    miss_count=0 if ai_handled_correctly else 1,
                    first_occurrence=datetime.utcnow(),
                    last_occurrence=datetime.utcnow(),
                    review_status="pending_review",  # 默认需人工审核
                )
                db.add(case)
                db.commit()
                return case
        finally:
            db.close()

    def _infer_expected_range(self, case_type: str, current_score: float) -> str:
        """根据案例类型推断期望分数范围"""
        ranges = {
            EdgeCaseType.MISSING_DESCRIPTION: "3.0-4.0",
            EdgeCaseType.MULTIPLE_ISSUES: "2.5-3.5",
            EdgeCaseType.PARTIAL_COMPLIANCE: "3.0-4.0",
            EdgeCaseType.BOUNDARY_SCORE: "3.0-4.5",
            EdgeCaseType.BLURRY_PHOTO: "3.0-4.0",
        }
        return ranges.get(case_type, f"{max(1.0, current_score - 1.0)}-{min(5.0, current_score + 1.0)}")

    def get_pending_review_cases(self, limit: int = 50) -> List[EdgeCaseLibrary]:
        """获取待审核的边缘案例"""
        db = SessionLocal()
        try:
            return db.query(EdgeCaseLibrary).filter(
                EdgeCaseLibrary.review_status == "pending_review",
                EdgeCaseLibrary.is_active == True,
            ).order_by(
                EdgeCaseLibrary.occurrence_count.desc()
            ).limit(limit).all()
        finally:
            db.close()

    def approve_case(
        self,
        case_id: str,
        reviewer_id: int,
        resolution_note: Optional[str] = None,
    ) -> bool:
        """审核通过边缘案例"""
        db = SessionLocal()
        try:
            case = db.query(EdgeCaseLibrary).filter(
                EdgeCaseLibrary.case_id == case_id
            ).first()

            if not case:
                return False

            case.review_status = "approved"
            case.reviewed_by = reviewer_id
            case.reviewed_at = datetime.utcnow()
            if resolution_note:
                case.resolution_note = resolution_note
            case.resolution_status = "resolved"

            db.commit()
            return True
        finally:
            db.close()

    def reject_case(self, case_id: str, reviewer_id: int, reason: str) -> bool:
        """驳回边缘案例"""
        db = SessionLocal()
        try:
            case = db.query(EdgeCaseLibrary).filter(
                EdgeCaseLibrary.case_id == case_id
            ).first()

            if not case:
                return False

            case.review_status = "rejected"
            case.reviewed_by = reviewer_id
            case.reviewed_at = datetime.utcnow()
            case.resolution_note = reason
            case.is_active = False  # 驳回后禁用

            db.commit()
            return True
        finally:
            db.close()

    def get_case_stats(self) -> Dict:
        """获取边缘案例统计"""
        db = SessionLocal()
        try:
            # 总体统计
            total = db.query(func.count(EdgeCaseLibrary.id)).filter(
                EdgeCaseLibrary.is_active == True,
            ).scalar() or 0

            pending = db.query(func.count(EdgeCaseLibrary.id)).filter(
                EdgeCaseLibrary.review_status == "pending_review",
                EdgeCaseLibrary.is_active == True,
            ).scalar() or 0

            approved = db.query(func.count(EdgeCaseLibrary.id)).filter(
                EdgeCaseLibrary.review_status == "approved",
                EdgeCaseLibrary.is_active == True,
            ).scalar() or 0

            # 按类型统计
            type_stats = db.query(
                EdgeCaseLibrary.case_type,
                func.count(EdgeCaseLibrary.id).label("count"),
                func.sum(EdgeCaseLibrary.occurrence_count).label("occurrences"),
                func.sum(EdgeCaseLibrary.hit_count).label("hits"),
            ).filter(
                EdgeCaseLibrary.is_active == True,
            ).group_by(EdgeCaseLibrary.case_type).all()

            by_type = []
            for stat in type_stats:
                occurrences = stat.occurrences or 0
                hits = stat.hits or 0
                by_type.append({
                    "type": stat.case_type,
                    "type_display": EdgeCaseType.display_name(stat.case_type),
                    "case_count": stat.count,
                    "total_occurrences": occurrences,
                    "hit_rate": (hits / occurrences * 100) if occurrences > 0 else 0,
                })

            return {
                "total_active_cases": total,
                "pending_review": pending,
                "approved": approved,
                "by_type": by_type,
            }
        finally:
            db.close()

    def get_approved_cases(self, case_type: Optional[str] = None) -> List[EdgeCaseLibrary]:
        """获取已审核通过的边缘案例（用于评分参考）"""
        db = SessionLocal()
        try:
            query = db.query(EdgeCaseLibrary).filter(
                EdgeCaseLibrary.review_status == "approved",
                EdgeCaseLibrary.is_active == True,
            )
            if case_type:
                query = query.filter(EdgeCaseLibrary.case_type == case_type)
            return query.order_by(EdgeCaseLibrary.hit_rate.desc()).all()
        finally:
            db.close()