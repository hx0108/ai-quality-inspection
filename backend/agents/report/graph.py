"""
Report Agent LangGraph 图构建
Agent 3: DeepSeek-V3.2 AI 分析 + 并行模块分析

工作流:
  collect_data → fan-out(analyze_module × N) → fan-in → generate_report → export_files → save_report
"""
from langgraph.graph import StateGraph, END
from langgraph.types import Send

from core.logger import get_logger
logger = get_logger("report_graph")

from .state import ReportState
from .nodes import collect_data, analyze_module, generate_report_node, export_files, save_report


def fan_out_analyze(state: dict) -> list[Send]:
    """
    条件边：动态分发 analyze_module 任务
    只对已评分模块并行分析
    """
    module_scores = state.get("module_scores", [])
    modules_data = state.get("modules_data", {})
    task_id = state["task_id"]
    project_id = state.get("project_id")
    check_date = state.get("check_date", "")
    modules_done = state.get("modules_done", 0)

    sends = []
    for module in module_scores:
        if module["module_pct_score"] <= 0:
            continue

        module_name = module["module_name"]
        data = modules_data.get(module_name, {})

        # 只传关键信息给 DeepSeek，避免 token 过长
        items_summary = []
        for item in data.get("items", []):
            items_summary.append({
                "item_id": item["item_id"],
                "item_name": item["item_name"],
                "score": item["score"],
                "scoring_basis": item["scoring_basis"],
                "improvement_suggestion": item["improvement_suggestion"]
            })

        sends.append(Send("analyze_module", {
            "task_id": task_id,
            "project_id": project_id,
            "check_date": check_date,
            "module_name": module_name,
            "module_pct_score": module["module_pct_score"],
            "items_summary": items_summary,
            "modules_done": modules_done,
        }))

    logger.info(f"fan-out: {len(sends)} 个模块待分析")
    return sends


def build_report_graph() -> StateGraph:
    """
    构建报告生成 LangGraph 图
    """
    graph = StateGraph(ReportState)

    # 添加节点
    graph.add_node("collect_data", collect_data)
    graph.add_node("analyze_module", analyze_module)
    graph.add_node("generate_report", generate_report_node)
    graph.add_node("export_files", export_files)
    graph.add_node("save_report", save_report)

    # 设置入口
    graph.set_entry_point("collect_data")

    # collect_data → fan-out(analyze_module × N) 并行分析
    graph.add_conditional_edges("collect_data", fan_out_analyze)

    # analyze_module 完成后 → fan-in 自动汇聚 → generate_report
    graph.add_edge("analyze_module", "generate_report")

    # generate_report → export_files → save_report → END
    graph.add_edge("generate_report", "export_files")
    graph.add_edge("export_files", "save_report")
    graph.add_edge("save_report", END)

    return graph.compile()
