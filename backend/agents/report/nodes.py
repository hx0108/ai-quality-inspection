"""
Report Agent 节点函数
Agent 3 LangGraph Nodes

工作流: collect_data → fan-out(analyze_module × N) → fan-in → generate_report → export_files → save_report
"""
import json
import uuid as _uuid
from datetime import datetime

from database import SessionLocal
from models.models import InspectionTask, InspectionRecord, Issue, ScoringResult, Report
from config import settings
from core.llm_client import DeepSeekClient
from api.report import generate_word_report, generate_pdf_report, report_progress, _persist_report_progress

from core.logger import get_logger
logger = get_logger("report_agent")


async def collect_data(state: dict) -> dict:
    """
    节点1: 数据收集
    从 DB 查询评分结果、问题列表，计算模块得分和项目总分
    """
    task_id = state["task_id"]
    logger.info(f"collect_data: {task_id}")

    # 更新进度
    if task_id in report_progress:
        report_progress[task_id]["current_step"] = "collecting_data"

    db = SessionLocal()
    try:
        task = db.query(InspectionTask).filter(InspectionTask.task_id == task_id).first()
        if not task:
            return {"errors": ["任务不存在"]}

        # 获取评分结果
        results = db.query(ScoringResult).join(
            InspectionRecord, ScoringResult.record_id == InspectionRecord.record_id
        ).filter(InspectionRecord.task_id == task_id).all()

        if not results:
            return {"errors": ["无评分数据"]}

        # 按模块分组
        modules_data = {}
        for r in results:
            if r.module_name not in modules_data:
                modules_data[r.module_name] = {
                    "items": [],
                    "raw_score_sum": 0,
                    "weight_sum": 0,
                    "issue_count": 0
                }
            modules_data[r.module_name]["items"].append({
                "item_id": r.item_id,
                "item_name": r.item_name,
                "score": float(r.score),
                "weight": float(r.weight),
                "weighted_score": float(r.weighted_score),
                "scoring_basis": r.scoring_basis,
                "improvement_suggestion": r.improvement_suggestion
            })
            modules_data[r.module_name]["raw_score_sum"] += float(r.weighted_score)
            modules_data[r.module_name]["weight_sum"] += float(r.weight)

        # 获取问题统计
        issues = db.query(Issue).join(
            InspectionRecord, Issue.record_id == InspectionRecord.record_id
        ).filter(InspectionRecord.task_id == task_id).all()

        issues_by_severity = {"严重": [], "一般": [], "轻微": []}
        for issue in issues:
            if issue.severity in issues_by_severity:
                issues_by_severity[issue.severity].append({
                    "issue_id": issue.issue_id,
                    "module_name": issue.module_name,
                    "item_id": issue.item_id,
                    "item_name": issue.item_name,
                    "description": issue.description,
                    "location": issue.location
                })
            if issue.module_name not in modules_data:
                modules_data[issue.module_name] = {
                    "items": [], "raw_score_sum": 0, "weight_sum": 0, "issue_count": 0
                }
            modules_data[issue.module_name]["issue_count"] += 1

        # 计算模块得分
        module_scores = []
        project_total = 0
        for module_name in settings.MODULE_WEIGHTS.keys():
            data = modules_data.get(module_name)
            if not data:
                module_scores.append({
                    "module_name": module_name,
                    "module_pct_score": 0,
                    "weight_ratio": settings.MODULE_WEIGHTS[module_name],
                    "weighted_contribution": 0,
                    "item_count": 0,
                    "issue_count": 0
                })
                continue

            raw_sum = data["raw_score_sum"]
            weight_sum = data["weight_sum"]
            max_score = 5 * weight_sum
            module_pct = (raw_sum / max_score * 100) if max_score > 0 else 0
            contribution = module_pct * settings.MODULE_WEIGHTS[module_name]
            project_total += contribution

            module_scores.append({
                "module_name": module_name,
                "module_pct_score": round(module_pct, 2),
                "weight_ratio": settings.MODULE_WEIGHTS[module_name],
                "weighted_contribution": round(contribution, 2),
                "item_count": len(data["items"]),
                "issue_count": data["issue_count"]
            })

        scored_count = len([m for m in module_scores if m["module_pct_score"] > 0])
        # 更新进度中的模块数
        if task_id in report_progress:
            report_progress[task_id]["modules_total"] = scored_count

        logger.info(f"collect_data 完成: {len(module_scores)} 个模块, 总分 {project_total:.2f}")

        return {
            "project_name": task.project.name if task.project else "",
            "check_date": task.check_date,
            "standard_type": task.standard_type or "diecheng",
            "total_score": round(project_total, 2),
            "module_scores": module_scores,
            "modules_data": modules_data,
            "issues_by_severity": issues_by_severity,
            "issue_summary": {
                "serious_count": len(issues_by_severity["严重"]),
                "general_count": len(issues_by_severity["一般"]),
                "minor_count": len(issues_by_severity["轻微"]),
                "total_count": len(issues)
            },
            "modules_total": scored_count,
            "modules_done": 0,
            "module_analyses": [],  # 初始化空列表
        }

    except Exception as e:
        logger.error(f"collect_data 失败: {e}")
        return {"errors": [str(e)]}
    finally:
        db.close()


