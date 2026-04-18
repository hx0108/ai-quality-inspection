"""
整改验证 LangGraph 节点函数

节点:
  validate_photos   → 验证照片完整性和有效性
  ai_verify         → 调用 Qwen-VL 进行AI核查
  judge_result      → 根据置信度阈值判定结果
  save_result       → 保存结果到数据库
  notify            → SSE 通知 + 长期记忆更新
"""
import os
import json
import time
import asyncio
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional

from database import SessionLocal
from models.models import Rectification, Issue, Photo, InspectionTask, ProjectMemory
from config import settings
from core.logger import get_logger

logger = get_logger("rectification_nodes")

# 并发控制：最多2个整改验证同时进行
_verify_semaphore = threading.Semaphore(2)


async def validate_photos(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    节点1: 验证照片完整性
    - 检查整改照片是否存在
    - 检查照片文件是否可读
    - 检查照片数量是否足够
    """
    rect_id = state.get("rectification_id", "")
    logger.info(f"[Rectification] 验证照片: {rect_id}")
    state["current_step"] = "validate_photos"

    rect_photo_paths = state.get("rectification_photo_paths", [])
    issue_photo_paths = state.get("issue_photo_paths", [])

    # 检查整改照片
    valid_rect_photos = [p for p in rect_photo_paths if os.path.exists(p)]
    valid_issue_photos = [p for p in issue_photo_paths if os.path.exists(p)]

    if not valid_rect_photos:
        state["photos_valid"] = False
        state["photos_count"] = 0
        state["photo_validation_msg"] = "未找到有效的整改照片文件"
        state["final_status"] = "ai_rejected"
        state["ai_result"] = {
            "photo_valid": False,
            "photo_info": "未找到整改照片文件",
            "note_qualified": False,
            "note_info": "",
            "confidence_score": 0,
            "rectification_depth": "无法判断",
            "analysis": "整改照片文件不存在或无法读取",
            "suggestion": "驳回"
        }
        state["confidence_score"] = 0
        state["suggestion"] = "驳回"
        logger.warning(f"[Rectification] 无有效整改照片: {rect_id}")
        return state

    state["rectification_photo_paths"] = valid_rect_photos
    state["issue_photo_paths"] = valid_issue_photos
    state["photos_valid"] = True
    state["photos_count"] = len(valid_rect_photos)
    state["photo_validation_msg"] = f"照片验证通过: {len(valid_rect_photos)}张整改照片, {len(valid_issue_photos)}张原问题照片"

    logger.info(f"[Rectification] 照片验证通过: {rect_id}, 整改={len(valid_rect_photos)}, 问题={len(valid_issue_photos)}")
    return state


async def ai_verify(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    节点2: 调用 Qwen-VL 进行AI核查
    - 使用核心 checker 逻辑
    - 包含重试机制（最多2次）
    """
    rect_id = state.get("rectification_id", "")
    logger.info(f"[Rectification] AI核查: {rect_id}")
    state["current_step"] = "ai_verify"

    # 照片无效则跳过AI调用
    if not state.get("photos_valid", False):
        logger.info(f"[Rectification] 照片无效，跳过AI核查: {rect_id}")
        return state

    from agents.rectification.checker import check_rectification

    max_retries = 2
    ai_result = None

    for attempt in range(1, max_retries + 1):
        try:
            ai_result = await check_rectification(
                issue_description=state.get("issue_description", ""),
                issue_severity=state.get("issue_severity", "一般"),
                issue_location=state.get("issue_location", ""),
                issue_photo_paths=state.get("issue_photo_paths", []),
                rectification_photo_paths=state.get("rectification_photo_paths", []),
                rectification_note=state.get("rectification_note", ""),
                expected_location=state.get("expected_location", "")
            )
            logger.info(f"[Rectification] AI核查成功 (attempt={attempt}): {rect_id}")
            break
        except Exception as e:
            logger.warning(f"[Rectification] AI核查失败 (attempt={attempt}/{max_retries}): {e}")
            if attempt == max_retries:
                ai_result = {
                    "photo_valid": False,
                    "photo_info": "",
                    "note_qualified": False,
                    "note_info": "",
                    "confidence_score": 0,
                    "rectification_depth": "无法判断",
                    "analysis": f"AI核查异常（重试{max_retries}次）: {str(e)}",
                    "suggestion": "驳回"
                }

    if ai_result:
        state["ai_result"] = ai_result
        state["confidence_score"] = float(ai_result.get("confidence_score", 0))
        state["suggestion"] = ai_result.get("suggestion", "驳回")
    else:
        state["ai_result"] = {
            "photo_valid": False, "photo_info": "", "note_qualified": False,
            "note_info": "", "confidence_score": 0,
            "rectification_depth": "无法判断", "analysis": "AI核查未返回结果", "suggestion": "驳回"
        }
        state["confidence_score"] = 0
        state["suggestion"] = "驳回"

    return state


async def judge_result(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    节点3: 根据置信度阈值判定结果
    - ≥85: 通过
    - 50-84: 人工复核
    - <50: 驳回
    - 支持多轮整改：驳回时记录轮次
    """
    rect_id = state.get("rectification_id", "")
    state["current_step"] = "judge_result"

    confidence = state.get("confidence_score", 0)
    suggestion = state.get("suggestion", "驳回")
    round_number = state.get("round_number", 1)

    # 置信度阈值判定
    if confidence >= 85 and suggestion == "通过":
        state["final_status"] = "ai_approved"
        logger.info(f"[Rectification] 判定通过: {rect_id}, score={confidence}, round={round_number}")
    elif 50 <= confidence < 85 or suggestion == "人工复核":
        state["final_status"] = "pending_review"
        logger.info(f"[Rectification] 判定人工复核: {rect_id}, score={confidence}, round={round_number}")
    else:
        state["final_status"] = "ai_rejected"
        logger.warning(f"[Rectification] 判定驳回: {rect_id}, score={confidence}, round={round_number}")

    return state


async def save_result(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    节点4: 保存结果到数据库
    - 更新整改记录状态
    - 保存AI核查结果
    """
    rect_id = state.get("rectification_id", "")
    state["current_step"] = "save_result"

    db = SessionLocal()
    try:
        r = db.query(Rectification).filter(
            Rectification.rectification_id == rect_id
        ).first()
        if not r:
            state["error"] = f"整改记录不存在: {rect_id}"
            return state

        # 更新状态
        r.status = state.get("final_status", "ai_rejected")
        r.ai_result = json.dumps(state.get("ai_result", {}), ensure_ascii=False)
        r.ai_checked_at = datetime.utcnow()
        r.updated_at = datetime.utcnow()

        # 更新多轮次信息（如果有 round_number 字段）
        if hasattr(r, 'round_number'):
            r.round_number = state.get("round_number", 1)

        db.commit()
        logger.info(f"[Rectification] 结果已保存: {rect_id}, status={r.status}")

    except Exception as e:
        logger.error(f"[Rectification] 保存结果失败: {e}")
        state["error"] = str(e)
        db.rollback()
    finally:
        db.close()

    return state


async def notify(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    节点5: SSE通知 + 长期记忆更新
    - 推送整改验证结果事件
    - 将整改模式写入长期记忆（供检查引导Agent使用）
    """
    rect_id = state.get("rectification_id", "")
    task_id = state.get("task_id", "")
    state["current_step"] = "notify"
    state["completed_at"] = datetime.now().isoformat()

    # SSE 通知
    try:
        from core.event_bus import event_bus
        await event_bus.publish(f"task:{task_id}", {
            "type": "rectification_verified",
            "rectification_id": rect_id,
            "status": state.get("final_status"),
            "confidence": state.get("confidence_score", 0),
            "suggestion": state.get("suggestion"),
        })
    except Exception as e:
        logger.warning(f"[Rectification] SSE通知失败: {e}")

    # 长期记忆：记录整改验证结果模式（供引导Agent使用）
    try:
        _update_rectification_memory(state)
    except Exception as e:
        logger.warning(f"[Rectification] 记忆更新失败: {e}")

    logger.info(f"[Rectification] 流程完成: {rect_id}")
    return state


def _update_rectification_memory(state: Dict[str, Any]):
    """将整改验证结果写入长期记忆"""
    if not state.get("task_id"):
        return

    db = SessionLocal()
    try:
        task = db.query(InspectionTask).filter(
            InspectionTask.task_id == state["task_id"]
        ).first()
        if not task or not task.project_id:
            return

        from core.long_memory import LongMemory, MemoryType
        memory = LongMemory()

        confidence = state.get("confidence_score", 0)
        severity = state.get("issue_severity", "一般")
        module = state.get("issue_module_name", "")
        description = state.get("issue_description", "")
        suggestion = state.get("suggestion", "")

        content = f"整改验证: [{severity}] {description[:50]}... → AI{suggestion}(置信度{confidence})"

        memory.add_memory(
            project_id=task.project_id,
            memory_type=MemoryType.IMPROVEMENT_TREND,
            content=content,
            module_name=module,
            confidence=confidence / 100.0,
            source="rectification_agent"
        )
    except Exception:
        pass
    finally:
        db.close()


# ==================== 条件边函数 ====================

def should_ai_verify(state: Dict[str, Any]) -> str:
    """条件边：照片有效则AI核查，否则直接保存"""
    if state.get("photos_valid", False):
        return "ai_verify"
    return "save_result"


def should_notify(state: Dict[str, Any]) -> bool:
    """条件边：总是通知"""
    return True
