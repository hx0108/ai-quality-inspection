"""
综合分析 Agent 节点函数
10个节点：validate_input, collect_reports, analyze_score, analyze_issue, analyze_module,
generate_insight, render_charts, assemble_report, export_files, save_result
"""
import json
import os
import re
import uuid
from datetime import datetime
from typing import Dict, Any, List

from database import SessionLocal
from models.models import (
    Report, InspectionTask, Project, AnalysisRecord, AnalysisProject
)
from config import settings
from core.llm_client import DeepSeekClient

from core.logger import get_logger
logger = get_logger("analysis_agent")


def _get_grade(score: float) -> str:
    """根据分数计算评级"""
    if score >= 99.5:
        return "A+"
    elif score >= 97.0:
        return "A"
    elif score >= 95.0:
        return "A-"
    elif score >= 90.0:
        return "B+"
    elif score >= 80.0:
        return "B"
    else:
        return "C"


# ==================== 节点1: 验证输入 ====================
async def validate_input(state: dict) -> dict:
    """验证输入参数"""
    mode = state.get("mode", "")

    if mode not in ("cross_project", "cross_time", "all_projects"):
        return {"valid": False, "error_message": f"不支持的模式: {mode}"}

    if mode == "cross_project":
        ra = state.get("report_a_id")
        rb = state.get("report_b_id")
        if not ra or not rb:
            return {"valid": False, "error_message": "跨项目对比需要选择两个报告"}
        if ra == rb:
            return {"valid": False, "error_message": "请选择两个不同的报告"}

    elif mode == "cross_time":
        pid = state.get("project_a_id")
        if not pid:
            return {"valid": False, "error_message": "跨时段对比需要选择一个项目"}

    elif mode == "all_projects":
        if not state.get("time_range_start") or not state.get("time_range_end"):
            return {"valid": False, "error_message": "全项目概览需要指定时间范围"}

    logger.info(f"输入验证通过, mode={mode}")
    return {"valid": True, "current_step": "validate_input", "progress_pct": 5}


# ==================== 节点2: 收集报告数据 ====================
async def collect_reports(state: dict) -> dict:
    """从数据库收集报告数据"""
    mode = state.get("mode")
    db = SessionLocal()
    reports_data = []
    projects_info = []
    label_a = "对象A"
    label_b = "对象B"

    try:
        if mode == "cross_project":
            # 按报告ID精确选择
            for rid, idx in [(state.get("report_a_id"), 0), (state.get("report_b_id"), 1)]:
                report = db.query(Report).filter(Report.report_id == rid).first()
                if not report or not report.content_json:
                    return {"valid": False, "error_message": f"报告 {rid} 不存在或无内容"}

                project = db.query(Project).filter(Project.id == report.project_id).first()
                content = json.loads(report.content_json) if isinstance(report.content_json, str) else report.content_json
                reports_data.append(content)
                projects_info.append({
                    "project_id": report.project_id,
                    "project_name": project.name if project else content.get("project_name", "未知"),
                    "report_id": report.report_id,
                    "check_date": content.get("check_date", ""),
                    "total_score": float(report.total_score or 0)
                })

            label_a = f"{projects_info[0]['project_name']} ({projects_info[0]['check_date']})"
            label_b = f"{projects_info[1]['project_name']} ({projects_info[1]['check_date']})"

        elif mode == "cross_time":
            pid = state.get("project_a_id")
            project = db.query(Project).filter(Project.id == pid).first()
            if not project:
                return {"valid": False, "error_message": "项目不存在"}

            # 查找该项目所有报告，关联任务获取 check_date
            report_a_id = state.get("report_a_id")
            report_b_id = state.get("report_b_id")

            if report_a_id and report_b_id:
                # 精确指定报告
                for rid, idx in [(report_a_id, 0), (report_b_id, 1)]:
                    report = db.query(Report).filter(Report.report_id == rid).first()
                    if not report or not report.content_json:
                        return {"valid": False, "error_message": f"报告 {rid} 不存在或无内容"}
                    content = json.loads(report.content_json) if isinstance(report.content_json, str) else report.content_json
                    reports_data.append(content)
                    projects_info.append({
                        "project_id": pid,
                        "project_name": project.name,
                        "report_id": report.report_id,
                        "check_date": content.get("check_date", ""),
                        "total_score": float(report.total_score or 0)
                    })
            else:
                # 按时间范围取最新
                start = state.get("time_range_start", "")
                end = state.get("time_range_end", "")
                all_reports = db.query(Report).filter(
                    Report.project_id == pid
                ).order_by(Report.generated_at.desc()).all()

                if len(all_reports) < 2:
                    return {"valid": False, "error_message": f"项目 '{project.name}' 至少需要2份报告才能进行跨时段对比"}

                # 取最早和最新的
                for report in [all_reports[-1], all_reports[0]]:
                    content = json.loads(report.content_json) if isinstance(report.content_json, str) else report.content_json
                    reports_data.append(content)
                    projects_info.append({
                        "project_id": pid,
                        "project_name": project.name,
                        "report_id": report.report_id,
                        "check_date": content.get("check_date", ""),
                        "total_score": float(report.total_score or 0)
                    })

            label_a = f"{projects_info[0]['project_name']} T1 ({projects_info[0]['check_date']})"
            label_b = f"{projects_info[1]['project_name']} T2 ({projects_info[1]['check_date']})"

        elif mode == "all_projects":
            start = state.get("time_range_start", "2000-01-01")
            end = state.get("time_range_end", "2099-12-31")

            # 查找时间范围内有报告的项目
            tasks_in_range = db.query(InspectionTask).filter(
                InspectionTask.check_date >= start,
                InspectionTask.check_date <= end,
                InspectionTask.status == "completed"
            ).all()

            task_ids = [t.task_id for t in tasks_in_range]
            reports = db.query(Report).filter(
                Report.task_id.in_(task_ids)
            ).all()

            if len(reports) < 2:
                return {"valid": False, "error_message": f"当前时间范围内仅有 {len(reports)} 个项目有报告，至少需要 2 个"}

            if len(reports) > 20:
                return {"valid": False, "error_message": f"匹配到 {len(reports)} 个项目，超过上限 20，请缩小时间范围"}

            for report in reports:
                if not report.content_json:
                    continue
                content = json.loads(report.content_json) if isinstance(report.content_json, str) else report.content_json
                project = db.query(Project).filter(Project.id == report.project_id).first()
                reports_data.append(content)
                projects_info.append({
                    "project_id": report.project_id,
                    "project_name": content.get("project_name", project.name if project else "未知"),
                    "report_id": report.report_id,
                    "check_date": content.get("check_date", ""),
                    "total_score": float(report.total_score or 0)
                })

            # 按总分降序排列
            projects_info.sort(key=lambda x: x["total_score"], reverse=True)
            reports_data_sorted = []
            for pi in projects_info:
                for rd in reports_data:
                    if rd.get("task_id") == pi.get("report_id") or rd.get("project_name") == pi.get("project_name"):
                        reports_data_sorted.append(rd)
                        break
            reports_data = reports_data_sorted if reports_data_sorted else reports_data

            label_a = f"全项目概览 ({start} ~ {end})"
            label_b = f"共 {len(projects_info)} 个项目"

        logger.info(f"收集到 {len(reports_data)} 份报告数据")
        return {
            "reports_data": reports_data,
            "projects_info": projects_info,
            "label_a": label_a,
            "label_b": label_b,
            "current_step": "collect_reports",
            "progress_pct": 15
        }

    except Exception as e:
        logger.error(f"收集报告失败: {e}")
        return {"valid": False, "error_message": str(e), "errors": [str(e)]}
    finally:
        db.close()


