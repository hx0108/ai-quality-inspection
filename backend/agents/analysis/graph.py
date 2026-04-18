"""
综合分析 Agent 图构建
工作流: validate_input → collect_reports → [analyze_score, analyze_issue, analyze_module] 并行
→ generate_insight → render_charts → assemble_report → export_files → save_result → END
"""
from langgraph.graph import StateGraph, END
from agents.analysis.state import AnalysisState
from agents.analysis import nodes


def build_analysis_graph():
    """构建综合分析 LangGraph 图"""
    graph = StateGraph(AnalysisState)

    # 添加节点
    graph.add_node("validate_input", nodes.validate_input)
    graph.add_node("collect_reports", nodes.collect_reports)
    graph.add_node("analyze_score", nodes.analyze_score)
    graph.add_node("analyze_issue", nodes.analyze_issue)
    graph.add_node("analyze_module", nodes.analyze_module)
    graph.add_node("generate_insight", nodes.generate_insight)
    graph.add_node("render_charts", nodes.render_charts)
    graph.add_node("assemble_report", nodes.assemble_report)
    graph.add_node("export_files", nodes.export_files)
    graph.add_node("save_result", nodes.save_result)

    # 入口
    graph.set_entry_point("validate_input")

    # 条件边：验证失败直接结束
    graph.add_conditional_edges(
        "validate_input",
        lambda state: "collect_reports" if state.get("valid", False) else END,
        {
            "collect_reports": "collect_reports",
            END: END
        }
    )

    # collect_reports → 并行三维度分析
    graph.add_edge("collect_reports", "analyze_score")
    graph.add_edge("collect_reports", "analyze_issue")
    graph.add_edge("collect_reports", "analyze_module")

    # 三维度 → generate_insight (LangGraph auto fan-in)
    graph.add_edge("analyze_score", "generate_insight")
    graph.add_edge("analyze_issue", "generate_insight")
    graph.add_edge("analyze_module", "generate_insight")

    # 后续线性流程
    graph.add_edge("generate_insight", "render_charts")
    graph.add_edge("render_charts", "assemble_report")
    graph.add_edge("assemble_report", "export_files")
    graph.add_edge("export_files", "save_result")
    graph.add_edge("save_result", END)

    return graph.compile()
