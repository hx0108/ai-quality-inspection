"""
数据库模型定义
参考 TECH_DESIGN.md 第5节
"""
from datetime import datetime
import uuid
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Enum, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base
import enum


class UserRole(str, enum.Enum):
    """用户角色"""
    ADMIN = "admin"
    INSPECTOR = "inspector"
    SITE_SUPERVISOR = "site_supervisor"
    FIELD_SUPERVISOR = "field_supervisor"
    PROJECT_STAFF = "project_staff"


class TaskStatus(str, enum.Enum):
    """任务状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class RecordStatus(str, enum.Enum):
    """检查记录状态"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class ItemStatus(str, enum.Enum):
    """检查项状态"""
    PENDING = "pending"
    CHECKED = "checked"
    SKIPPED = "skipped"


class Severity(str, enum.Enum):
    """问题严重程度"""
    SERIOUS = "严重"
    GENERAL = "一般"
    MINOR = "轻微"


# ==================== 用户表 ====================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    real_name = Column(String(50), nullable=False)
    role = Column(String(20), nullable=False, default="inspector")
    is_active = Column(Boolean, default=True)
    must_change_pwd = Column(Boolean, default=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)  # 驻场经理/项目人员所属项目
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    assignments = relationship("TaskAssignment", back_populates="inspector")
    project = relationship("Project", back_populates="users")
    user_projects = relationship("UserProject", back_populates="user", cascade="all, delete-orphan")


# ==================== 项目表 ====================
class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(20), unique=True, nullable=True)
    address = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    tasks = relationship("InspectionTask", back_populates="project")
    users = relationship("User", back_populates="project")
    project_users = relationship("UserProject", back_populates="project", cascade="all, delete-orphan")


# ==================== 用户-项目多对多关联表 ====================
class UserProject(Base):
    __tablename__ = "user_projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    user = relationship("User", back_populates="user_projects")
    project = relationship("Project", back_populates="project_users")


# ==================== 检查任务表（父任务） ====================
class InspectionTask(Base):
    __tablename__ = "inspection_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(50), unique=True, nullable=False, index=True)  # Q-YYYYMMDD-XXXXXXXX
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    check_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    status = Column(String(20), nullable=False, default="pending")
    standard_type = Column(String(20), nullable=False, default="diecheng")  # diecheng / feidiecheng
    total_score = Column(Numeric(5, 2), nullable=True)  # 项目总分 0-100
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    project = relationship("Project", back_populates="tasks")
    assignments = relationship("TaskAssignment", back_populates="task", cascade="all, delete-orphan")
    records = relationship("InspectionRecord", back_populates="task", cascade="all, delete-orphan")
    report = relationship("Report", back_populates="task", uselist=False)


# ==================== 任务模块分配表 ====================
class TaskAssignment(Base):
    __tablename__ = "task_assignments"
    __table_args__ = (
        # 每个任务每个模块只能分配一人
        UniqueConstraint('task_id', 'module_name', name='uq_task_module'),
    )

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(50), ForeignKey("inspection_tasks.task_id"), nullable=False)
    module_name = Column(String(50), nullable=False)
    inspector_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    task = relationship("InspectionTask", back_populates="assignments")
    inspector = relationship("User", back_populates="assignments")