# ==================== 节点3: 维度一 综合得分分析 ====================
async def analyze_score(state: dict) -> dict:
    """综合得分对比分析（纯计算）"""
    reports_data = state.get("reports_data", [])
    mode = state.get("mode", "cross_project")
    module_weights = settings.MODULE_WEIGHTS

    comparison_matrix = []

    if mode == "all_projects":
        # 模式三：排行榜
        projects_info = state.get("projects_info", [])
        for pi in projects_info:
            pi["grade"] = _get_grade(pi["total_score"])

        # 统计摘要
        scores = [p["total_score"] for p in projects_info]
        score_analysis = {
            "ranking": projects_info,
            "statistics": {
                "mean": round(sum(scores) / len(scores), 2) if scores else 0,
                "max": round(max(scores), 2) if scores else 0,
                "min": round(min(scores), 2) if scores else 0,
                "range": round(max(scores) - min(scores), 2) if scores else 0,
                "count": len(scores)
            }
        }
    else:
        # 模式一/二：两方对比
        rd_a = reports_data[0] if len(reports_data) > 0 else {}
        rd_b = reports_data[1] if len(reports_data) > 1 else {}
        score_a = float(rd_a.get("total_score", 0))
        score_b = float(rd_b.get("total_score", 0))

        # 构建模块对比矩阵
        modules_a = {m["module_name"]: m for m in rd_a.get("modules", [])}
        modules_b = {m["module_name"]: m for m in rd_b.get("modules", [])}

        for mname, weight in module_weights.items():
            ma = modules_a.get(mname, {})
            mb = modules_b.get(mname, {})
            sa = float(ma.get("module_pct_score", 0))
            sb = float(mb.get("module_pct_score", 0))
            diff = round(sa - sb, 2)

            comparison_matrix.append({
                "module_name": mname,
                "weight": weight,
                "score_a": sa,
                "score_b": sb,
                "diff": diff,
                "winner": "A" if diff > 0.2 else ("B" if diff < -0.2 else "持平")
            })

        score_analysis = {
            "total_score_a": score_a,
            "total_score_b": score_b,
            "diff": round(score_a - score_b, 2),
            "winner": "A" if score_a > score_b else ("B" if score_b > score_a else "持平"),
            "grade_a": _get_grade(score_a),
            "grade_b": _get_grade(score_b)
        }

    logger.info("得分分析完成")
    return {
        "comparison_matrix": comparison_matrix,
        "score_analysis": score_analysis,
    }


# ==================== 节点4: 维度二 问题分布分析 ====================
async def analyze_issue(state: dict) -> dict:
    """问题分布对比分析"""
    reports_data = state.get("reports_data", [])
    mode = state.get("mode", "cross_project")

    if mode == "all_projects":
        # 模式三：统计全局共性问题
        all_issues = []
        for rd in reports_data:
            issues = rd.get("issues", {})
            for severity, items in issues.items():
                for item in items:
                    all_issues.append({**item, "severity": severity})

        # 按描述统计频次
        issue_freq = {}
        for iss in all_issues:
            key = iss.get("description", "")[:50]
            if key:
                issue_freq[key] = issue_freq.get(key, 0) + 1

        top_issues = sorted(issue_freq.items(), key=lambda x: -x[1])[:5]
        issue_analysis = {
            "top_common_issues": [{"description": k, "count": v} for k, v in top_issues],
            "total_issues": len(all_issues),
            "by_severity": {
                "严重": sum(1 for i in all_issues if i.get("severity") == "严重"),
                "一般": sum(1 for i in all_issues if i.get("severity") == "一般"),
                "轻微": sum(1 for i in all_issues if i.get("severity") == "轻微")
            }
        }
    else:
        # 模式一/二
        rd_a = reports_data[0] if len(reports_data) > 0 else {}
        rd_b = reports_data[1] if len(reports_data) > 1 else {}
        issues_a = rd_a.get("issue_summary", {})
        issues_b = rd_b.get("issue_summary", {})

        issue_list_a = []
        issue_list_b = []
        for sev in ["严重", "一般", "轻微"]:
            issue_list_a.extend(rd_a.get("issues", {}).get(sev, []))
            issue_list_b.extend(rd_b.get("issues", {}).get(sev, []))

        # 模式二：问题追踪
        problem_tracking = None
        if mode == "cross_time":
            desc_a = {i.get("description", "") for i in issue_list_a}
            desc_b = {i.get("description", "") for i in issue_list_b}
            resolved = desc_a - desc_b
            new = desc_b - desc_a
            persistent = desc_a & desc_b
            problem_tracking = {
                "resolved": list(resolved),
                "new": list(new),
                "persistent": list(persistent)
            }

        issue_analysis = {
            "summary_a": issues_a,
            "summary_b": issues_b,
            "total_a": sum(issues_a.values()) if isinstance(issues_a, dict) else 0,
            "total_b": sum(issues_b.values()) if isinstance(issues_b, dict) else 0,
            "problem_tracking": problem_tracking
        }

    logger.info("问题分析完成")
    return {"issue_analysis": issue_analysis}


