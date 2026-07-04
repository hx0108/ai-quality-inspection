"""
Report Agent 状态定义
Agent 3 LangGraph State
"""
from typing import TypedDict, Annotated
from operator import add


class ReportState(TypedDict):
    """报告生成工作流状态"""
    # 输入
    task_id: str
    project_id: int

    # collect_data 输出
    project_name: str
    check_date: str
    standard_type: str
    total_score: float
    module_scores: list                    # [{module_name, module_pct_score, weight_ratio, ...}]
    modules_data: dict                     # {module_name: {items, raw_score_sum, ...}}
    issues_by_severity: dict               # {"严重": [...], "一般": [...], "轻微": [...]}
    issue_summary: dict

    # analyze_module 并行输出（reducer: 追加合并）
    module_analyses: Annotated[list, add]

    # generate_report 输出
    ai_full_report: str

    # export_files 输出
    report_id: str
    word_path: str
    pdf_path: str

    # 进度
    current_step: str
    modules_done: int
    modules_total: int
    errors: Annotated[list, add]