# ==================== 检查记录表（模块级别） ====================
class InspectionRecord(Base):
    __tablename__ = "inspection_records"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(String(50), unique=True, nullable=False, index=True)  # REC-YYYYMMDD-XXX
    task_id = Column(String(50), ForeignKey("inspection_tasks.task_id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    module_name = Column(String(50), nullable=False)
    inspector_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    check_date = Column(String(10), nullable=False)
    status = Column(String(20), nullable=False, default="not_started")
    data_json = Column(Text, nullable=True)  # 完整检查数据 JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    task = relationship("InspectionTask", back_populates="records")
    inspector = relationship("User", foreign_keys=[inspector_id])
    issues = relationship("Issue", back_populates="record", cascade="all, delete-orphan")
    scoring_results = relationship("ScoringResult", back_populates="record", cascade="all, delete-orphan")


# ==================== 问题表 ====================
class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(String(50), unique=True, nullable=False, index=True)  # ISS-YYYYMMDD-XXX
    record_id = Column(String(50), ForeignKey("inspection_records.record_id"), nullable=False, index=True)
    module_name = Column(String(50), nullable=False)
    item_id = Column(String(20), nullable=False)  # 检查项编号
    item_name = Column(String(200), nullable=True)  # 检查项名称
    description = Column(Text, nullable=True)  # 问题描述
    location = Column(String(255), nullable=True)  # 问题位置
    severity = Column(String(20), nullable=False, default="一般")  # 严重/一般/轻微
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    record = relationship("InspectionRecord", back_populates="issues")
    photos = relationship("Photo", back_populates="issue", cascade="all, delete-orphan")


# ==================== 照片表 ====================
class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(String(50), unique=True, nullable=False, index=True)  # PHO-YYYYMMDD-XXX
    issue_id = Column(String(50), ForeignKey("issues.issue_id"), nullable=True, index=True)
    file_path = Column(String(255), nullable=False)
    file_name = Column(String(100), nullable=False)
    photo_type = Column(String(20), nullable=True)  # 问题照片
    upload_time = Column(DateTime, default=datetime.utcnow)

    # 水印相机元数据（确保拍摄位置真实性）
    latitude = Column(Float, nullable=True)              # GPS 纬度
    longitude = Column(Float, nullable=True)             # GPS 经度
    address = Column(String(500), nullable=True)         # GPS 逆地理编码地址
    capture_time = Column(DateTime, nullable=True)       # 实际拍摄时间
    inspector_name = Column(String(50), nullable=True)   # 拍摄人姓名
    watermark_hash = Column(String(128), nullable=True)  # 防篡改签名

    # 关系
    issue = relationship("Issue", back_populates="photos")


# ==================== 评分结果表 ====================
class ScoringResult(Base):
    __tablename__ = "scoring_results"

    id = Column(Integer, primary_key=True, index=True)
    scoring_id = Column(String(50), unique=True, nullable=False, index=True)  # SCR-YYYYMMDD-XXX
    record_id = Column(String(50), ForeignKey("inspection_records.record_id"), nullable=False)
    module_name = Column(String(50), nullable=False)
    item_id = Column(String(20), nullable=False)
    item_name = Column(String(200), nullable=True)
    score = Column(Numeric(3, 1), nullable=False)  # 评价得分 0-5，skipped 项默认 5
    weight = Column(Numeric(6, 4), nullable=False)  # 权重系数
    weighted_score = Column(Numeric(6, 4), nullable=False)  # 单项加权得分 = score * weight
    module_pct_score = Column(Numeric(5, 2), nullable=True)  # 模块百分制得分（模块汇总后填入）
    scoring_basis = Column(Text, nullable=True)  # 评分依据
    improvement_suggestion = Column(Text, nullable=True)  # 改进建议
    check_standard = Column(Text, nullable=True)  # 检查标准
    check_method = Column(Text, nullable=True)  # 检查方法
    scoring_rule = Column(Text, nullable=True)  # 评分规则
    is_skipped = Column(Boolean, default=False)  # 是否为跳过项
    is_fallback = Column(Boolean, default=False)  # 是否为降级默认分数（AI评分失败时）
    is_edited = Column(Boolean, default=False)  # 是否被人工修改
    edit_reason = Column(String(200), nullable=True)  # 人工修改原因分类
    original_score = Column(Numeric(3, 1), nullable=True)  # AI原始分数（首次编辑前保存）
    edited_by = Column(Integer, nullable=True)  # 修改人ID
    edited_at = Column(DateTime, nullable=True)  # 修改时间
    scored_at = Column(DateTime, default=datetime.utcnow)

    # 置信度与人工复核（Phase 2新增）
    confidence_score = Column(Numeric(3, 2), nullable=True)  # 置信度 0-1，默认0.8
    needs_human_review = Column(Boolean, default=False)       # 是否需要人工复核（置信度<0.8）
    jev_confidence = Column(Numeric(4, 3), nullable=True)    # Jev 判断模型：给分正确概率 0-1
    jev_direction = Column(String(10), nullable=True)        # Jev 独立判断：偏低/正确/偏高
    human_reviewed = Column(Boolean, default=False)          # 是否已人工复核
    human_reviewed_by = Column(Integer, nullable=True)       # 复核人
    human_reviewed_at = Column(DateTime, nullable=True)      # 复核时间

    # 关系
    record = relationship("InspectionRecord", back_populates="scoring_results")


# ==================== 报告表 ====================
class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String(50), unique=True, nullable=False, index=True)  # R-YYYYMMDD-XXXXXXXX
    task_id = Column(String(50), ForeignKey("inspection_tasks.task_id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    report_type = Column(String(20), nullable=False, default="full")
    version = Column(Integer, nullable=False, default=1)  # 报告版本号
    total_score = Column(Numeric(5, 2), nullable=True)  # 项目总分 0-100
    content_json = Column(Text, nullable=True)  # 报告内容 JSON
    file_path = Column(String(255), nullable=True)  # Word/PDF 文件路径
    generated_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    task = relationship("InspectionTask", back_populates="report")


# ==================== 综合分析记录表 ====================
class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(50), unique=True, nullable=False, index=True)  # ANA-YYYYMMDD-XXXXXXXX
    mode = Column(String(20), nullable=False)  # cross_project / cross_time / all_projects
    project_a_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    project_b_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    report_a_id = Column(String(50), nullable=True)
    report_b_id = Column(String(50), nullable=True)
    time_range_start = Column(String(20), nullable=True)
    time_range_end = Column(String(20), nullable=True)
    result_json = Column(Text, nullable=True)  # 完整分析结果 JSON
    summary_text = Column(Text, nullable=True)  # 执行摘要文本
    file_path = Column(String(255), nullable=True)  # Word 文件路径
    pdf_path = Column(String(255), nullable=True)  # PDF 文件路径
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    project_a = relationship("Project", foreign_keys=[project_a_id])
    project_b = relationship("Project", foreign_keys=[project_b_id])


# ==================== 整改记录表 ====================
class Rectification(Base):
    __tablename__ = "rectifications"

    id = Column(Integer, primary_key=True, index=True)
    rectification_id = Column(String(50), unique=True, nullable=False, index=True)  # RECT-YYYYMMDD-xxxxxxxx
    issue_id = Column(String(50), ForeignKey("issues.issue_id"), nullable=False, index=True)
    record_id = Column(String(50), ForeignKey("inspection_records.record_id"), nullable=False)
    task_id = Column(String(50), ForeignKey("inspection_tasks.task_id"), nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending/submitted/ai_approved/ai_rejected/approved/rejected
    rectification_note = Column(Text, nullable=True)  # 整改说明
    rectification_time = Column(String(20), nullable=True)  # 整改完成时间（项目人员填写）
    submitted_at = Column(DateTime, nullable=True)  # 提交时间
    ai_result = Column(Text, nullable=True)  # AI核查结果JSON
    ai_checked_at = Column(DateTime, nullable=True)  # AI核查时间
    reviewed_at = Column(DateTime, nullable=True)  # 管理员审核时间
    review_note = Column(Text, nullable=True)  # 审核意见
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 审核人
    round_number = Column(Integer, default=1)  # 整改轮次（1=首次, 2=二次整改...）
    deadline = Column(String(10), nullable=True)  # 整改截止日期 "YYYY-MM-DD" = check_date + 30天
    reminder_sent = Column(String(20), nullable=True)  # 提醒状态: NULL / "expiring" / "expired"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    issue = relationship("Issue", backref="rectifications")
    record = relationship("InspectionRecord", backref="rectifications")
    task = relationship("InspectionTask", backref="rectifications")
    reviewer = relationship("User", foreign_keys=[reviewer_id])


# ==================== 分析关联项目表（模式三多项目） ====================
class AnalysisProject(Base):
    __tablename__ = "analysis_projects"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(50), nullable=False, index=True)
    project_id = Column(Integer, nullable=False)
    report_id = Column(String(50), nullable=True)
    rank_position = Column(Integer, nullable=True)  # 排名（模式三用）
    grade = Column(String(5), nullable=True)  # 评级 A+/A/A-/B+/B/C


# ==================== 任务进度持久化表 ====================
class TaskProgress(Base):
    """后台任务进度持久化（评分/报告/分析共用）"""
    __tablename__ = "task_progress"

    id = Column(Integer, primary_key=True, index=True)
    progress_key = Column(String(100), unique=True, nullable=False, index=True)  # 类型前缀+ID，如 "scoring:TASK-xxx"
    progress_type = Column(String(20), nullable=False)  # scoring / report / analysis
    ref_id = Column(String(50), nullable=False)  # task_id 或 analysis_id
    status = Column(String(20), nullable=False, default="pending")  # pending/scoring/generating/running/completed/failed
    detail_json = Column(Text, nullable=True)  # JSON: 模块级进度、current_step 等
    error = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== LLM用量日志表 ====================
class LlmUsageLog(Base):
    __tablename__ = "llm_usage_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    model_name = Column(String(50))
    call_type = Column(String(50))
    prompt_tokens = Column(Integer, default=0)           # DeepSeek返回的合并值(含cache)
    completion_tokens = Column(Integer, default=0)        # = output_tokens
    total_tokens = Column(Integer, default=0)
    # DeepSeek 细分字段（其他模型这些值为0）
    input_cache_hit_tokens = Column(Integer, default=0)   # input_tokens_detail.cache_read_tokens
    input_cache_miss_tokens = Column(Integer, default=0)  # input_tokens_detail.cache_miss_tokens
    duration_ms = Column(Integer, default=0)
    task_id = Column(String(50), nullable=True, index=True)
    success = Column(Boolean, default=True)


# ==================== 偏见检测记录表 ====================
class BiasDetection(Base):
    __tablename__ = "bias_detection"

    id = Column(Integer, primary_key=True, index=True)
    detection_id = Column(String(50), unique=True, nullable=False, index=True)  # BIA-YYYYMMDD-XXX

    # 检测维度
    dimension_type = Column(String(20), nullable=False)  # module/inspector
    dimension_value = Column(String(50), nullable=False)  # 如"安全管理"或"user_5"

    # 统计数据
    total_samples = Column(Integer, default=0)           # 样本数
    ai_mean_score = Column(Numeric(3, 2), nullable=True)  # AI平均分
    human_mean_score = Column(Numeric(3, 2), nullable=True)  # 人工平均分
    deviation_rate = Column(Numeric(5, 2), nullable=True)  # 偏差率 = |AI-Human| / Human * 100%

    # 告警状态
    is_alert = Column(Boolean, default=False)           # 是否触发告警
    alert_level = Column(String(10), nullable=True)      # warning/critical
    alert_threshold = Column(Numeric(5, 2), nullable=True)  # 触发告警的阈值

    # 元数据
    analysis_period_start = Column(String(20), nullable=True)  # 分析周期开始
    analysis_period_end = Column(String(20), nullable=True)    # 分析周期结束
    detected_at = Column(DateTime, default=datetime.utcnow)


# ==================== 边缘案例库表 ====================
class EdgeCaseLibrary(Base):
    __tablename__ = "edge_case_library"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String(50), unique=True, nullable=False, index=True)  # EC-YYYYMMDD-XXX

    # 案例分类
    case_type = Column(String(50), nullable=False)  # blurry_photo/missing_description/multiple_issues等
    module_name = Column(String(50), nullable=True)  # 所属模块
    item_id = Column(String(20), nullable=True)      # 关联检查项

    # 案例描述
    title = Column(String(200), nullable=False)      # 案例标题
    description = Column(Text, nullable=True)        # 详细描述
    typical_input = Column(Text, nullable=True)       # 典型输入（JSON）
    expected_score_range = Column(String(20), nullable=True)  # 期望分数范围 "3.0-4.0"

    # 统计
    occurrence_count = Column(Integer, default=0)    # 出现次数
    hit_count = Column(Integer, default=0)            # 命中次数（被正确识别）
    miss_count = Column(Integer, default=0)          # 漏检次数（应识别但未识别）
    hit_rate = Column(Numeric(5, 2), default=0)      # 命中率

    # 状态
    is_active = Column(Boolean, default=True)        # 是否启用
    review_status = Column(String(20), default="pending_review")  # pending_review/approved/rejected
    resolution_status = Column(String(20), default="pending")  # pending/analyzed/resolved
    resolution_note = Column(Text, nullable=True)    # 解决方案

    # 审核信息
    reviewed_by = Column(Integer, nullable=True)      # 审核人
    reviewed_at = Column(DateTime, nullable=True)     # 审核时间

    # 元数据
    first_occurrence = Column(DateTime, nullable=True)   # 首次出现时间
    last_occurrence = Column(DateTime, nullable=True)   # 最近出现时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== AI评估指标表 ====================
class AIMetrics(Base):
    __tablename__ = "ai_metrics"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(String(50), unique=True, nullable=False, index=True)  # MET-YYYYMMDD-XXX

    # 时间范围
    period_start = Column(String(20), nullable=False)
    period_end = Column(String(20), nullable=False)

    # 准确性指标
    total_scored = Column(Integer, default=0)           # 总评分次数
    total_edited = Column(Integer, default=0)           # 人工修改次数
    consistency_rate = Column(Numeric(5, 2), default=0)  # 一致性率 = 1 - edited/total

    # 准确性细分
    accuracy_rate = Column(Numeric(5, 2), nullable=True)  # 准确率（与golden dataset对比）
    f1_score = Column(Numeric(5, 4), nullable=True)      # F1分数
    precision_score = Column(Numeric(5, 4), nullable=True)
    recall_score = Column(Numeric(5, 4), nullable=True)

    # 置信度分布
    high_confidence_count = Column(Integer, default=0)   # 置信度>=0.8
    medium_confidence_count = Column(Integer, default=0) # 置信度0.5-0.8
    low_confidence_count = Column(Integer, default=0)    # 置信度<0.5

    # 边缘案例统计
    edge_cases_detected = Column(Integer, default=0)
    edge_cases_hit_rate = Column(Numeric(5, 2), default=0)

    # 偏见指标
    max_module_deviation = Column(Numeric(5, 2), default=0)   # 最大模块偏差率
    max_inspector_deviation = Column(Numeric(5, 2), default=0)  # 最大检查员偏差率
    active_bias_alerts = Column(Integer, default=0)

    # 性能指标
    avg_response_time_ms = Column(Integer, default=0)    # 平均响应时间
    timeout_count = Column(Integer, default=0)           # 超时次数
    fallback_count = Column(Integer, default=0)         # 降级次数

    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== 项目长记忆表 ====================
class ProjectMemory(Base):
    """项目长记忆：跨检查周期记住关键信息"""
    __tablename__ = "project_memories"

    id = Column(Integer, primary_key=True, index=True)
    memory_id = Column(String(50), unique=True, nullable=False, index=True)  # MEM-YYYYMMDD-XXX

    # 关联信息
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    task_id = Column(String(50), nullable=True)  # 来源任务

    # 记忆内容
    memory_type = Column(String(30), nullable=False)  # recurring_issue/pattern/bias_note/score_pattern
    content = Column(Text, nullable=False)  # 记忆内容（JSON格式）
    summary = Column(String(200), nullable=True)  # 摘要（用于展示）

    # 关联维度
    module_name = Column(String(50), nullable=True)  # 关联模块
    item_id = Column(String(20), nullable=True)  # 关联检查项
    severity = Column(String(20), nullable=True)  # 关联严重程度

    # 统计
    confidence = Column(Numeric(3, 2), default=0.8)  # 记忆可信度 0-1
    occurrence_count = Column(Integer, default=1)  # 出现次数
    last_accessed = Column(DateTime, default=datetime.utcnow)  # 最后访问时间
    access_count = Column(Integer, default=0)  # 被引用次数

    # 状态
    is_active = Column(Boolean, default=True)  # 是否启用
    is_verified = Column(Boolean, default=False)  # 是否已人工验证

    # 时间
    first_seen = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    project = relationship("Project")


# ==================== 消息通知表 ====================
class Notification(Base):
    """系统消息通知"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(String(50), unique=True, nullable=False, index=True)  # NTF-YYYYMMDD-XXX

    # 接收人
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    username = Column(String(50), nullable=False)

    # 通知内容
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    notify_type = Column(String(30), nullable=False)  # task_assigned/inspection_complete/scoring_complete/report_ready/rectification_reminder/rectification_rejected/rectification_approved

    # 关联业务
    ref_type = Column(String(20), nullable=True)   # task/record/report/rectification
    ref_id = Column(String(50), nullable=True)     # 关联的业务ID

    # 状态
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    user = relationship("User")


# ==================== 编译评分规则表（技能编译） ====================
class ScoringRule(Base):
    """从人工修正案例中抽象提取的评分规则"""
    __tablename__ = "scoring_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(String(50), unique=True, nullable=False, index=True)  # RULE-YYYYMMDD-XXX

    # 规则作用域
    module_name = Column(String(50), nullable=False, index=True)
    severity_pattern = Column(String(20), nullable=True)              # 严重/一般/轻微/any
    issue_keyword = Column(String(100), nullable=True)                # 触发关键词

    # 抽象规则
    rule_text = Column(Text, nullable=False)                          # 规则描述
    score_directive = Column(String(100), nullable=True)              # 评分指令

    # 来源与统计
    source_case_count = Column(Integer, default=1)                    # 编译来源案例数
    support_rate = Column(Numeric(5, 4), default=1.0)                # 支持率
    avg_ai_deviation = Column(Numeric(3, 2), default=0)              # AI平均偏差

    # 状态
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verified_by = Column(Integer, nullable=True)

    # 时间
    compiled_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== 评分修正指令表（自我改进） ====================
class ScoringDirective(Base):
    """评分修正指令（自我改进循环产出）"""
    __tablename__ = "scoring_directives"

    id = Column(Integer, primary_key=True, index=True)
    directive_id = Column(String(50), unique=True, nullable=False, index=True)  # DIR-YYYYMMDD-XXX

    # 作用域
    module_name = Column(String(50), nullable=False, index=True)
    trigger_condition = Column(String(200), nullable=True)            # 触发条件

    # 修正指令
    directive_text = Column(Text, nullable=False)                     # 注入Prompt的指令
    direction = Column(String(10), nullable=False)                    # higher/lower
    magnitude = Column(Numeric(3, 2), default=0)                      # 调整幅度

    # 效果验证
    pre_deviation = Column(Numeric(5, 2), default=0)                  # 启用前偏差
    post_deviation = Column(Numeric(5, 2), nullable=True)             # 启用后偏差
    improvement_pct = Column(Numeric(5, 2), nullable=True)            # 改善百分比
    validation_status = Column(String(20), default="pending")         # pending/improved/unchanged/worsened

    # 来源
    source_alert_id = Column(String(50), nullable=True)               # 关联 BiasDetection
    sample_count = Column(Integer, default=0)

    # 状态
    is_active = Column(Boolean, default=True)
    confidence = Column(Numeric(3, 2), default=0.5)

    # 时间
    created_at = Column(DateTime, default=datetime.utcnow)
    validated_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== Prompt模板表 ====================
class PromptTemplate(Base):
    """Prompt版本管理（在线编辑、版本化、热加载）"""
    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, index=True)
    prompt_key = Column(String(50), unique=True, nullable=False, index=True)  # scoring_module, report_generate, etc.
    version = Column(Integer, default=1)
    template = Column(Text, nullable=False)
    description = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