# ==================== 节点5: 维度三 8模块逐一分析 ====================
async def analyze_module(state: dict) -> dict:
    """8模块逐一对比分析"""
    reports_data = state.get("reports_data", [])
    mode = state.get("mode", "mode")
    module_weights = settings.MODULE_WEIGHTS

    module_analysis = {"modules": []}

    if mode == "all_projects":
        # 模式三：每模块统计各项目得分
        for mname in module_weights:
            scores = []
            for rd in reports_data:
                for m in rd.get("modules", []):
                    if m.get("module_name") == mname:
                        scores.append(float(m.get("module_pct_score", 0)))
            module_analysis["modules"].append({
                "module_name": mname,
                "weight": module_weights[mname],
                "scores": scores,
                "avg": round(sum(scores) / len(scores), 2) if scores else 0,
                "max": round(max(scores), 2) if scores else 0,
                "min": round(min(scores), 2) if scores else 0
            })
    else:
        # 模式一/二
        rd_a = reports_data[0] if len(reports_data) > 0 else {}
        rd_b = reports_data[1] if len(reports_data) > 1 else {}
        analyses_a = {m["module_name"]: m for m in rd_a.get("module_analyses", [])}
        analyses_b = {m["module_name"]: m for m in rd_b.get("module_analyses", [])}
        modules_a = {m["module_name"]: m for m in rd_a.get("modules", [])}
        modules_b = {m["module_name"]: m for m in rd_b.get("modules", [])}

        for mname, weight in module_weights.items():
            ma = modules_a.get(mname, {})
            mb = modules_b.get(mname, {})
            aa = analyses_a.get(mname, {})
            ab = analyses_b.get(mname, {})
            sa = float(ma.get("module_pct_score", 0))
            sb = float(mb.get("module_pct_score", 0))
            diff = round(sa - sb, 2)

            module_analysis["modules"].append({
                "module_name": mname,
                "weight": weight,
                "score_a": sa,
                "score_b": sb,
                "diff": diff,
                "trend": "↑" if diff > 0.2 else ("↓" if diff < -0.2 else "→"),
                "winner": "A" if diff > 0.2 else ("B" if diff < -0.2 else "持平"),
                "analysis_a": aa.get("overall_evaluation", ""),
                "analysis_b": ab.get("overall_evaluation", ""),
                "issues_a": aa.get("main_issues", []),
                "issues_b": ab.get("main_issues", [])
            })

    logger.info("模块分析完成")
    return {"module_analysis": module_analysis}


# ==================== 节点6: LLM 生成洞察 ====================
async def generate_insight(state: dict) -> dict:
    """调用 DeepSeek 生成智能洞察和建议"""
    client = DeepSeekClient()
    mode = state.get("mode", "cross_project")
    reports_data = state.get("reports_data", [])
    label_a = state.get("label_a", "对象A")
    label_b = state.get("label_b", "对象B")
    comparison_matrix = state.get("comparison_matrix", [])
    score_analysis = state.get("score_analysis", {})
    issue_analysis = state.get("issue_analysis", {})
    module_analysis = state.get("module_analysis", {})
    projects_info = state.get("projects_info", [])

    # 构建传给 LLM 的数据
    if mode == "all_projects":
        summary_a = {"total_score": score_analysis.get("statistics", {}).get("mean", 0)}
        summary_b = {"total_score": 0}
        matrix_for_llm = comparison_matrix if comparison_matrix else []
    else:
        summary_a = {
            "total_score": score_analysis.get("total_score_a", 0),
            "serious_count": issue_analysis.get("summary_a", {}).get("serious_count", 0),
            "general_count": issue_analysis.get("summary_a", {}).get("general_count", 0),
            "minor_count": issue_analysis.get("summary_a", {}).get("minor_count", 0),
        }
        summary_b = {
            "total_score": score_analysis.get("total_score_b", 0),
            "serious_count": issue_analysis.get("summary_b", {}).get("serious_count", 0),
            "general_count": issue_analysis.get("summary_b", {}).get("general_count", 0),
            "minor_count": issue_analysis.get("summary_b", {}).get("minor_count", 0),
        }
        matrix_for_llm = comparison_matrix

    comparison_data = {
        "mode": mode,
        "label_a": label_a,
        "label_b": label_b,
        "comparison_matrix": matrix_for_llm,
        "summary_a": summary_a,
        "summary_b": summary_b,
        "module_analyses": module_analysis.get("modules", [])[:8]
    }

    # 调用 LLM
    logger.info("正在调用 DeepSeek-V3.2 生成洞察...")
    ai_result = await client.compare_reports(comparison_data)

    executive_summary = ai_result.get("executive_summary", "分析完成")
    action_items = ai_result.get("action_items", [])

    # 将分析洞察写入长记忆（Agent-Curated Memory）
    try:
        from core.long_memory import LongMemory, MemoryType
        for pi in projects_info:
            pid = pi.get("project_id")
            if pid and executive_summary:
                LongMemory.add_memory(
                    project_id=pid,
                    memory_type=MemoryType.INSIGHT,
                    content={
                        "executive_summary": executive_summary[:200],
                        "mode": mode,
                        "label_a": label_a,
                        "label_b": label_b,
                    },
                    summary=f"[{mode}] {executive_summary[:80]}",
                    confidence=0.7,
                )
        logger.info("分析洞察已写入长记忆")
    except Exception as e:
        logger.warning(f"写入洞察失败(不影响主流程): {e}")

    logger.info("LLM 洞察生成完成")
    return {
        "ai_result": ai_result,
        "executive_summary": executive_summary,
        "action_items": action_items,
        "current_step": "generate_insight",
        "progress_pct": 65
    }


