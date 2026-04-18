"""
整改验证 LangGraph 状态定义
流程: validate_photos → ai_verify → judge_result → [pass/人工复核/驳回]
"""
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime


class RectificationState(TypedDict, total=False):
    """整改验证工作流状态"""

    # 输入
    rectification_id: str              # 整改记录ID
    issue_id: str                       # 问题ID
    record_id: str                      # 检查记录ID
    task_id: str                        # 任务ID

    # 问题信息
    issue_description: str              # 原问题描述
    issue_severity: str                 # 严重程度
    issue_location: str                 # 问题位置
    issue_module_name: str              # 所属模块
    expected_location: str              # 预期地点（项目名）

    # 照片
    issue_photo_paths: List[str]        # 原问题照片路径
    rectification_photo_paths: List[str]  # 整改照片路径

    # 整改信息
    rectification_note: str             # 整改说明
    rectification_time: str             # 整改时间
    round_number: int                   # 当前轮次（1=首次, 2=二次整改...）

    # 照片验证结果
    photos_valid: bool                  # 照片是否有效
    photos_count: int                   # 整改照片数量
    photo_validation_msg: str           # 验证消息

    # AI核查结果
    ai_result: Dict[str, Any]           # AI核查完整结果
    confidence_score: float             # 置信度分数
    suggestion: str                     # AI建议: 通过/驳回/人工复核

    # 最终判定
    final_status: str                   # 最终状态: ai_approved/ai_rejected/pending_review

    # 流程状态
    current_step: str                   # 当前步骤
    error: Optional[str]                # 错误信息
    started_at: str                     # 开始时间
    completed_at: Optional[str]         # 完成时间
