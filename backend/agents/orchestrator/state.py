"""
Orchestrator 状态定义
串联 Agent 2 → Agent 3 → Agent 4
"""
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime


class OrchestratorState(TypedDict, total=False):
    """Orchestrator 工作流状态"""

    # 任务信息
    task_id: str                           # 检查任务ID
    project_id: int                         # 项目ID
    project_name: str                        # 项目名称
    check_date: str                         # 检查日期

    # Agent 2 评分结果
    scoring_completed: bool                 # 评分是否完成
    scoring_results: List[Dict[str, Any]]   # 评分结果列表
    module_scores: List[Dict[str, Any]]     # 各模块百分制得分
    total_score: float                      # 项目总分

    # Agent 3 报告结果
    report_completed: bool                  # 报告是否生成
    report_id: str                          # 报告ID
    report_file_path: str                   # 报告文件路径
    module_analyses: List[Dict[str, Any]]   # 各模块分析结果
    overall_analysis: Dict[str, Any]        # 综合分析结果

    # Agent 4 整改追踪
    rectification_tracked: bool             # 整改是否已追踪
    pending_rectifications: int            # 待整改数量
    completed_rectifications: int           # 已完成整改数量

    # Human-in-the-Loop 审核门控
    needs_human_review: bool                # 是否需要人工审核
    review_count: int                       # 待审核项数量

    # 流程状态
    current_step: str                       # 当前步骤: scoring / report / rectification / done
    steps_completed: List[str]             # 已完成的步骤列表
    error: Optional[str]                    # 错误信息
    error_detail: Optional[str]             # 错误详情

    # 元数据
    started_at: str                        # 开始时间
    completed_at: Optional[str]             # 完成时间
    duration_seconds: Optional[float]      # 耗时（秒）