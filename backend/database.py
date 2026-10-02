"""
数据库配置模块
使用 SQLAlchemy ORM
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings
from core.logger import get_logger

logger = get_logger("database")

# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite 需此参数
    pool_pre_ping=True,
    pool_size=20,           # 连接池大小，支持8人并发+后台评分线程
    max_overflow=10,        # 超出pool_size后最多创建的临时连接
    pool_recycle=300        # 5分钟回收连接，避免SQLite锁积累
)


# 开启 SQLite WAL 模式 — 允许并发读写，提升多人同时操作性能
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")  # 写冲突时等待5秒而非立即报错
    cursor.execute("PRAGMA synchronous=NORMAL")  # 平衡性能与安全性，比FULL快很多
    cursor.execute("PRAGMA cache_size=-8000")     # 8MB缓存，提升查询速度
    cursor.close()


# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def get_db():
    """获取数据库会话（依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库（创建所有表）"""
    from models import models  # 导入模型
    Base.metadata.create_all(bind=engine)
    _migrate_scoring_results()
    _migrate_scoring_results_confidence()  # 置信度字段
    _migrate_users_phone()
    _migrate_users_must_change_pwd()
    _migrate_supervisor_to_field_supervisor()
    _migrate_users_project_id()
    _backfill_scoring_template_fields()
    _migrate_analysis_records()
    _migrate_analysis_projects()
    _migrate_task_progress()
    _migrate_llm_usage_logs()
    _migrate_bias_detection()
    _migrate_edge_case_library()
    _migrate_ai_metrics()
    _migrate_project_memories()  # 项目长记忆表
    _migrate_reports_version()   # reports 表 version 字段
    _migrate_add_indexes()       # 为缺少索引的外键列添加索引
    _migrate_scoring_rules()     # 编译评分规则表（技能编译）
    _migrate_scoring_directives()  # 评分修正指令表（自我改进）
    _migrate_prompt_templates()    # Prompt版本管理表
    _migrate_rectification_round() # 整改多轮次字段
    _migrate_rectification_deadline()  # 整改截止日期+提醒状态
    _migrate_photo_metadata()      # 照片水印元数据字段
    _migrate_system_settings()     # 系统设置表（API KEY 管理）
    _migrate_custom_standards()    # 自定义检查标准表（标准导入功能）


def _migrate_users_must_change_pwd():
    """为 users 表添加 must_change_pwd 列"""
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(users)"))
        existing_cols = {row[1] for row in result.fetchall()}
        if 'must_change_pwd' not in existing_cols:
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN must_change_pwd BOOLEAN DEFAULT 0"))
                conn.commit()
                logger.info("Added column: must_change_pwd")
            except Exception as e:
                logger.debug(f"Skip must_change_pwd: {e}")


def _migrate_users_project_id():
    """为 users 表添加 project_id 列（驻场经理/项目人员所属项目）"""
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(users)"))
        existing_cols = {row[1] for row in result.fetchall()}
        if 'project_id' not in existing_cols:
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN project_id INTEGER REFERENCES projects(id)"))
                conn.commit()
                logger.info("Added column: project_id to users")
            except Exception as e:
                logger.debug(f"Skip project_id: {e}")


def _migrate_supervisor_to_field_supervisor():
    """将数据库中 supervisor 角色迁移为 field_supervisor"""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("UPDATE users SET role='field_supervisor' WHERE role='supervisor'"))
            conn.commit()
        except Exception as e:
            logger.debug(f"Skip supervisor migration: {e}")


def _migrate_users_phone():
    """为 users 表添加 phone 列（兼容已有数据库）"""
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(users)"))
        existing_cols = {row[1] for row in result.fetchall()}
        if 'phone' not in existing_cols:
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(20)"))
                # partial unique index：允许多个 NULL，但非 NULL 值唯一
                conn.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_phone ON users(phone) WHERE phone IS NOT NULL"
                ))
                conn.commit()
                logger.info("Added column: phone")
            except Exception as e:
                logger.debug(f"Skip phone: {e}")


def _migrate_scoring_results():
    """为 scoring_results 表添加新字段（兼容已有数据库）"""
    from sqlalchemy import text
    with engine.connect() as conn:
        migrations = [
            ("is_edited", "ALTER TABLE scoring_results ADD COLUMN is_edited BOOLEAN DEFAULT 0"),
            ("edited_by", "ALTER TABLE scoring_results ADD COLUMN edited_by INTEGER"),
            ("edited_at", "ALTER TABLE scoring_results ADD COLUMN edited_at DATETIME"),
            ("check_standard", "ALTER TABLE scoring_results ADD COLUMN check_standard TEXT"),
            ("check_method", "ALTER TABLE scoring_results ADD COLUMN check_method TEXT"),
            ("scoring_rule", "ALTER TABLE scoring_results ADD COLUMN scoring_rule TEXT"),
            ("is_fallback", "ALTER TABLE scoring_results ADD COLUMN is_fallback BOOLEAN DEFAULT 0"),
            ("edit_reason", "ALTER TABLE scoring_results ADD COLUMN edit_reason VARCHAR(200)"),
            ("original_score", "ALTER TABLE scoring_results ADD COLUMN original_score DECIMAL(3,1)"),
            ("jev_confidence", "ALTER TABLE scoring_results ADD COLUMN jev_confidence DECIMAL(4,3)"),
            ("jev_direction", "ALTER TABLE scoring_results ADD COLUMN jev_direction VARCHAR(10)"),
        ]
        # 检查已有列，避免重复添加
        result = conn.execute(text("PRAGMA table_info(scoring_results)"))
        existing_cols = {row[1] for row in result.fetchall()}
        for col_name, sql in migrations:
            if col_name not in existing_cols:
                try:
                    conn.execute(text(sql))
                    logger.info(f"Added column: {col_name}")
                except Exception as e:
                    logger.debug(f"Skip {col_name}: {e}")
        conn.commit()


def _migrate_analysis_records():
    """创建 analysis_records 表（如果不存在）"""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS analysis_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id VARCHAR(50) UNIQUE NOT NULL,
                    mode VARCHAR(20) NOT NULL,
                    project_a_id INTEGER,
                    project_b_id INTEGER,
                    report_a_id VARCHAR(50),
                    report_b_id VARCHAR(50),
                    time_range_start VARCHAR(20),
                    time_range_end VARCHAR(20),
                    result_json TEXT,
                    summary_text TEXT,
                    file_path VARCHAR(255),
                    pdf_path VARCHAR(255),
                    created_by INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_analysis_records_analysis_id ON analysis_records(analysis_id)"
            ))
            # 为旧表添加 pdf_path 列
            try:
                conn.execute(text("ALTER TABLE analysis_records ADD COLUMN pdf_path VARCHAR(255)"))
            except Exception:
                pass  # 列已存在
            conn.commit()
            logger.info("analysis_records table ready")
        except Exception as e:
            logger.debug(f"Skip analysis_records: {e}")


def _migrate_analysis_projects():
    """创建 analysis_projects 表（如果不存在）"""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS analysis_projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id VARCHAR(50) NOT NULL,
                    project_id INTEGER NOT NULL,
                    report_id VARCHAR(50),
                    rank_position INTEGER,
                    grade VARCHAR(5)
                )
            """))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_analysis_projects_analysis_id ON analysis_projects(analysis_id)"
            ))
            conn.commit()
            logger.info("analysis_projects table ready")
        except Exception as e:
            logger.debug(f"Skip analysis_projects: {e}")