# ==================== 节点7: 图表数据 ====================
async def render_charts(state: dict) -> dict:
    """生成 ECharts 配置 JSON"""
    mode = state.get("mode", "cross_project")
    comparison_matrix = state.get("comparison_matrix", [])
    module_analysis = state.get("module_analysis", {})
    score_analysis = state.get("score_analysis", {})
    label_a = state.get("label_a", "对象A")
    label_b = state.get("label_b", "对象B")
    projects_info = state.get("projects_info", [])

    chart_data = {}

    if mode != "all_projects":
        # 柱状图：8模块得分对比
        categories = [m.get("module_name", "") for m in comparison_matrix]
        chart_data["bar"] = {
            "title": {"text": "模块得分对比", "left": "center", "textStyle": {"color": "#1a1d26"}},
            "tooltip": {"trigger": "axis"},
            "legend": {"data": [label_a, label_b], "bottom": 0},
            "xAxis": {"type": "category", "data": categories, "axisLabel": {"rotate": 30}},
            "yAxis": {"type": "value", "max": 100, "name": "得分"},
            "series": [
                {"name": label_a, "type": "bar", "data": [round(m.get("score_a", 0), 2) for m in comparison_matrix], "itemStyle": {"color": "#2563eb"}},
                {"name": label_b, "type": "bar", "data": [round(m.get("score_b", 0), 2) for m in comparison_matrix], "itemStyle": {"color": "#8b5cf6"}}
            ]
        }

        # 雷达图
        indicator = [{"name": m.get("module_name", ""), "max": 100} for m in comparison_matrix]
        chart_data["radar"] = {
            "title": {"text": "8维度雷达图", "left": "center", "textStyle": {"color": "#1a1d26"}},
            "tooltip": {},
            "legend": {"data": [label_a, label_b], "bottom": 0},
            "radar": {"indicator": indicator},
            "series": [{
                "type": "radar",
                "data": [
                    {"name": label_a, "value": [round(m.get("score_a", 0), 2) for m in comparison_matrix], "areaStyle": {"opacity": 0.2}},
                    {"name": label_b, "value": [round(m.get("score_b", 0), 2) for m in comparison_matrix], "areaStyle": {"opacity": 0.2}}
                ]
            }]
        }
    else:
        # 模式三：热力图数据
        module_names = list(settings.MODULE_WEIGHTS.keys())
        project_names = [p.get("project_name", "") for p in projects_info]
        heat_data = []
        for pi_idx, pi in enumerate(projects_info):
            rd = state.get("reports_data", [{}])[pi_idx] if pi_idx < len(state.get("reports_data", [])) else {}
            modules = {m["module_name"]: float(m.get("module_pct_score", 0)) for m in rd.get("modules", [])}
            for mi_idx, mname in enumerate(module_names):
                heat_data.append([mi_idx, pi_idx, modules.get(mname, 0)])

        chart_data["heatmap"] = {
            "title": {"text": "项目×模块热力图", "left": "center", "textStyle": {"color": "#1a1d26"}},
            "tooltip": {"position": "top"},
            "xAxis": {"type": "category", "data": module_names, "axisLabel": {"rotate": 30}},
            "yAxis": {"type": "category", "data": project_names},
            "visualMap": {"min": 80, "max": 100, "calculable": True, "orient": "horizontal", "left": "center", "bottom": 0, "inRange": {"color": ["#ef4444", "#f59e0b", "#22c55e"]}},
            "series": [{"type": "heatmap", "data": heat_data, "label": {"show": True}}]
        }

        # 排行柱状图
        chart_data["ranking_bar"] = {
            "title": {"text": "项目总分排行", "left": "center", "textStyle": {"color": "#1a1d26"}},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": project_names, "axisLabel": {"rotate": 30}},
            "yAxis": {"type": "value", "max": 100},
            "series": [{"type": "bar", "data": [round(p.get("total_score", 0), 2) for p in projects_info], "itemStyle": {"color": "#2563eb"}}]
        }

    logger.info("图表数据生成完成")
    return {"chart_data": chart_data, "current_step": "render_charts", "progress_pct": 82}


# ==================== 节点8: 组装报告 ====================
async def assemble_report(state: dict) -> dict:
    """组装完整 Markdown 报告"""
    mode = state.get("mode", "cross_project")
    label_a = state.get("label_a", "对象A")
    label_b = state.get("label_b", "对象B")
    ai_result = state.get("ai_result", {})
    comparison_matrix = state.get("comparison_matrix", [])
    score_analysis = state.get("score_analysis", {})
    issue_analysis = state.get("issue_analysis", {})
    module_analysis = state.get("module_analysis", {})
    projects_info = state.get("projects_info", [])
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 使用 LLM 生成的报告，如果有
    ai_report = ai_result.get("full_report_markdown", "")
    if ai_report:
        final_report_md = f"""# 综合分析报告

> 生成时间: {now}
> 分析模式: {mode}
> 分析对象: {label_a} vs {label_b}
> 分析模型: DeepSeek-V3.2

---

{ai_report}
"""
    else:
        # 从 AI 结构化数据组装报告
        ai = ai_result if isinstance(ai_result, dict) else {}
        final_report_md = f"""# 综合分析报告

> 生成时间: {now}
> 分析模式: {mode}
> 分析对象: {label_a} vs {label_b}
> 分析模型: DeepSeek-V3.2

---

## 执行摘要

{ai.get('executive_summary', '分析完成')}

## 整体评价

{ai.get('overall_verdict', '')}

"""
        sc = ai.get('score_comparison', {})
        if sc:
            final_report_md += f"## 得分对比\n\n胜出方：{sc.get('winner','持平')} | 差值：{sc.get('diff',0):+.2f}\n\n{sc.get('analysis','')}\n\n"

        if ai.get('strengths_a'):
            final_report_md += f"### {label_a} 优势\n"
            for s in ai['strengths_a']:
                final_report_md += f"- {s}\n"
            final_report_md += "\n"

        if ai.get('strengths_b'):
            final_report_md += f"### {label_b} 优势\n"
            for s in ai['strengths_b']:
                final_report_md += f"- {s}\n"
            final_report_md += "\n"

        if ai.get('weaknesses_a'):
            final_report_md += f"### {label_a} 薄弱环节\n"
            for w in ai['weaknesses_a']:
                final_report_md += f"- {w}\n"
            final_report_md += "\n"

        if ai.get('weaknesses_b'):
            final_report_md += f"### {label_b} 薄弱环节\n"
            for w in ai['weaknesses_b']:
                final_report_md += f"- {w}\n"
            final_report_md += "\n"

        if ai.get('key_differences'):
            final_report_md += "## 关键差异\n"
            for d in ai['key_differences']:
                final_report_md += f"- {d}\n"
            final_report_md += "\n"

        if ai.get('common_issues'):
            final_report_md += "## 共性问题\n"
            for c in ai['common_issues']:
                final_report_md += f"- {c}\n"
            final_report_md += "\n"

        if ai.get('action_items'):
            final_report_md += "## 行动建议\n\n| 动作 | 负责人 | 时限 |\n|---|---|---|\n"
            for a in ai['action_items']:
                final_report_md += f"| {a.get('action','')} | {a.get('responsible','')} | {a.get('deadline','')} |\n"
            final_report_md += "\n"

        if ai.get('final_conclusion'):
            final_report_md += f"## 结论\n\n{ai['final_conclusion']}\n"

    logger.info("报告组装完成")
    return {"final_report_md": final_report_md, "current_step": "assemble_report", "progress_pct": 90}


# ==================== 节点9: 导出文件 ====================


