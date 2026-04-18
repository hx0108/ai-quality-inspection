"""
Scoring Agent LangGraph 图构建
Agent 2: Qwen-plus AI 评分 + 并行模块评分

工作流:
  collect_records → fan-out(score_module × N) → fan-in → compute_total → END
"""
from langgraph.graph import StateGraph, END
from langgraph.types import Send

from core.logger import get_logger
logger = get_logger("scoring_graph")

from .state import ScoringState
from .nodes import collect_records, score_module, compute_total


def fan_out_scoring(state: dict) -> list:
    """
    条件边：动态分发 score_module 任务
    只对未评分的模块并行评分
    """
    records = state.get("records", [])
    task_id = state["task_id"]
    standard_type = state.get("standard_type", "diecheng")

    sends = []
    for record in records:
        sends.append(Send("score_module", {
            "task_id": task_id,
            "record_id": record["record_id"],
            "module_name": record["module_name"],
            "standard_type": standard_type,
        }))

    logger.info(f"fan-out: {len(sends)} 个模块待评分")
    return sends


def build_scoring_graph():
    """
    构建评分 LangGraph 图
    """
    graph = StateGraph(ScoringState)

    # 添加节点
    graph.add_node("collect_records", collect_records)
    graph.add_node("score_module", score_module)
    graph.add_node("compute_total", compute_total)

    # 设置入口
    graph.set_entry_point("collect_records")

    # collect_records → fan-out(score_module × N) 并行评分
    graph.add_conditional_edges("collect_records", fan_out_scoring)

    # score_module 完成后 → fan-in 自动汇聚 → compute_total
    graph.add_edge("score_module", "compute_total")

    # compute_total → END
    graph.add_edge("compute_total", END)

    return graph.compile()