async def analyze_module(state: dict) -> dict:
    """
    节点2: 单模块分析（并行执行）
    通过 Send 传入单个模块的数据
    """
    module_name = state["module_name"]
    module_pct_score = state["module_pct_score"]
    items_summary = state["items_summary"]
    task_id = state["task_id"]

    logger.info(f"analyze_module: {module_name} ({module_pct_score:.2f}分)")

    # 更新进度
    if task_id in report_progress:
        report_progress[task_id]["current_step"] = f"analyzing:{module_name}"

    if not settings.DEEPSEEK_API_KEY:
        result = {
            "module_name": module_name,
            "module_pct_score": module_pct_score,
            "overall_evaluation": "未配置 DEEPSEEK_API_KEY",
            "main_issues": [],
            "improvement_suggestions": []
        }
        return {
            "module_analyses": [result],
        }

    try:
        deepseek = DeepSeekClient()
        analysis = await deepseek.analyze_module(
            module_name, module_pct_score, items_summary
        )
        result = {
            "module_name": module_name,
            "module_pct_score": module_pct_score,
            "overall_evaluation": analysis.get("overall_evaluation", ""),
            "main_issues": analysis.get("main_issues", []),
            "improvement_suggestions": analysis.get("improvement_suggestions", [])
        }
        logger.info(f"模块分析完成: {module_name}")
    except Exception as e:
        logger.error(f"模块分析失败 {module_name}: {e}")
        result = {
            "module_name": module_name,
            "module_pct_score": module_pct_score,
            "overall_evaluation": f"分析失败: {str(e)}",
            "main_issues": [],
            "improvement_suggestions": []
        }

    # 更新 modules_done 进度（持久化到DB，让前端轮询能实时看到）
    if task_id in report_progress:
        report_progress[task_id]["modules_done"] = report_progress[task_id].get("modules_done", 0) + 1
        report_progress[task_id]["current_step"] = f"analyzing:{module_name}"
        _persist_report_progress(task_id)

    return {
        "module_analyses": [result],
    }


async def generate_report_node(state: dict) -> dict:
    """
    节点3: 生成综合报告
    汇总所有模块分析，调用 DeepSeek 生成综合报告
    """
    task_id = state["task_id"]
    module_analyses = state.get("module_analyses", [])
    total_score = state.get("total_score", 0)

    logger.info(f"generate_report: 汇总 {len(module_analyses)} 个模块分析")

    if task_id in report_progress:
        report_progress[task_id]["current_step"] = "generating_report"

    # SSE 事件：报告生成中
    try:
        from core.event_bus import event_bus
        await event_bus.publish(f"task:{task_id}", {
            "type": "report_progress",
            "status": "generating",
            "step": "generate_report",
        })
    except Exception:
        pass

    if not settings.DEEPSEEK_API_KEY:
        return {
            "ai_full_report": "未配置 DEEPSEEK_API_KEY，无法生成AI分析报告",
            "current_step": "exporting_files"
        }

    try:
        deepseek = DeepSeekClient()
        module_summaries = []
        for ma in module_analyses:
            module_summaries.append({
                "module_name": ma["module_name"],
                "score": ma["module_pct_score"],
                "overall_evaluation": ma.get("overall_evaluation", ""),
                "main_issues": ma.get("main_issues", []),
                "improvement_suggestions": ma.get("improvement_suggestions", [])
            })

        project_name = state.get("project_name", "")
        check_date = state.get("check_date", "")
        ai_full_report = await deepseek.generate_report(
            project_name, check_date, module_summaries, total_score
        )
        logger.info("综合报告生成完成")
        return {
            "ai_full_report": ai_full_report,
            "current_step": "exporting_files"
        }
    except Exception as e:
        logger.error(f"综合报告生成失败: {e}")
        return {
            "ai_full_report": f"综合报告生成失败: {str(e)}",
            "current_step": "exporting_files"
        }