def _backfill_scoring_template_fields():
    """回填已有评分记录的检查标准、检查方法、评分规则字段"""
    from models.models import ScoringResult, InspectionRecord, InspectionTask
    from api.tasks import load_template_items

    db = SessionLocal()
    try:
        # 查找所有 check_standard 为空的评分记录
        empty_results = db.query(ScoringResult).filter(
            (ScoringResult.check_standard == None) | (ScoringResult.check_standard == "")
        ).all()

        if not empty_results:
            return

        # 按 (task_id, module_name) 分组，批量回填
        task_cache = {}  # task_id -> standard_type
        template_cache = {}  # (module_name, standard_type) -> {item_id: item}
        updated = 0

        for r in empty_results:
            # 获取 record -> task 的 standard_type
            record = db.query(InspectionRecord).filter(
                InspectionRecord.record_id == r.record_id
            ).first()
            if not record:
                continue

            if record.task_id not in task_cache:
                task = db.query(InspectionTask).filter(
                    InspectionTask.task_id == record.task_id
                ).first()
                task_cache[record.task_id] = task.standard_type if task else "diecheng"

            standard_type = task_cache[record.task_id]

            # 加载模板
            cache_key = (r.module_name, standard_type)
            if cache_key not in template_cache:
                items = load_template_items(r.module_name, standard_type)
                template_cache[cache_key] = {item["item_id"]: item for item in items}

            items_map = template_cache[cache_key]
            template_item = items_map.get(r.item_id)
            if template_item:
                r.check_standard = template_item.get("check_standard", "")
                r.check_method = template_item.get("check_method", "")
                r.scoring_rule = template_item.get("scoring_rule", "")
                updated += 1

        db.commit()
        if updated > 0:
            logger.info(f"回填了 {updated} 条评分记录的模板字段")
    except Exception as e:
        logger.error(f"回填失败: {e}")
    finally:
        db.close()


