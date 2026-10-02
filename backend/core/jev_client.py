"""
Jev 判断模型客户端（TypeSafe System One）

Jev 不生成文字，只返回类型化判断与校准概率，用于对生成式模型
（AI评分 / 整改复核）的结论做独立置信度复核。

问题类型（一个请求可混用，并行评估）：
    choice: {"type": "choice", "instructions": ..., "criteria": {选项: 说明}}
            → answer: {"choice", "confidence", "probabilities"}
    score:  {"type": "score",  "instructions": ..., "criteria": [说明0, 说明1, ...]}
            → answer: {"score", "legend", "probabilities"}
    noul:   {"type": "noul",   "instructions": ...}
            → answer: {"noul": 0-1 概率}

设计约束：任何失败一律返回 None，调用方回退现有置信度逻辑，绝不阻断主流程。
"""
import asyncio
import time
import logging
from typing import Dict, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)

# 熔断器：连续失败后暂停调用，避免拖慢评分/整改主链路（复用 llm_client 模式）
from core.llm_client import CircuitBreaker

_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=120)


def jev_available() -> bool:
    """Jev 是否已启用（开关 + Key）"""
    return bool(settings.JEV_ENABLED and settings.JEV_API_KEY)


async def jev_system_one(
    state: str,
    questions: Dict,
    call_type: str = "jev_verify",
) -> Optional[Dict]:
    """
    调用 systemone 端点，返回 answers 字典；失败/未启用返回 None。

    Args:
        state: 待判断的文本上下文（检查标准/问题/AI结论等，Jev 不能看图）
        questions: 类型化问题定义，见模块 docstring
        call_type: 用量日志里的调用类型标记（jev_scoring / jev_rectification）
    """
    if not jev_available():
        return None
    if _breaker.is_open("jev"):
        logger.debug("Jev 熔断中，跳过判断")
        return None

    payload = {
        "state": state,
        "model": settings.JEV_MODEL,
        "questions": questions,
    }

    try:
        start = time.time()
        resp = None
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            # 跨境链路抖动：连接类失败重试1次
            for attempt in range(2):
                try:
                    resp = await client.post(
                        f"{settings.JEV_BASE_URL}/v1/systemone",
                        headers={
                            "Authorization": f"Bearer {settings.JEV_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                    break
                except (httpx.ConnectTimeout, httpx.ConnectError):
                    if attempt == 1:
                        raise
                    logger.info("Jev 连接失败，重试1次")
                    await asyncio.sleep(1)
        duration_ms = int((time.time() - start) * 1000)

        if resp.status_code != 200:
            _breaker.record_failure("jev")
            logger.warning(f"Jev API {resp.status_code}: {resp.text[:200]}")
            return None

        result = resp.json()
        _breaker.record_success("jev")

        # 用量日志（对齐 llm_client 的 prompt/completion 口径）
        usage = result.get("usage") or {}
        try:
            from core.llm_client import _log_llm_usage
            _log_llm_usage(
                settings.JEV_MODEL, call_type,
                {"usage": {
                    "prompt_tokens": usage.get("input_tokens", 0),
                    "completion_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                }},
                duration_ms,
            )
        except Exception:
            pass  # 日志失败不影响判断结果

        return result.get("answers") or {}

    except Exception as e:
        _breaker.record_failure("jev")
        logger.warning(f"Jev 调用异常（回退现有置信度）: {e!r}")
        return None
