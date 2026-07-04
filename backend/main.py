"""
FastAPI 应用入口
物业品质检查系统后端
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from contextlib import asynccontextmanager
from config import settings
from database import init_db
from core.logger import get_logger

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 安全检查：确保 SECRET_KEY 已设置
    if not settings.SECRET_KEY:
        raise RuntimeError(
            "安全错误：请在 .env 文件中设置 SECRET_KEY！\n"
            "生成命令：python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )

    # 启动时初始化数据库
    init_db()
    logger.info("Database initialized")

    # 初始化审计日志表
    from core.audit import ensure_audit_table
    ensure_audit_table()

    # 启动时扫描：为已评分完成但缺少报告的任务自动生成报告
    _recover_missed_reports()

    # 启动时恢复未完成的后台任务进度（从数据库加载到内存）
    _recover_progress_from_db()

    # 启动定时任务：每日凌晨2点收集AI评估指标
    _start_scheduler()

    # 启动时立即生成整改到期/逾期提醒通知
    try:
        _scheduled_rectification_reminders()
        logger.info("启动时整改提醒已执行")
    except Exception as e:
        logger.error(f"启动时整改提醒失败: {e}")

    yield

    # ===== 关机逻辑：释放资源 =====
    logger.info("应用正在关闭，清理资源...")

    # 关闭共享 httpx 客户端
    from core.llm_client import QwenClient, DeepSeekClient
    for client_cls in [QwenClient, DeepSeekClient]:
        try:
            if client_cls._shared_client and not client_cls._shared_client.is_closed:
                await client_cls._shared_client.aclose()
                logger.info(f"已关闭 {client_cls.__name__} httpx 客户端")
        except Exception as e:
            logger.error(f"关闭 {client_cls.__name__} 客户端失败: {e}")

    # 释放数据库引擎
    try:
        from database import engine
        engine.dispose()
        logger.info("数据库引擎已释放")
    except Exception as e:
        logger.error(f"释放数据库引擎失败: {e}")

    # 关闭定时任务调度器
    if _scheduler_instance and _scheduler_instance.running:
        _scheduler_instance.shutdown(wait=False)
        logger.info("定时任务调度器已关闭")

    logger.info("资源清理完成")


# ==================== 定时任务调度器 ====================
_scheduler_instance = None


def _start_scheduler():
    """启动 APScheduler，注册定时任务"""
    global _scheduler_instance
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from core.metrics_collector import run_metrics_collection

        _scheduler_instance = BackgroundScheduler(timezone="Asia/Shanghai")

        # 每天凌晨2点：收集前一天的AI评估指标
        _scheduler_instance.add_job(
            func=run_metrics_collection,
            trigger="cron",
            hour=2,
            minute=0,
            id="daily_metrics_collection",
            replace_existing=True,
            max_instances=1,
        )

        # 每天凌晨3点：技能编译（从人工修正案例中提取评分规则）
        _scheduler_instance.add_job(
            func=_scheduled_rule_compilation,
            trigger="cron",
            hour=3,
            minute=0,
            id="daily_rule_compilation",
            replace_existing=True,
            max_instances=1,
        )

        # 每天凌晨4点：记忆策展（清理过期记忆，发现跨项目模式）
        _scheduler_instance.add_job(
            func=_scheduled_memory_curation,
            trigger="cron",
            hour=4,
            minute=0,
            id="daily_memory_curation",
            replace_existing=True,
            max_instances=1,
        )

        # 每周一凌晨5点：自我改进循环（从偏见告警生成修正指令）
        _scheduler_instance.add_job(
            func=_scheduled_self_improvement,
            trigger="cron",
            day_of_week="mon",
            hour=5,
            minute=0,
            id="weekly_self_improvement",
            replace_existing=True,
            max_instances=1,
        )

        # 每天凌晨1点：整改到期提醒
        _scheduler_instance.add_job(
            func=_scheduled_rectification_reminders,
            trigger="cron",
            hour=10,
            minute=0,
            id="daily_rectification_reminders",
            replace_existing=True,
            max_instances=1,
        )

        _scheduler_instance.start()
        logger.info("APScheduler 已启动: 10:00整改提醒 | 02:00指标收集 | 03:00技能编译 | 04:00记忆策展 | 周一05:00自我改进")
    except ImportError:
        logger.warning("APScheduler 未安装，定时指标收集已跳过。安装命令: pip install apscheduler")
    except Exception as e:
        logger.error(f"启动定时任务调度器失败: {e}")


# ==================== 定时任务包装函数 ====================

def _scheduled_rectification_reminders():
    """定时任务：按项目汇总，发送到期/逾期提醒（每项目一条通知，直接写SQLite避免异步丢失）"""
    from datetime import datetime, timedelta
    from collections import defaultdict, Counter
    import sqlite3, random

    db_path = str(settings.DATA_DIR / "inspection.db")
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d")
        exp5 = (today + timedelta(days=5)).strftime("%Y-%m-%d")

        # 两种提醒：即将到期（精确匹配5天后）和已逾期（所有deadline < 今天的）
        reminder_configs = [
            ("expiring", "即将到期",
             "SELECT r.rectification_id, r.task_id, r.reminder_sent, i.module_name FROM rectifications r LEFT JOIN issues i ON r.issue_id = i.issue_id WHERE r.status = 'pending' AND r.deadline = ?",
             (exp5,)),
            ("expired", "已逾期",
             "SELECT r.rectification_id, r.task_id, r.reminder_sent, i.module_name FROM rectifications r LEFT JOIN issues i ON r.issue_id = i.issue_id WHERE r.status = 'pending' AND r.deadline < ?",
             (today_str,)),
        ]

        for reminder_type, label, sql, params in reminder_configs:
            c.execute(sql, params)
            rects = [r for r in c.fetchall() if r["reminder_sent"] != reminder_type]
            if not rects:
                continue

            by_task = defaultdict(list)
            for r in rects:
                by_task[r["task_id"]].append(r)

            for task_id, task_rects in by_task.items():
                c.execute("""
                    SELECT p.name, t.project_id FROM inspection_tasks t
                    JOIN projects p ON t.project_id = p.id WHERE t.task_id = ?
                """, (task_id,))
                task_info = c.fetchone()
                if not task_info:
                    continue
                project_name = task_info["name"]
                project_id = task_info["project_id"]

                module_counts = Counter()
                for r in task_rects:
                    module_counts[r["module_name"] or "未知"] += 1
                total_count = sum(module_counts.values())
                module_detail = "、".join(f"{m}{cnt}项" for m, cnt in module_counts.items())

                if reminder_type == "expiring":
                    title = f"整改即将到期 - {project_name}"
                    content = f"项目「{project_name}」有{total_count}条整改将于5天后到期，涉及：{module_detail}。请尽快督促整改。"
                else:
                    title = f"整改已逾期 - {project_name}"
                    content = f"项目「{project_name}」有{total_count}条整改已逾期，涉及：{module_detail}。请立即处理。"

                recipients = set()
                c.execute("""
                    SELECT u.id, u.username FROM users u
                    JOIN user_projects up ON u.id = up.user_id
                    WHERE up.project_id = ? AND u.role = 'field_supervisor' AND u.is_active = 1
                """, (project_id,))
                for r in c.fetchall():
                    recipients.add((r["id"], r["username"]))
                c.execute("SELECT id, username FROM users WHERE role = 'admin' AND is_active = 1")
                for r in c.fetchall():
                    recipients.add((r["id"], r["username"]))

                now = datetime.now().isoformat()
                for user_id, username in recipients:
                    nid = f"NTF-{today.strftime('%Y%m%d')}-{random.randint(100000, 999999)}"
                    c.execute(
                        "INSERT INTO notifications (notification_id, user_id, username, title, content, notify_type, ref_type, ref_id, is_read, created_at) VALUES (?,?,?,?,?,?,?,?,0,?)",
                        (nid, user_id, username, title, content, "rectification_reminder", "task", task_id, now)
                    )

            for r in rects:
                c.execute("UPDATE rectifications SET reminder_sent = ? WHERE rectification_id = ?", (reminder_type, r["rectification_id"]))

            conn.commit()
            if rects:
                logger.info(f"[整改提醒] {len(by_task)}个项目{label}, 共{len(rects)}条记录")

        conn.close()
    except Exception as e:
        logger.error(f"[整改提醒] 失败: {e}")


def _scheduled_rule_compilation():
    """定时任务：技能编译 — 从人工修正案例中抽象评分规则"""
    import asyncio
    try:
        from core.rule_compiler import run_compilation
        loop = asyncio.new_event_loop()
        try:
            rules = loop.run_until_complete(run_compilation())
            logger.info(f"[Scheduler] 技能编译完成，生成 {len(rules)} 条规则")
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"[Scheduler] 技能编译失败: {e}")


def _scheduled_memory_curation():
    """定时任务：记忆策展 — 清理过期记忆，发现跨项目通用模式"""
    try:
        from core.memory_curator import run_curation
        result = run_curation()
        logger.info(f"[Scheduler] 记忆策展完成: {result}")
    except Exception as e:
        logger.error(f"[Scheduler] 记忆策展失败: {e}")


def _scheduled_self_improvement():
    """定时任务：自我改进 — 从偏见告警生成评分修正指令"""
    try:
        from core.self_improver import run_improvement
        result = run_improvement()
        logger.info(f"[Scheduler] 自我改进完成: {result}")
    except Exception as e:
        logger.error(f"[Scheduler] 自我改进失败: {e}")


def _recover_missed_reports():
    """
    启动时安全网：扫描所有已评分完成但缺少报告的任务，自动补生成报告。
    防止服务器重启或异常导致报告遗漏。
    同时处理卡在 reporting 状态的任务。
    """
    import threading
    from database import SessionLocal
    from models.models import InspectionTask, InspectionRecord, ScoringResult as ScoringResultModel, Report

    db = SessionLocal()
    try:
        tasks = db.query(InspectionTask).all()
        recovered = 0
        for task in tasks:
            # 跳过已有报告的任务
            existing_report = db.query(Report).filter(Report.task_id == task.task_id).first()
            if existing_report:
                # 如果任务卡在 reporting 状态但已有报告，重置为 completed
                if task.status == "reporting":
                    task.status = "completed"
                    logger.info(f"[Startup Recovery] 修复卡住的任务状态: {task.task_id} -> completed")
                continue

            # 如果任务卡在 reporting 状态但没有报告，尝试重新生成
            if task.status == "reporting":
                logger.info(f"[Startup Recovery] 发现卡在reporting状态的任务: {task.task_id}，尝试重新生成")
                # 先重置状态为 completed，这样 _check_and_trigger_report 才能处理
                task.status = "completed"

            # 检查是否所有已完成的模块都已评分
            completed_records = db.query(InspectionRecord).filter(
                InspectionRecord.task_id == task.task_id,
                InspectionRecord.status == "completed"
            ).all()

            if not completed_records:
                continue

            all_scored = True
            for record in completed_records:
                count = db.query(ScoringResultModel).filter(
                    ScoringResultModel.record_id == record.record_id
                ).count()
                if count == 0:
                    all_scored = False
                    break

            if not all_scored:
                continue

            # 所有模块已评分且无报告 → 自动补生成
            recovered += 1
            logger.info(f"[Startup Recovery] 发现遗漏报告的任务: {task.task_id}，自动补生成")

            # 使用 scoring.py 的安全触发机制
            from api.scoring import _check_and_trigger_report
            threading.Thread(
                target=_check_and_trigger_report,
                args=(task.task_id,),
                daemon=True
            ).start()

        if recovered > 0:
            logger.info(f"[Startup Recovery] 共发现 {recovered} 个遗漏报告任务，已启动补生成")
        else:
            logger.info("[Startup Recovery] 无遗漏报告")
    finally:
        db.close()


# 创建 FastAPI 应用（禁用默认docs，使用自定义）
app = FastAPI(
    title=settings.APP_NAME,
    description="物业品质检查多Agent系统后端API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,  # 禁用默认 docs
    redoc_url=None  # 禁用默认 redoc
)

# 导出 limiter 供路由模块使用（登录速率限制在 auth.py 内部实现）


# 自定义 Swagger UI（使用国内可访问的 CDN）
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{settings.APP_NAME} - API文档",
        # 使用 bootcdn（国内CDN）
        swagger_js_url="https://cdn.bootcdn.net/ajax/libs/swagger-ui/5.10.5/swagger-ui-bundle.min.js",
        swagger_css_url="https://cdn.bootcdn.net/ajax/libs/swagger-ui/5.10.5/swagger-ui.min.css",
    )


# 自定义 ReDoc（备用文档）
@app.get("/redoc", include_in_schema=False)
async def custom_redoc_html():
    from fastapi.openapi.docs import get_redoc_html
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{settings.APP_NAME} - API文档",
        redoc_js_url="https://cdn.bootcdn.net/ajax/libs/redoc/2.0.0/bundles/redoc.standalone.js",
    )

# 配置 CORS（从环境变量读取，支持多域名逗号分隔）
def _parse_origins() -> list:
    """解析 ALLOWED_ORIGINS 环境变量，支持逗号分隔的多个域名"""
    origins_str = settings.ALLOWED_ORIGINS
    origins = [o.strip() for o in origins_str.split(",") if o.strip()]
    if not origins:
        return ["http://localhost:5173"]  # 默认值
    return origins

CORS_ORIGINS = _parse_origins()

# GZip 压缩中间件 - 减小响应体积，提升传输速度
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


# ==================== 路由注册 ====================
from api import auth, tasks, inspection, scoring, report, users, projects, analysis, rectification, llm_stats, quality_api, orchestrator, knowledge_base_api, notification, prompts, events, guide, geocode, ai_metrics, backup, settings_api

app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/v1/users", tags=["用户管理"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["项目管理"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["检查任务"])
app.include_router(inspection.router, prefix="/api/v1/records", tags=["检查记录"])
app.include_router(scoring.router, prefix="/api/v1/scoring", tags=["评分"])
app.include_router(report.router, prefix="/api/v1/reports", tags=["报告"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["综合分析"])
app.include_router(rectification.router, prefix="/api/v1/rectifications", tags=["整改复查"])
app.include_router(llm_stats.router, prefix="/api/v1/llm-stats", tags=["LLM监控"])
app.include_router(quality_api.router, prefix="/api/v1/quality", tags=["品质检查"])
app.include_router(orchestrator.router, prefix="/api/v1/orchestrator", tags=["Orchestrator编排"])
app.include_router(knowledge_base_api.router, prefix="/api/v1/knowledge", tags=["问题知识库"])
app.include_router(notification.router, prefix="/api/v1/notifications", tags=["通知"])
app.include_router(prompts.router,      prefix="/api/v1/admin",        tags=["Prompt管理"])
app.include_router(settings_api.router, prefix="/api/v1/admin",        tags=["AI模型配置"])
app.include_router(events.router,       prefix="/api/v1/events",       tags=["SSE推送"])
app.include_router(guide.router,        prefix="/api/v1/guide",        tags=["检查引导"])
app.include_router(geocode.router,     prefix="/api/v1/utils",        tags=["工具"])
app.include_router(ai_metrics.router,  prefix="/api/v1/ai-metrics",   tags=["AI效果评估"])
app.include_router(backup.router,      prefix="/api/v1/backup",       tags=["数据备份"])

# ==================== 自动备份调度器 ====================
from api.backup import start_backup_scheduler
start_backup_scheduler()


# ==================== 健康检查 ====================
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"欢迎使用{settings.APP_NAME}",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """健康检查（供负载均衡器和监控探活使用）"""
    try:
        from database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
        )


def _recover_progress_from_db():
    """
    启动时从数据库恢复未完成的后台任务进度到内存。
    处理服务器重启后内存丢失的场景。
    """
    from database import SessionLocal
    try:
        from core.progress_store import progress_store

        # 1. 恢复评分进度
        from core.scoring_tracker import scoring_tracker
        scoring_items = progress_store.recover_in_progress("scoring")
        for item in scoring_items:
            task_id = item["ref_id"]
            detail = item.get("detail", {})
            modules = detail.get("modules", {})
            # 检查是否已实际完成（评分结果已保存到 scoring_results 表）
            db_check = SessionLocal()
            try:
                from models.models import ScoringResult, InspectionRecord
                completed_records = db_check.query(InspectionRecord).filter(
                    InspectionRecord.task_id == task_id,
                    InspectionRecord.status == "completed"
                ).all()
                if completed_records:
                    record_ids = [r.record_id for r in completed_records]
                    scored_count = db_check.query(ScoringResult).filter(
                        ScoringResult.record_id.in_(record_ids)
                    ).count()
                    if scored_count > 0:
                        # 已有评分结果，标记为完成
                        progress_store.update("scoring", task_id, "completed")
                        for mn in modules:
                            scoring_tracker.set_module_status(task_id, mn, "completed")
                        continue
            finally:
                db_check.close()

            # 未完成的评分进度恢复到内存
            for mn, minfo in modules.items():
                if isinstance(minfo, dict):
                    scoring_tracker.set_module_status(task_id, mn, minfo.get("status", "failed"), minfo.get("error"))
                else:
                    scoring_tracker.set_module_status(task_id, mn, str(minfo))
        if scoring_items:
            logger.info(f"[Startup Recovery] 恢复 {len(scoring_items)} 个评分进度")

        # 2. 恢复报告进度
        from api.report import report_progress
        report_items = progress_store.recover_in_progress("report")
        for item in report_items:
            task_id = item["ref_id"]
            detail = item.get("detail", {})
            # 检查报告是否已实际生成
            db_check = SessionLocal()
            try:
                from models.models import Report
                existing = db_check.query(Report).filter(Report.task_id == task_id).first()
                if existing:
                    progress_store.update("report", task_id, "completed")
                    report_progress[task_id] = {"status": "completed"}
                    continue
            finally:
                db_check.close()
            # 标记为失败（服务器重启中断了生成过程）
            report_progress[task_id] = {
                "status": "failed",
                "error": "服务器重启导致报告生成中断，请重新生成",
                "current_step": detail.get("current_step", ""),
                "modules_done": detail.get("modules_done", 0),
                "modules_total": detail.get("modules_total", 0),
            }
            progress_store.update("report", task_id, "failed", detail, "服务器重启中断")
        if report_items:
            logger.info(f"[Startup Recovery] 恢复 {len(report_items)} 个报告进度")

        # 3. 恢复分析进度
        from api.analysis import analysis_progress
        analysis_items = progress_store.recover_in_progress("analysis")
        for item in analysis_items:
            analysis_id = item["ref_id"]
            detail = item.get("detail", {})
            # 检查分析是否已实际完成
            db_check = SessionLocal()
            try:
                from models.models import AnalysisRecord
                record = db_check.query(AnalysisRecord).filter(
                    AnalysisRecord.analysis_id == analysis_id
                ).first()
                if record and record.result_json:
                    progress_store.update("analysis", analysis_id, "completed")
                    analysis_progress[analysis_id] = {"status": "completed", "progress_pct": 100, "current_step": "completed", "error": None}
                    continue
            finally:
                db_check.close()
            # 标记为失败
            analysis_progress[analysis_id] = {
                "status": "failed",
                "error": "服务器重启导致分析中断，请重新开始",
                "current_step": detail.get("current_step", ""),
                "progress_pct": detail.get("progress_pct", 0),
            }
            progress_store.update("analysis", analysis_id, "failed", detail, "服务器重启中断")
        if analysis_items:
            logger.info(f"[Startup Recovery] 恢复 {len(analysis_items)} 个分析进度")

        # 清理旧的已完成记录
        progress_store.cleanup_completed()

    except Exception as e:
        logger.error(f"[Startup Recovery] 进度恢复失败: {e}")
# 运行命令：uvicorn main:app --reload --port 8000
# API 文档：http://localhost:8000/docs