def _migrate_task_progress():
    """创建 task_progress 表（如果不存在）"""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS task_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    progress_key VARCHAR(100) UNIQUE NOT NULL,
                    progress_type VARCHAR(20) NOT NULL,
                    ref_id VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    detail_json TEXT,
                    error TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_task_progress_key ON task_progress(progress_key)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_task_progress_type ON task_progress(progress_type)"
            ))
            conn.commit()
            logger.info("task_progress table ready")
        except Exception as e:
            logger.debug(f"Skip task_progress: {e}")


def _migrate_llm_usage_logs():
    """创建 llm_usage_logs 表（如果不存在）"""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS llm_usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    model_name VARCHAR(50),
                    call_type VARCHAR(50),
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    duration_ms INTEGER DEFAULT 0,
                    task_id VARCHAR(50),
                    success BOOLEAN DEFAULT 1
                )
            """))
            conn.commit()
            logger.info("llm_usage_logs table ready")
        except Exception as e:
            logger.debug(f"Skip llm_usage_logs: {e}")


def _migrate_scoring_results_confidence():
    """为 scoring_results 表添加置信度相关字段"""
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(scoring_results)"))
        existing_cols = {row[1] for row in result.fetchall()}
        migrations = [
            ("confidence_score", "ALTER TABLE scoring_results ADD COLUMN confidence_score DECIMAL(3,2)"),
            ("needs_human_review", "ALTER TABLE scoring_results ADD COLUMN needs_human_review BOOLEAN DEFAULT 0"),
            ("human_reviewed", "ALTER TABLE scoring_results ADD COLUMN human_reviewed BOOLEAN DEFAULT 0"),
            ("human_reviewed_by", "ALTER TABLE scoring_results ADD COLUMN human_reviewed_by INTEGER"),
            ("human_reviewed_at", "ALTER TABLE scoring_results ADD COLUMN human_reviewed_at DATETIME"),
        ]
        for col_name, sql in migrations:
            if col_name not in existing_cols:
                try:
                    conn.execute(text(sql))
                    logger.info(f"Added column: {col_name}")
                except Exception as e:
                    logger.debug(f"Skip {col_name}: {e}")
        conn.commit()


def _migrate_bias_detection():
    """创建 bias_detection 表（如果不存在）"""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS bias_detection (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    detection_id VARCHAR(50) UNIQUE NOT NULL,
                    dimension_type VARCHAR(20) NOT NULL,
                    dimension_value VARCHAR(50) NOT NULL,
                    total_samples INTEGER DEFAULT 0,
                    ai_mean_score DECIMAL(3,2),
                    human_mean_score DECIMAL(3,2),
                    deviation_rate DECIMAL(5,2),
                    is_alert BOOLEAN DEFAULT 0,
                    alert_level VARCHAR(10),
                    alert_threshold DECIMAL(5,2),
                    analysis_period_start VARCHAR(20),
                    analysis_period_end VARCHAR(20),
                    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bias_detection_id ON bias_detection(detection_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bias_detection_type ON bias_detection(dimension_type)"))
            conn.commit()
            logger.info("bias_detection table ready")
        except Exception as e:
            logger.debug(f"Skip bias_detection: {e}")


def _migrate_edge_case_library():
    """创建 edge_case_library 表（如果不存在）"""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS edge_case_library (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id VARCHAR(50) UNIQUE NOT NULL,
                    case_type VARCHAR(50) NOT NULL,
                    module_name VARCHAR(50),
                    item_id VARCHAR(20),
                    title VARCHAR(200) NOT NULL,
                    description TEXT,
                    typical_input TEXT,
                    expected_score_range VARCHAR(20),
                    occurrence_count INTEGER DEFAULT 0,
                    hit_count INTEGER DEFAULT 0,
                    miss_count INTEGER DEFAULT 0,
                    hit_rate DECIMAL(5,2) DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    review_status VARCHAR(20) DEFAULT 'pending_review',
                    resolution_status VARCHAR(20) DEFAULT 'pending',
                    resolution_note TEXT,
                    reviewed_by INTEGER,
                    reviewed_at DATETIME,
                    first_occurrence DATETIME,
                    last_occurrence DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_edge_case_id ON edge_case_library(case_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_edge_case_type ON edge_case_library(case_type)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_edge_case_status ON edge_case_library(review_status)"))
            conn.commit()
            logger.info("edge_case_library table ready")
        except Exception as e:
            logger.debug(f"Skip edge_case_library: {e}")


def _migrate_ai_metrics():
    """创建 ai_metrics 表（如果不存在）"""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS ai_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id VARCHAR(50) UNIQUE NOT NULL,
                    period_start VARCHAR(20) NOT NULL,
                    period_end VARCHAR(20) NOT NULL,
                    total_scored INTEGER DEFAULT 0,
                    total_edited INTEGER DEFAULT 0,
                    consistency_rate DECIMAL(5,2) DEFAULT 0,
                    accuracy_rate DECIMAL(5,2),
                    f1_score DECIMAL(5,4),
                    precision_score DECIMAL(5,4),
                    recall_score DECIMAL(5,4),
                    high_confidence_count INTEGER DEFAULT 0,
                    medium_confidence_count INTEGER DEFAULT 0,
                    low_confidence_count INTEGER DEFAULT 0,
                    edge_cases_detected INTEGER DEFAULT 0,
                    edge_cases_hit_rate DECIMAL(5,2) DEFAULT 0,
                    max_module_deviation DECIMAL(5,2) DEFAULT 0,
                    max_inspector_deviation DECIMAL(5,2) DEFAULT 0,
                    active_bias_alerts INTEGER DEFAULT 0,
                    avg_response_time_ms INTEGER DEFAULT 0,
                    timeout_count INTEGER DEFAULT 0,
                    fallback_count INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ai_metrics_id ON ai_metrics(record_id)"))
            conn.commit()
            logger.info("ai_metrics table ready")
        except Exception as e:
            logger.debug(f"Skip ai_metrics: {e}")


def _migrate_project_memories():
    """创建 project_memories 表（如果不存在）"""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS project_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id VARCHAR(50) UNIQUE NOT NULL,
                    project_id INTEGER NOT NULL,
                    task_id VARCHAR(50),
                    memory_type VARCHAR(30) NOT NULL,
                    content TEXT NOT NULL,
                    summary VARCHAR(200),
                    module_name VARCHAR(50),
                    item_id VARCHAR(20),
                    severity VARCHAR(20),
                    confidence DECIMAL(3,2) DEFAULT 0.8,
                    occurrence_count INTEGER DEFAULT 1,
                    last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    is_verified BOOLEAN DEFAULT 0,
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_project_memories_id ON project_memories(memory_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_project_memories_project ON project_memories(project_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_project_memories_type ON project_memories(memory_type)"))
            conn.commit()
            logger.info("project_memories table ready")
        except Exception as e:
            logger.debug(f"Skip project_memories: {e}")


def _migrate_reports_version():
    """为 reports 表添加 version 列（如不存在）"""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            result = conn.execute(text("PRAGMA table_info(reports)"))
            existing_cols = {row[1] for row in result.fetchall()}
            if 'version' not in existing_cols:
                conn.execute(text("ALTER TABLE reports ADD COLUMN version INTEGER DEFAULT 1"))
                conn.commit()
                logger.info("Added column: version to reports")
            else:
                logger.info("Column reports.version already exists")
        except Exception as e:
            logger.debug(f"Skip reports.version migration: {e}")


def _migrate_add_indexes():
    """为缺少索引的高频查询外键列添加索引"""
    from sqlalchemy import text
    indexes_to_add = [
        ("issues", "record_id", "ix_issues_record_id"),
        ("photos", "issue_id", "ix_photos_issue_id"),
        ("rectifications", "issue_id", "ix_rects_issue_id"),
        ("inspection_records", "project_id", "ix_records_project_id"),
        ("inspection_records", "inspector_id", "ix_records_inspector_id"),
        ("llm_usage_logs", "task_id", "ix_llm_task_id"),
        ("notifications", "user_id", "ix_notifications_user_id"),
    ]
    for table, column, idx_name in indexes_to_add:
        try:
            with engine.connect() as conn:
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})"))
            logger.info(f"索引 {idx_name} 已确保存在")
        except Exception as e:
            logger.debug(f"索引 {idx_name} 跳过: {e}")


def _migrate_scoring_rules():
    """创建 scoring_rules 表（如果不存在）"""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS scoring_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id VARCHAR(50) UNIQUE NOT NULL,
                    module_name VARCHAR(50) NOT NULL,
                    severity_pattern VARCHAR(20),
                    issue_keyword VARCHAR(100),
                    rule_text TEXT NOT NULL,
                    score_directive VARCHAR(100),
                    source_case_count INTEGER DEFAULT 1,
                    support_rate DECIMAL(5,4) DEFAULT 1.0,
                    avg_ai_deviation DECIMAL(3,2) DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    is_verified BOOLEAN DEFAULT 0,
                    verified_by INTEGER,
                    compiled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_scoring_rules_id ON scoring_rules(rule_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_scoring_rules_module ON scoring_rules(module_name)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_scoring_rules_active ON scoring_rules(is_active)"))
            conn.commit()
            logger.info("scoring_rules table ready")
        except Exception as e:
            logger.debug(f"Skip scoring_rules: {e}")


def _migrate_scoring_directives():
    """创建 scoring_directives 表（如果不存在）"""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS scoring_directives (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    directive_id VARCHAR(50) UNIQUE NOT NULL,
                    module_name VARCHAR(50) NOT NULL,
                    trigger_condition VARCHAR(200),
                    directive_text TEXT NOT NULL,
                    direction VARCHAR(10) NOT NULL,
                    magnitude DECIMAL(3,2) DEFAULT 0,
                    pre_deviation DECIMAL(5,2) DEFAULT 0,
                    post_deviation DECIMAL(5,2),
                    improvement_pct DECIMAL(5,2),
                    validation_status VARCHAR(20) DEFAULT 'pending',
                    source_alert_id VARCHAR(50),
                    sample_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    confidence DECIMAL(3,2) DEFAULT 0.5,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    validated_at DATETIME,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_scoring_dir_id ON scoring_directives(directive_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_scoring_dir_module ON scoring_directives(module_name)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_scoring_dir_active ON scoring_directives(is_active)"))
            conn.commit()
            logger.info("scoring_directives table ready")
        except Exception as e:
            logger.debug(f"Skip scoring_directives: {e}")


def _migrate_prompt_templates():
    """创建 prompt_templates 表（如果不存在）"""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS prompt_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt_key VARCHAR(50) UNIQUE NOT NULL,
                    version INTEGER DEFAULT 1,
                    template TEXT NOT NULL,
                    description VARCHAR(200),
                    is_active BOOLEAN DEFAULT 1,
                    updated_by INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_prompt_key ON prompt_templates(prompt_key)"))
            conn.commit()
            logger.info("prompt_templates table ready")
        except Exception as e:
            logger.debug(f"Skip prompt_templates: {e}")


def _migrate_rectification_round():
    """为 rectifications 表添加 round_number 列"""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            result = conn.execute(text("PRAGMA table_info(rectifications)"))
            existing_cols = {row[1] for row in result.fetchall()}
            if 'round_number' not in existing_cols:
                conn.execute(text("ALTER TABLE rectifications ADD COLUMN round_number INTEGER DEFAULT 1"))
                conn.commit()
                logger.info("Added column: round_number to rectifications")
        except Exception as e:
            logger.debug(f"Skip round_number migration: {e}")


def _migrate_photo_metadata():
    """为 photos 表添加水印相机元数据字段"""
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(photos)"))
        existing_cols = {row[1] for row in result.fetchall()}
        migrations = [
            ("latitude", "ALTER TABLE photos ADD COLUMN latitude FLOAT"),
            ("longitude", "ALTER TABLE photos ADD COLUMN longitude FLOAT"),
            ("address", "ALTER TABLE photos ADD COLUMN address VARCHAR(500)"),
            ("capture_time", "ALTER TABLE photos ADD COLUMN capture_time DATETIME"),
            ("inspector_name", "ALTER TABLE photos ADD COLUMN inspector_name VARCHAR(50)"),
            ("watermark_hash", "ALTER TABLE photos ADD COLUMN watermark_hash VARCHAR(128)"),
        ]
        for col_name, sql in migrations:
            if col_name not in existing_cols:
                try:
                    conn.execute(text(sql))
                    logger.info(f"Added column: {col_name} to photos")
                except Exception as e:
                    logger.debug(f"Skip {col_name}: {e}")
        conn.commit()


def _migrate_rectification_deadline():
    """为 rectifications 表添加 deadline 和 reminder_sent 列，并回填历史数据"""
    from sqlalchemy import text
    from datetime import datetime, timedelta
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(rectifications)"))
        existing_cols = {row[1] for row in result.fetchall()}

        if 'deadline' not in existing_cols:
            conn.execute(text("ALTER TABLE rectifications ADD COLUMN deadline VARCHAR(10)"))
            conn.commit()
            logger.info("Added column: deadline to rectifications")

        if 'reminder_sent' not in existing_cols:
            conn.execute(text("ALTER TABLE rectifications ADD COLUMN reminder_sent VARCHAR(20)"))
            conn.commit()
            logger.info("Added column: reminder_sent to rectifications")

        # 回填：从 task 的 check_date + 30天 写入 deadline（只更新 deadline 为 NULL 的记录）
        backfill_result = conn.execute(text(
            "SELECT r.rectification_id, t.check_date "
            "FROM rectifications r "
            "JOIN inspection_tasks t ON r.task_id = t.task_id "
            "WHERE r.deadline IS NULL AND t.check_date IS NOT NULL"
        ))
        rows = backfill_result.fetchall()
        count = 0
        for row in rows:
            try:
                check_dt = datetime.strptime(row[1], "%Y-%m-%d")
                deadline = (check_dt + timedelta(days=30)).strftime("%Y-%m-%d")
                conn.execute(text(
                    "UPDATE rectifications SET deadline = :deadline WHERE rectification_id = :rid"
                ), {"deadline": deadline, "rid": row[0]})
                count += 1
            except (ValueError, TypeError):
                pass
        if count > 0:
            conn.commit()
            logger.info(f"Backfilled deadline for {count} rectification records")


def _migrate_custom_standards():
    """创建 custom_standards 表（检查标准导入功能生成的自定义标准）"""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS custom_standards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    standard_type VARCHAR(50) UNIQUE NOT NULL,
                    label VARCHAR(100) NOT NULL,
                    scoring_model VARCHAR(20) NOT NULL DEFAULT 'point_cap',
                    modules_json TEXT NOT NULL DEFAULT '{}',
                    module_count INTEGER NOT NULL DEFAULT 0,
                    items_total INTEGER NOT NULL DEFAULT 0,
                    template_file VARCHAR(255) NOT NULL,
                    source_filename VARCHAR(255),
                    created_by INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER NOT NULL DEFAULT 1
                )
            """))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_custom_standards_type ON custom_standards(standard_type)"
            ))
            conn.commit()
            logger.info("custom_standards table ready")
        except Exception as e:
            logger.debug(f"Skip custom_standards: {e}")


def _migrate_system_settings():
    """创建 system_settings 表（运行时可编辑的系统配置，如 API KEY）"""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key VARCHAR(100) UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    updated_by INTEGER,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_system_settings_key ON system_settings(key)"
            ))
            conn.commit()
            logger.info("system_settings table ready")
        except Exception as e:
            logger.debug(f"Skip system_settings: {e}")