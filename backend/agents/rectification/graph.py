"""
整改验证 LangGraph 图构建

工作流:
  validate_photos → [ai_verify | skip] → judge_result → save_result → notify → END

照片无效时跳过AI核查，直接驳回。
"""
from langgraph.graph import StateGraph, END

from core.logger import get_logger
logger = get_logger("rectification_graph")

from .state import RectificationState
from .nodes import (
    validate_photos,
    ai_verify,
    judge_result,
    save_result,
    notify,
    should_ai_verify,
)


def build_rectification_graph():
    """
    构建整改验证 LangGraph 图

    流程:
      validate_photos → ai_verify → judge_result → save_result → notify → END
                         ↑ (照片无效则跳过，直接 save_result)
    """
    graph = StateGraph(RectificationState)

    # 添加节点
    graph.add_node("validate_photos", validate_photos)
    graph.add_node("ai_verify", ai_verify)
    graph.add_node("judge_result", judge_result)
    graph.add_node("save_result", save_result)
    graph.add_node("notify", notify)

    # 设置入口
    graph.set_entry_point("validate_photos")

    # validate_photos → ai_verify 或 save_result（照片无效时跳过AI）
    graph.add_conditional_edges(
        "validate_photos",
        should_ai_verify,
        {
            "ai_verify": "ai_verify",
            "save_result": "save_result"
        }
    )

    # ai_verify → judge_result
    graph.add_edge("ai_verify", "judge_result")

    # judge_result → save_result
    graph.add_edge("judge_result", "save_result")

    # save_result → notify
    graph.add_edge("save_result", "notify")

    # notify → END
    graph.add_edge("notify", END)

    return graph.compile()


# 预编译的 graph 实例（单例）
_rectification_graph = None


def get_rectification_graph():
    """获取或创建整改验证 graph 单例"""
    global _rectification_graph
    if _rectification_graph is None:
        _rectification_graph = build_rectification_graph()
    return _rectification_graph
