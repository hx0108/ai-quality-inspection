"""
Scoring Agent 状态定义
Agent 2 LangGraph State
"""
from typing import TypedDict, Annotated
from operator import add


class ScoringState(TypedDict):
    """评分工作流状态"""
    # 输入
    task_id: str

    # collect_records 输出
    records: list                       # [{record_id, module_name}]
    standard_type: str                  # diecheng / feidiecheng

    # score_module 并行输出（reducer: 追加合并）
    scoring_results: Annotated[list, add]

    # 进度
    completed_modules: Annotated[list, add]  # ["客户服务", "安全管理", ...]
    errors: Annotated[list, add]