def _render_radar_chart(chart_option: dict, title: str, width: int, height: int) -> bytes:
    """使用 matplotlib 渲染高质量雷达图"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    import numpy as np
    import io
    import os

    # 设置中文字体
    font_path = None
    font_candidates = [
        '/app/fonts/chinese_font.otf',
        '/app/fonts/NotoSansSC-Regular.ttf',
        '/usr/share/fonts/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        'C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/msyhbd.ttc',
        'C:/Windows/Fonts/simhei.ttf', 'C:/Windows/Fonts/simsun.ttc',
    ]
    for candidate in font_candidates:
        if os.path.exists(candidate) and os.path.getsize(candidate) > 0:
            font_path = candidate
            break

    if font_path:
        try:
            fm.fontManager.addfont(font_path)
            font_prop = fm.FontProperties(fname=font_path)
            plt.rcParams['font.family'] = font_prop.get_name()
            plt.rcParams['axes.unicode_minus'] = False
        except Exception:
            font_prop = None
    else:
        font_prop = None

    radar_cfg = chart_option.get("radar", {})
    indicators = radar_cfg.get("indicator", [])
    labels = [ind.get("name", "") for ind in indicators]
    n = len(labels)
    if n < 3:
        return b''

    # 角度（从顶部开始，顺时针）
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]  # 闭合

    fig, ax = plt.subplots(figsize=(width / 100, height / 100), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor('white')

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    ax.set_xticks(angles[:-1])
    fp_label = fm.FontProperties(fname=font_path, size=11) if font_path else None
    ax.set_xticklabels(labels, fontproperties=fp_label, color='#374151')

    # 径向刻度
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=8, color='#9ca3af')

    # 网格样式
    ax.spines['polar'].set_color('#d1d5db')
    ax.grid(color='#e5e7eb', linewidth=0.8)

    # 数据系列
    series_list = chart_option.get("series", [])
    radar_series = series_list[0] if series_list else {}
    data_items = radar_series.get("data", [])

    colors = ['#2563eb', '#8b5cf6', '#22c55e']

    for d_idx, item in enumerate(data_items):
        vals = [float(v) for v in item.get("value", [])]
        vals_closed = vals + vals[:1]  # 闭合
        name = item.get("name", f"系列{d_idx + 1}")
        c = colors[d_idx % len(colors)]

        ax.plot(angles, vals_closed, 'o-', linewidth=2, color=c, markersize=5, label=name)
        ax.fill(angles, vals_closed, alpha=0.15, color=c)

        # 数值标注
        for i, v in enumerate(vals):
            angle = angles[i]
            ax.annotate(f'{v:.1f}', xy=(angle, v), fontsize=8, color=c,
                        ha='center', va='bottom',
                        xytext=(0, 8), textcoords='offset points')

    # 标题
    fp_title = fm.FontProperties(fname=font_path, size=16) if font_path else None
    ax.set_title(title, fontproperties=fp_title, color='#1a1d26', pad=20, fontweight='bold')

    # 图例
    fp_legend = fm.FontProperties(fname=font_path, size=10) if font_path else None
    ax.legend(loc='lower right', bbox_to_anchor=(1.15, -0.05), prop=fp_legend,
              frameon=True, fancybox=True, shadow=False)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _render_chart_to_image(chart_option: dict, title: str, width: int = 800, height: int = 500) -> bytes:
    """使用 matplotlib 渲染图表为 PNG（支持柱状图和雷达图）"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    import numpy as np
    import io

    # 设置中文字体
    font_path = None
    font_candidates = [
        '/app/fonts/chinese_font.otf',
        '/app/fonts/NotoSansSC-Regular.ttf',
        '/usr/share/fonts/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        'C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/msyhbd.ttc',
        'C:/Windows/Fonts/simhei.ttf', 'C:/Windows/Fonts/simsun.ttc',
    ]
    for candidate in font_candidates:
        if os.path.exists(candidate) and os.path.getsize(candidate) > 0:
            font_path = candidate
            break

    if font_path:
        try:
            fm.fontManager.addfont(font_path)
            font_prop = fm.FontProperties(fname=font_path)
            plt.rcParams['font.family'] = font_prop.get_name()
            plt.rcParams['axes.unicode_minus'] = False
        except Exception:
            font_prop = None
    else:
        font_prop = None

    fp_label = fm.FontProperties(fname=font_path, size=10) if font_path else None
    fp_title = fm.FontProperties(fname=font_path, size=14) if font_path else None
    fp_legend = fm.FontProperties(fname=font_path, size=9) if font_path else None

    series_list = chart_option.get("series", [])
    categories = chart_option.get("xAxis", {}).get("data", [])

    # ====== 判断图表类型 ======
    is_radar = chart_option.get("radar") is not None or (
        series_list and series_list[0].get("type") == "radar"
    )

    if is_radar:
        return _render_radar_chart(chart_option, title, width, height)

    elif series_list and categories:
        # ====== 柱状图渲染（matplotlib） ======
        fig, ax = plt.subplots(figsize=(width / 100, height / 100))
        fig.patch.set_facecolor('white')

        x = np.arange(len(categories))
        n_series = len(series_list)
        bar_width = 0.35
        colors = ['#2563eb', '#8b5cf6', '#22c55e', '#f59e0b', '#ef4444']

        for s_idx, series in enumerate(series_list):
            data = [float(v) for v in series.get("data", [])]
            name = series.get("name", f"系列{s_idx + 1}")
            color = colors[s_idx % len(colors)]
            offset = (s_idx - n_series / 2 + 0.5) * bar_width
            bars = ax.bar(x + offset, data, bar_width, label=name, color=color, edgecolor='white', linewidth=0.5)
            # 数值标注
            for bar_item, val in zip(bars, data):
                ax.annotate(f'{val:.1f}',
                            xy=(bar_item.get_x() + bar_item.get_width() / 2, val),
                            xytext=(0, 4), textcoords='offset points',
                            ha='center', va='bottom', fontsize=8, color=color,
                            fontproperties=fp_label)

        ax.set_title(title, fontproperties=fp_title, color='#1a1d26', fontweight='bold', pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels(categories, fontproperties=fp_label, color='#374151')
        for label in ax.get_xticklabels():
            label.set_rotation(30)
            label.set_ha('right')
        ax.set_ylim(0, 105)
        ax.set_ylabel('得分', fontproperties=fp_label, color='#6b7280')
        ax.yaxis.set_major_locator(plt.MultipleLocator(20))
        ax.grid(axis='y', alpha=0.3, color='#e5e7eb')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#d1d5db')
        ax.spines['bottom'].set_color('#d1d5db')

        ax.legend(prop=fp_legend, loc='lower right', frameon=True, fancybox=True)

        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()

    # 空图表
    from PIL import Image
    img = Image.new('RGB', (width, height), '#FFFFFF')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def _add_markdown_to_doc(doc, md_text: str):
    """将 Markdown 文本转换为 Word 文档内容（支持表格、列表、标题等）"""
    lines = md_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        # 表格处理
        if line.startswith("| ") and "|" in line[1:]:
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            # 过滤掉分隔行
            data_lines = [l for l in table_lines if not all(c in '|-: ' for c in l)]
            if data_lines:
                # 解析表头和数据
                parsed = []
                for dl in data_lines:
                    cells = [c.strip() for c in dl.strip('|').split('|')]
                    parsed.append(cells)

                if parsed:
                    n_cols = max(len(row) for row in parsed)
                    table = doc.add_table(rows=len(parsed), cols=n_cols, style="Table Grid")
                    for ri, row in enumerate(parsed):
                        for ci, cell in enumerate(row):
                            if ci < n_cols:
                                table.rows[ri].cells[ci].text = cell
                    # 表头加粗
                    for ci in range(n_cols):
                        for paragraph in table.rows[0].cells[ci].paragraphs:
                            for run in paragraph.runs:
                                run.bold = True
            continue

        if line.startswith("# "):
            doc.add_heading(line[2:], level=1)
        elif line.startswith("## "):
            doc.add_heading(line[3:], level=2)
        elif line.startswith("### "):
            doc.add_heading(line[4:], level=3)
        elif line.startswith("#### "):
            doc.add_heading(line[5:], level=4)
        elif line.startswith("> "):
            p = doc.add_paragraph(line[2:])
            try:
                p.style = doc.styles["Intense Quote"]
            except KeyError:
                for run in p.runs:
                    run.italic = True
        elif line.startswith("- ") or line.startswith("* "):
            doc.add_paragraph(line[2:], style="List Bullet")
        elif line.startswith(tuple(f"{n}. " for n in range(1, 20))):
            doc.add_paragraph(line[3:], style="List Number")
        else:
            # 处理加粗 **text**
            p = doc.add_paragraph()
            parts = line.split("**")
            for pi, part in enumerate(parts):
                run = p.add_run(part)
                if pi % 2 == 1:
                    run.bold = True

        i += 1


async def export_files(state: dict) -> dict:
    """导出 Word + PDF 文件"""
    analysis_id = state.get("analysis_id", f"ANA-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}")
    final_report_md = state.get("final_report_md", "")
    chart_data = state.get("chart_data", {})
    export_paths = {}

    try:
        from docx import Document
        from docx.shared import Pt, Inches, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        import io as _io

        doc = Document()

        # 设置默认字体
        style = doc.styles['Normal']
        style.font.name = 'Microsoft YaHei'
        style.font.size = Pt(11)

        # ====== 封面/标题 ======
        doc.add_heading("综合分析报告", 0)

        # 基本信息表
        table = doc.add_table(rows=4, cols=2, style="Table Grid")
        mode_map = {"cross_project": "跨项目对比", "cross_time": "跨时段对比", "all_projects": "全项目概览"}
        info = [
            ("分析模式", mode_map.get(state.get("mode", ""), state.get("mode", ""))),
            ("分析对象", f"{state.get('label_a', '')} vs {state.get('label_b', '')}"),
            ("分析时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("分析模型", "DeepSeek-V3.2 (deepseek-chat)")
        ]
        for i, (k, v) in enumerate(info):
            table.rows[i].cells[0].text = k
            table.rows[i].cells[1].text = str(v)
            for paragraph in table.rows[i].cells[0].paragraphs:
                for run in paragraph.runs:
                    run.bold = True

        doc.add_paragraph()

        # ====== 得分对比区 ======
        score_analysis = state.get("score_analysis", {})
        mode = state.get("mode", "")
        comparison_matrix = state.get("comparison_matrix", [])
        label_a = state.get("label_a", "对象A")
        label_b = state.get("label_b", "对象B")

        if mode != "all_projects" and score_analysis:
            doc.add_heading("总体得分对比", level=1)
            score_table = doc.add_table(rows=3, cols=3, style="Table Grid")
            headers = ["指标", label_a, label_b]
            for ci, h in enumerate(headers):
                score_table.rows[0].cells[ci].text = h
                for paragraph in score_table.rows[0].cells[ci].paragraphs:
                    for run in paragraph.runs:
                        run.bold = True

            score_table.rows[1].cells[0].text = "总分"
            score_table.rows[1].cells[1].text = f"{score_analysis.get('total_score_a', 0):.2f}"
            score_table.rows[1].cells[2].text = f"{score_analysis.get('total_score_b', 0):.2f}"

            score_table.rows[2].cells[0].text = "评级"
            score_table.rows[2].cells[1].text = score_analysis.get('grade_a', '')
            score_table.rows[2].cells[2].text = score_analysis.get('grade_b', '')

            doc.add_paragraph()

        # ====== 模块对比表格 ======
        if comparison_matrix:
            doc.add_heading("模块得分对比明细", level=1)
            n_cols = 6 if mode != "all_projects" else 3
            m_table = doc.add_table(rows=len(comparison_matrix) + 1, cols=n_cols, style="Table Grid")

            if mode != "all_projects":
                m_headers = ["模块名称", "权重", f"{label_a}得分", f"{label_b}得分", "差值", "判定"]
            else:
                m_headers = ["模块名称", "权重", "得分"]

            for ci, h in enumerate(m_headers):
                m_table.rows[0].cells[ci].text = h
                for paragraph in m_table.rows[0].cells[ci].paragraphs:
                    for run in paragraph.runs:
                        run.bold = True

            for ri, m in enumerate(comparison_matrix):
                row = m_table.rows[ri + 1]
                row.cells[0].text = m.get("module_name", "")
                row.cells[1].text = f"{m.get('weight', 0) * 100:.0f}%"
                if mode != "all_projects":
                    row.cells[2].text = f"{m.get('score_a', 0):.2f}"
                    row.cells[3].text = f"{m.get('score_b', 0):.2f}"
                    row.cells[4].text = f"{m.get('diff', 0):+.2f}"
                    row.cells[5].text = m.get("winner", "")
                else:
                    row.cells[2].text = f"{m.get('score_a', 0):.2f}"

            doc.add_paragraph()

        # ====== 图表嵌入 ======
        chart_images = []
        chart_configs = [
            ("bar", "模块得分对比"),
            ("radar", "8维度雷达图"),
            ("heatmap", "项目×模块热力图"),
            ("ranking_bar", "项目总分排行"),
        ]
        for chart_key, chart_title in chart_configs:
            chart_option = chart_data.get(chart_key)
            if chart_option:
                try:
                    img_bytes = _render_chart_to_image(chart_option, chart_title)
                    img_stream = _io.BytesIO(img_bytes)
                    doc.add_heading(chart_title, level=2)
                    doc.add_picture(img_stream, width=Inches(6.0))
                    last_paragraph = doc.paragraphs[-1]
                    last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    doc.add_paragraph()
                    chart_images.append(chart_key)
                    logger.info(f"图表已嵌入: {chart_title}")
                except Exception as e:
                    logger.error(f"图表嵌入失败 {chart_key}: {e}")

        # ====== AI 分析正文 ======
        if final_report_md:
            _add_markdown_to_doc(doc, final_report_md)

        # 保存 Word
        word_path = settings.ANALYSIS_DIR / f"{analysis_id}.docx"
        doc.save(str(word_path))
        export_paths["word"] = str(word_path)
        logger.info(f"Word 文件已导出: {word_path}")

        # ====== 生成 PDF ======
        try:
            pdf_path = settings.ANALYSIS_DIR / f"{analysis_id}.pdf"
            _generate_pdf(state, final_report_md, chart_data, str(pdf_path))
            export_paths["pdf"] = str(pdf_path)
            logger.info(f"PDF 文件已导出: {pdf_path}")
        except Exception as e:
            logger.error(f"PDF导出失败: {e}")

    except Exception as e:
        logger.error(f"Word导出失败: {e}")
        import traceback
        traceback.print_exc()

    return {
        "analysis_id": analysis_id,
        "export_paths": export_paths,
        "current_step": "export_files",
        "progress_pct": 95
    }


def _generate_pdf(state: dict, final_report_md: str, chart_data: dict, pdf_path: str):
    """使用 reportlab 生成 PDF"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image as RLImage, PageBreak
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import io as _io
    import glob as _glob

    # 注册中文字体（优先外部 TTF，fallback 到内置 CID 字体）
    font_name = 'Helvetica'
    font_candidates = [
        '/app/fonts/simhei.ttf',
        '/app/fonts/NotoSansSC-Regular.ttf',
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
        '/usr/share/fonts/simhei.ttf',
    ]
    for pattern in ['/usr/share/fonts/**/*.ttf', '/usr/share/fonts/**/*.ttc']:
        for f in _glob.glob(pattern, recursive=True):
            if any(kw in f.lower() for kw in ['simhei', 'noto', 'wqy', 'cjk', 'sc-']):
                font_candidates.insert(0, f)
    for fp in font_candidates:
        if os.path.exists(fp) and os.path.getsize(fp) > 0:
            try:
                pdfmetrics.registerFont(TTFont('MSYH', fp))
                font_name = 'MSYH'
                break
            except Exception:
                continue

    # Fallback: 使用 reportlab 内置 CID 字体（支持中文，无需外部文件）
    if font_name == 'Helvetica':
        try:
            from reportlab.pdfbase.cidfonts import UnicodeCIDFont
            pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
            font_name = 'STSong-Light'
        except Exception:
            pass  # 最终 fallback 到 Helvetica（中文会乱码，但至少不会崩溃）

    doc = SimpleDocTemplate(
        pdf_path, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()

    # 自定义样式
    title_style = ParagraphStyle(
        'CNTitle', parent=styles['Title'],
        fontName=font_name, fontSize=20, spaceAfter=20, alignment=TA_CENTER
    )
    h1_style = ParagraphStyle(
        'CNH1', parent=styles['Heading1'],
        fontName=font_name, fontSize=16, spaceAfter=10, spaceBefore=16,
        textColor=HexColor('#1a1d26')
    )
    h2_style = ParagraphStyle(
        'CNH2', parent=styles['Heading2'],
        fontName=font_name, fontSize=14, spaceAfter=8, spaceBefore=12,
        textColor=HexColor('#1a1d26')
    )
    body_style = ParagraphStyle(
        'CNBody', parent=styles['Normal'],
        fontName=font_name, fontSize=10, leading=16, spaceAfter=6
    )
    bullet_style = ParagraphStyle(
        'CNBullet', parent=styles['Normal'],
        fontName=font_name, fontSize=10, leading=14, leftIndent=20,
        bulletIndent=10, spaceAfter=3
    )

    elements = []

    # 标题
    elements.append(Paragraph("综合分析报告", title_style))
    elements.append(Spacer(1, 10))

    # 基本信息表
    mode_map = {"cross_project": "跨项目对比", "cross_time": "跨时段对比", "all_projects": "全项目概览"}
    mode = state.get("mode", "")
    info_data = [
        ["分析模式", mode_map.get(mode, mode)],
        ["分析对象", f"{state.get('label_a', '')} vs {state.get('label_b', '')}"],
        ["分析时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["分析模型", "DeepSeek-V3.2"],
    ]
    info_table = Table(info_data, colWidths=[3*cm, 12*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (0, -1), HexColor('#f3f4f6')),
        ('BOLD', (0, 0), (0, -1)),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#d1d5db')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 15))

    # 得分对比
    score_analysis = state.get("score_analysis", {})
    comparison_matrix = state.get("comparison_matrix", [])
    label_a = state.get("label_a", "对象A")
    label_b = state.get("label_b", "对象B")

    if mode != "all_projects" and score_analysis:
        elements.append(Paragraph("总体得分对比", h1_style))
        score_data = [
            ["指标", label_a, label_b],
            ["总分", f"{score_analysis.get('total_score_a', 0):.2f}", f"{score_analysis.get('total_score_b', 0):.2f}"],
            ["评级", score_analysis.get('grade_a', ''), score_analysis.get('grade_b', '')],
        ]
        st = Table(score_data, colWidths=[3*cm, 6*cm, 6*cm])
        st.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
            ('BOLD', (0, 0), (-1, 0)),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#d1d5db')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(st)
        elements.append(Spacer(1, 10))

    # 模块对比表格
    if comparison_matrix:
        elements.append(Paragraph("模块得分对比明细", h1_style))
        if mode != "all_projects":
            m_headers = ["模块", "权重", f"{label_a}", f"{label_b}", "差值", "判定"]
            m_data = [m_headers]
            for m in comparison_matrix:
                m_data.append([
                    m.get("module_name", ""),
                    f"{m.get('weight', 0) * 100:.0f}%",
                    f"{m.get('score_a', 0):.2f}",
                    f"{m.get('score_b', 0):.2f}",
                    f"{m.get('diff', 0):+.2f}",
                    m.get("winner", ""),
                ])
            mt = Table(m_data, colWidths=[3*cm, 1.5*cm, 2.5*cm, 2.5*cm, 2*cm, 2*cm])
        else:
            m_headers = ["模块", "权重", "得分"]
            m_data = [m_headers]
            for m in comparison_matrix:
                m_data.append([
                    m.get("module_name", ""),
                    f"{m.get('weight', 0) * 100:.0f}%",
                    f"{m.get('score_a', 0):.2f}",
                ])
            mt = Table(m_data, colWidths=[5*cm, 3*cm, 5*cm])

        mt.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
            ('BOLD', (0, 0), (-1, 0)),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#d1d5db')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#ffffff'), HexColor('#f9fafb')]),
        ]))
        elements.append(mt)
        elements.append(Spacer(1, 10))

    # 图表
    chart_configs = [
        ("bar", "模块得分对比"),
        ("radar", "8维度雷达图"),
        ("heatmap", "项目×模块热力图"),
        ("ranking_bar", "项目总分排行"),
    ]
    for chart_key, chart_title in chart_configs:
        chart_option = chart_data.get(chart_key)
        if chart_option:
            try:
                img_bytes = _render_chart_to_image(chart_option, chart_title, width=1000, height=600)
                img_stream = _io.BytesIO(img_bytes)
                elements.append(Paragraph(chart_title, h2_style))
                elements.append(RLImage(img_stream, width=16*cm, height=10*cm))
                elements.append(Spacer(1, 10))
            except Exception as e:
                logger.error(f"[Analysis PDF] 图表嵌入失败 {chart_key}: {e}")

    # AI 分析正文
    if final_report_md:
        elements.append(PageBreak())
        elements.append(Paragraph("AI 分析报告", h1_style))
        elements.append(Spacer(1, 10))

        md_lines = final_report_md.split("\n")
        i = 0
        while i < len(md_lines):
            line = md_lines[i].strip()
            if not line:
                elements.append(Spacer(1, 4))
                i += 1
                continue

            # 渲染 Markdown 表格（行动建议等）
            if line.startswith("| ") and "|" in line[1:]:
                table_lines = []
                while i < len(md_lines) and md_lines[i].strip().startswith("|"):
                    table_lines.append(md_lines[i].strip())
                    i += 1
                # 过滤分隔行
                data_lines = [l for l in table_lines if not all(c in '|-: ' for c in l)]
                if data_lines:
                    parsed = []
                    for dl in data_lines:
                        cells = [c.strip() for c in dl.strip('|').split('|')]
                        parsed.append(cells)
                    if parsed:
                        n_cols = max(len(row) for row in parsed)
                        col_w = (16 * cm) / max(n_cols, 1)
                        table_data = []
                        for ri, row in enumerate(parsed):
                            row_cells = []
                            for ci in range(n_cols):
                                cell_text = row[ci] if ci < len(row) else ""
                                cell_text = cell_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                                row_cells.append(Paragraph(cell_text, body_style))
                            table_data.append(row_cells)
                        t = Table(table_data, colWidths=[col_w] * n_cols)
                        style_cmds = [
                            ('FONTNAME', (0, 0), (-1, -1), font_name),
                            ('FONTSIZE', (0, 0), (-1, -1), 9),
                            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#d1d5db')),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('TOPPADDING', (0, 0), (-1, -1), 3),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                        ]
                        if len(table_data) > 1:
                            style_cmds.append(('BACKGROUND', (0, 0), (-1, 0), HexColor('#2563eb')))
                            style_cmds.append(('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')))
                            style_cmds.append(('BOLD', (0, 0), (-1, 0)))
                        t.setStyle(TableStyle(style_cmds))
                        elements.append(t)
                        elements.append(Spacer(1, 8))
                continue

            # 转义 XML 特殊字符
            line_escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # 处理加粗 **text** → <b>text</b>
            import re
            line_formatted = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line_escaped)

            if line_formatted.startswith("# "):
                elements.append(Paragraph(line_formatted[2:], h1_style))
            elif line_formatted.startswith("## "):
                elements.append(Paragraph(line_formatted[3:], h2_style))
            elif line_formatted.startswith("### "):
                elements.append(Paragraph(line_formatted[4:], ParagraphStyle(
                    'CNH3', parent=body_style, fontSize=12, spaceBefore=8, spaceAfter=4
                )))
            elif line_formatted.startswith("> "):
                elements.append(Paragraph(line_formatted[2:], ParagraphStyle(
                    'CNQuote', parent=body_style, fontSize=10, leftIndent=20,
                    textColor=HexColor('#6b7280'), fontName=font_name
                )))
            elif line_formatted.startswith("- ") or line_formatted.startswith("* "):
                elements.append(Paragraph(f"• {line_formatted[2:]}", bullet_style))
            else:
                elements.append(Paragraph(line_formatted, body_style))

            i += 1

    doc.build(elements)


# ==================== 节点10: 保存结果 ====================
async def save_result(state: dict) -> dict:
    """保存分析结果到数据库"""
    db = SessionLocal()
    analysis_id = state.get("analysis_id", f"ANA-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}")
    mode = state.get("mode", "")
    projects_info = state.get("projects_info", [])

    try:
        # 检查是否已有记录（由API创建的初始记录）
        record = db.query(AnalysisRecord).filter(AnalysisRecord.analysis_id == analysis_id).first()

        result_json = json.dumps({
            "score_analysis": state.get("score_analysis", {}),
            "issue_analysis": state.get("issue_analysis", {}),
            "module_analysis": state.get("module_analysis", {}),
            "ai_result": state.get("ai_result", {}),
            "chart_data": state.get("chart_data", {}),
            "comparison_matrix": state.get("comparison_matrix", []),
            "projects_info": projects_info,
            "label_a": state.get("label_a", ""),
            "label_b": state.get("label_b", "")
        }, ensure_ascii=False)

        if record:
            record.result_json = result_json
            record.summary_text = state.get("executive_summary", "")
            record.file_path = state.get("export_paths", {}).get("word", "")
            record.pdf_path = state.get("export_paths", {}).get("pdf", "")
        else:
            record = AnalysisRecord(
                analysis_id=analysis_id,
                mode=mode,
                project_a_id=state.get("project_a_id"),
                project_b_id=state.get("project_b_id"),
                report_a_id=projects_info[0].get("report_id") if projects_info else None,
                report_b_id=projects_info[1].get("report_id") if len(projects_info) > 1 else None,
                time_range_start=state.get("time_range_start"),
                time_range_end=state.get("time_range_end"),
                result_json=result_json,
                summary_text=state.get("executive_summary", ""),
                file_path=state.get("export_paths", {}).get("word", ""),
                pdf_path=state.get("export_paths", {}).get("pdf", "")
            )
            db.add(record)

        # 模式三：保存 AnalysisProject 记录
        if mode == "all_projects":
            for idx, pi in enumerate(projects_info):
                ap = AnalysisProject(
                    analysis_id=analysis_id,
                    project_id=pi.get("project_id"),
                    report_id=pi.get("report_id"),
                    rank_position=idx + 1,
                    grade=pi.get("grade", "")
                )
                db.add(ap)

        db.commit()
        logger.info(f"结果已保存: {analysis_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"保存失败: {e}")
    finally:
        db.close()

    return {"current_step": "completed", "progress_pct": 100}
