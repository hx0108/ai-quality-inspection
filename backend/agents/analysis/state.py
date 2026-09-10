"""
综合分析 Agent 状态定义（与现有 Agent 2/3 保持一致的 TypedDict 模式）
"""
from typing import TypedDict, Optional, Annotated
from operator import add


class AnalysisState(TypedDict, total=False):
    """综合分析 Agent 状态"""

    # === 输入 ===
    mode: str                           # "cross_project" / "cross_time" / "all_projects"
    project_a_id: Optional[int]
    project_b_id: Optional[int]
    time_range_start: Optional[str]
    time_range_end: Optional[str]
    report_a_id: Optional[str]
    report_b_id: Optional[str]
    project_ids: Optional[list]          # 全项目概览：选中的项目ID列表
    filters: Optional[dict]

    # === 数据收集输出 ===
    reports_data: list                  # 从 Report.content_json 解析的报告数据列表
    projects_info: list                 # 项目基本信息列表
    label_a: str                        # 对象A 标签（如 "中新里 (2026-04-03)"）
    label_b: str                        # 对象B 标签

    # === 三维度分析输出 ===
    comparison_matrix: list             # 各模块对比矩阵（按报告实际模块，蝶城8/砺质5）
    score_analysis: dict                # 维度一: 综合得分分析
    issue_analysis: dict                # 维度二: 问题分布分析
    module_analysis: dict               # 维度三: 逐模块分析

    # === 洞察生成输出 ===
    ai_result: dict                     # LLM 返回的完整分析结果
    executive_summary: str
    action_items: list

    # === 图表数据 ===
    chart_data: dict                    # ECharts 配置 JSON

    # === 最终输出 ===
    final_report_md: str                # 完整 Markdown 报告
    analysis_id: str
    export_paths: dict                  # {"word": "...", "pdf": "..."}

    # === 进度与错误 ===
    current_step: str
    progress_pct: int
    valid: bool
    error_message: str
    errors: Annotated[list, add]