def export_files(state: dict) -> dict:
    """
    节点4: 导出 Word + PDF 文件
    """
    task_id = state["task_id"]
    logger.info(f"export_files: {task_id}")

    if task_id in report_progress:
        report_progress[task_id]["current_step"] = "exporting_files"

    # 构建报告内容 dict
    module_analyses = state.get("module_analyses", [])
    report_content = {
        "task_id": task_id,
        "project_name": state.get("project_name", ""),
        "check_date": state.get("check_date", ""),
        "generated_at": datetime.now().isoformat(),
        "total_score": state.get("total_score", 0),
        "modules": state.get("module_scores", []),
        "issues": state.get("issues_by_severity", {}),
        "issue_summary": state.get("issue_summary", {}),
        "module_analyses": module_analyses,
        "ai_full_report": state.get("ai_full_report", ""),
        "scoring_method": "Qwen-plus AI评分",
        "analysis_method": "DeepSeek-V3.2 AI分析"
    }

    # 生成报告 ID（与任务ID共享日期和随机编码，仅前缀不同）
    today = datetime.now().strftime("%Y%m%d")
    suffix = task_id.split("-", 2)[-1] if "-" in task_id else _uuid.uuid4().hex[:8]
    report_id = f"R-{today}-{suffix}"

    # 生成 Word
    settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    word_path = str(settings.REPORTS_DIR / f"{report_id}.docx")
    word_success = False
    try:
        generate_word_report(report_content, word_path)
        word_success = True
        logger.info(f"Word报告已生成: {word_path}")
    except Exception as e:
        logger.error(f"Word报告生成失败: {e}", exc_info=True)

    # 生成 PDF
    pdf_path = str(settings.REPORTS_DIR / f"{report_id}.pdf")
    pdf_success = False
    try:
        generate_pdf_report(report_content, pdf_path)
        pdf_success = True
        logger.info("PDF生成完成")
    except Exception as e:
        logger.warning(f"PDF生成失败: {e}", exc_info=True)
        pdf_path = None

    if not word_success and not pdf_success:
        return {"errors": state.get("errors", []) + ["报告文件导出失败"]}

    logger.info(f"文件导出完成: {report_id}")

    return {
        "report_id": report_id,
        "word_path": word_path if word_success else "",
        "pdf_path": pdf_path or "",
        "current_step": "saving_report"
    }


async def save_report(state: dict) -> dict:
    """
    节点5: 保存报告记录到数据库
    """
    task_id = state["task_id"]
    report_id = state.get("report_id", "")
    logger.info(f"save_report: {report_id}")

    db = SessionLocal()
    try:
        task = db.query(InspectionTask).filter(InspectionTask.task_id == task_id).first()
        if not task:
            return {"errors": [f"任务不存在: {task_id}"]}

        # 构建完整报告内容
        module_analyses = state.get("module_analyses", [])
        report_content = {
            "task_id": task_id,
            "project_name": state.get("project_name", ""),
            "check_date": state.get("check_date", ""),
            "generated_at": datetime.now().isoformat(),
            "total_score": state.get("total_score", 0),
            "modules": state.get("module_scores", []),
            "issues": state.get("issues_by_severity", {}),
            "issue_summary": state.get("issue_summary", {}),
            "module_analyses": module_analyses,
            "ai_full_report": state.get("ai_full_report", ""),
            "scoring_method": "Qwen-plus AI评分",
            "analysis_method": "DeepSeek-V3.2 AI分析"
        }

        # 计算版本号：该任务的最新版本 + 1
        latest_version = db.query(Report).filter(
            Report.task_id == task_id
        ).order_by(Report.version.desc()).first()
        next_version = (latest_version.version + 1) if latest_version else 1

        report_record = Report(
            report_id=report_id,
            task_id=task_id,
            project_id=task.project_id,
            report_type="full",
            version=next_version,
            total_score=report_content["total_score"],
            content_json=json.dumps(report_content, ensure_ascii=False),
            file_path=state.get("word_path", "")
        )
        db.add(report_record)
        db.commit()
        logger.info(f"报告已保存: {report_id}, 版本 v{next_version}")

        # SSE 事件：报告完成
        try:
            from core.event_bus import event_bus
            await event_bus.publish(f"task:{task_id}", {
                "type": "report_progress",
                "status": "completed",
                "report_id": report_id,
            })
        except Exception:
            pass

        return {"current_step": "completed"}

    except Exception as e:
        logger.error(f"save_report 失败: {e}")
        return {"errors": [str(e)]}
    finally:
        db.close()
