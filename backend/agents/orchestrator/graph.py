"""
Orchestrator LangGraph 图构建
串联 Agent 2 → [审核门控] → Agent 3 → Agent 4

工作流:
  start_pipeline → run_scoring → check_review_gate → [run_report 或 wait_for_review]
                                       ↓                ↓
                                   track_rectification → finalize

  审核门控仅在 ENABLE_HUMAN_REVIEW_GATE=True 时生效，默认直接跳过
"""
from langgraph.graph import StateGraph, END

from core.logger import get_logger
logger = get_logger("orchestrator_graph")

from .state import OrchestratorState
from .nodes import (
    start_pipeline,
    run_scoring,
    run_report,
    track_rectification,
    finalize,
    check_human_review_gate,
    should_run_report,
    should_track_rectification,
    should_wait_for_review,
)


def build_orchestrator_graph():
    """
    构建 Orchestrator LangGraph 图

    流程 (ENABLE_HUMAN_REVIEW_GATE=False, 默认):
      start_pipeline → run_scoring → check_review_gate → run_report → track_rectification → finalize

    流程 (ENABLE_HUMAN_REVIEW_GATE=True):
      start_pipeline → run_scoring → check_review_gate → [wait_for_review / run_report]
                        ↘ (失败) → finalize
    """
    graph = StateGraph(OrchestratorState)

    # 添加节点
    graph.add_node("start_pipeline", start_pipeline)
    graph.add_node("run_scoring", run_scoring)
    graph.add_node("check_review_gate", check_human_review_gate)
    graph.add_node("run_report", run_report)
    graph.add_node("track_rectification", track_rectification)
    graph.add_node("finalize", finalize)

    # wait_for_review 是一个空节点（暂停点），等待外部 resume
    async def wait_for_review(state):
        """等待人工审核 — 节点不做任何操作，仅标记状态"""
        return {"current_step": "waiting_for_review"}

    graph.add_node("wait_for_review", wait_for_review)

    # 设置入口
    graph.set_entry_point("start_pipeline")

    # start_pipeline → run_scoring
    graph.add_edge("start_pipeline", "run_scoring")

    # run_scoring 成功后 → check_review_gate，失败后 → finalize
    graph.add_conditional_edges(
        "run_scoring",
        lambda state: "check_review_gate" if should_run_report(state) else "finalize",
        {
            "check_review_gate": "check_review_gate",
            "finalize": "finalize"
        }
    )

    # check_review_gate → run_report 或 wait_for_review
    graph.add_conditional_edges(
        "check_review_gate",
        should_wait_for_review,
        {
            "run_report": "run_report",
            "wait_for_review": "wait_for_review",
        }
    )

    # wait_for_review → finalize（暂停后由外部 resume 再走 run_report）
    graph.add_edge("wait_for_review", "finalize")

    # run_report 成功后 → track_rectification，失败后 → finalize
    graph.add_conditional_edges(
        "run_report",
        lambda state: "track_rectification" if should_track_rectification(state) else "finalize",
        {
            "track_rectification": "track_rectification",
            "finalize": "finalize"
        }
    )

    # track_rectification → finalize
    graph.add_edge("track_rectification", "finalize")

    # finalize → END
    graph.add_edge("finalize", END)

    return graph.compile()


# 预编译的 graph 实例（单例）
_orchestrator_graph = None


def get_orchestrator_graph():
    """获取或创建 Orchestrator graph 单例"""
    global _orchestrator_graph
    if _orchestrator_graph is None:
        _orchestrator_graph = build_orchestrator_graph()
    return _orchestrator_graph
