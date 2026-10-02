"""
整改照片 AI 核查模块
使用 Qwen-VL 视觉模型分析整改照片
"""
import json
import base64
import httpx
from datetime import datetime
from typing import List, Dict, Any, Optional

from config import settings

import logging
logger = logging.getLogger(__name__)


async def check_rectification(
    issue_description: str,
    issue_severity: str,
    issue_location: str,
    issue_photo_paths: List[str],
    rectification_photo_paths: List[str],
    rectification_note: str,
    expected_location: str = ""
) -> Dict[str, Any]:
    """
    调用 Qwen-VL 视觉模型核查整改照片

    Args:
        issue_description: 原问题描述
        issue_severity: 问题严重程度
        issue_location: 问题位置
        issue_photo_paths: 原问题照片文件路径列表
        rectification_photo_paths: 整改照片文件路径列表
        rectification_note: 整改说明
        expected_location: 预期地点（从任务获取）

    Returns:
        AI核查结果: { photo_valid, photo_info, note_qualified, note_info,
                     confidence_score, rectification_depth, analysis, suggestion }
    """
    api_key = settings.DASHSCOPE_API_KEY
    if not api_key:
        return _default_result(False, "API密钥未配置")

    if not rectification_photo_paths:
        return _default_result(False, "未提供整改照片")

    # 编码照片为 base64
    try:
        issue_images = [_encode_image(p) for p in issue_photo_paths[:3]]
        rect_images = [_encode_image(p) for p in rectification_photo_paths[:5]]
    except Exception as e:
        return _default_result(False, f"照片编码失败: {str(e)}")

    # 构建多模态消息
    content_parts = []

    # 文字说明部分
    text_prompt = f"""你是物业品质检查整改核查专家。请分析以下整改材料，判断整改是否合格。

【重要说明】
本次核查将采用"水印照片+整改说明"双通道验证方式：
- 水印照片可验证时，优先核查照片
- 管理性/程序性问题（制度更新、培训完成、资料归档等）无法通过照片验证，需重点审查整改说明
- 两种方式满足任一要求，且不存在驳回条件时，即可判定通过

## 原始问题信息
- 问题描述：{issue_description}
- 严重程度：{issue_severity}
- 问题位置：{issue_location or '未指定'}

## 整改信息
- 整改说明：{rectification_note or '无说明'}
- 预期地点：{expected_location or '未指定'}

## 核查要求

### 通道一：照片核查（适用于可拍照验证的物理性问题）

**维度一：水印验证**
- 水印时间必须在整改期限内存地范围内，且不能早于问题发现时间
- 水印地点应与问题位置一致或合理范围内
- 水印信息不完整或存在明显异常的，视为水印无效

**维度二：整改对比**
- 问题区域是否已被实际修复（而非临时遮挡或表面处理）
- 修复质量是否符合行业标准（如修补平整、无色差、无安全隐患）
- 修复范围是否覆盖了问题描述中的所有区域

**维度三：整改长效性**
- 是否仅为表面处理（如仅用物品遮挡、仅刷漆覆盖）
- 是否存在复发风险（如裂缝只补漆未加固、积水只清理未做防水）

### 通道二：说明核查（适用于管理性/程序性问题）

**维度四：整改说明核查**
请重点审查整改说明的完整性和合理性：
- 整改说明是否明确描述了已完成的具体整改动作？
- 整改动作是否与原问题对应（问题→动作→结果，逻辑完整）？
- 完成时间和责任方是否合理？
- 涉及制度更新、培训、记录归档等，是否有支撑材料描述？

**【以下情况可依据说明判定通过】**
- 属于管理性/程序性问题（如培训完成、制度更新、资料归档）
- 问题描述与整改说明逻辑对应
- 说明内容具体、可信、不存在明显漏洞

**【以下情况属整改说明不合格，触发驳回】**
- 说明含糊不清（如仅写"已完成整改"无具体内容）
- 说明与问题描述明显不符
- 说明中描述的完成时间早于问题发现时间（逻辑错误）
- 说明描述的动作无法解决原问题

## 本次核查照片情况
整改照片：{len(rectification_photo_paths)} 张，原问题照片：{len(issue_photo_paths)} 张

## 输出格式（必须是合法JSON）
```json
{{
    "photo_valid": true或false,
    "photo_info": "照片核查结果摘要，包括水印验证、整改对比、长效性判断",
    "note_qualified": true或false,
    "note_info": "整改说明核查结果，包括说明完整性和逻辑合理性判断",
    "confidence_score": 0-100的置信度分数,
    "rectification_depth": "根本性修复/表面处理/临时遮挡/管理性整改/无法判断",
    "analysis": "综合分析，按通道一（照片）和通道二（说明）分别说明，最后给出综合判定依据",
    "suggestion": "通过/驳回/人工复核"
}}
```

## 置信度与建议对照表
- confidence_score ≥ 85 → suggestion = "通过"
- 50 ≤ confidence_score < 85 → suggestion = "人工复核"
- confidence_score < 50 → suggestion = "驳回"

直接输出JSON，不要有其他文字。"""

    content_parts.append({"type": "text", "text": text_prompt})

    # 添加原问题照片
    if issue_images:
        content_parts.append({"type": "text", "text": "\n## 原问题照片："})
        for img in issue_images:
            if img:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img}"}
                })

    # 添加整改照片
    content_parts.append({"type": "text", "text": "\n## 整改后照片："})
    for img in rect_images:
        if img:
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img}"}
            })

    try:
        import time as _time
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
            start = _time.time()
            response = await client.post(
                f"{settings.DASHSCOPE_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "qwen3.5-plus",  # 原生多模态，图文推理能力优于 qwen-vl-plus
                    "messages": [
                        {
                            "role": "system",
                            "content": """你是专业的物业品质检查整改核查专家。你必须客观、严谨地分析整改材料，输出必须是合法的JSON格式。

【核心判定逻辑】
整改是否合格，采用"水印照片+整改说明"双通道验证：
- 通道一（照片核查）：水印有效 + 问题已实际修复 → 通过
- 通道二（说明核查）：整改说明清晰完整、逻辑合理 → 通过（适用于管理性/程序性问题，无法拍照验证的场景）
- 两种方式满足任一要求，且不存在驳回条件时，即可判定通过
- 严重问题（如安全隐患）必须通过照片验证，说明不能替代照片

【判定优先级规则】
1. 水印无效时，仍可依据整改说明判定是否通过（照片非唯一途径）
2. 严重程度为"严重"的问题，照片验证为必须项，说明不能替代
3. 置信度≥85分时，suggestion直接输出"通过"
4. 置信度在50-84分之间时，suggestion必须输出"人工复核"，不得输出"通过"或"驳回"
5. 置信度<50分时，suggestion直接输出"驳回"
6. 发现临时遮挡、表面处理等非根本性整改时，应判定为不合格"""
                        },
                        {"role": "user", "content": content_parts}
                    ],
                    "temperature": 0.1,
                    "enable_thinking": False
                }
            )

        if response.status_code != 200:
            try:
                err_body = response.json()
                err_msg = err_body.get("error", {}).get("message", response.text[:300])
            except Exception:
                err_msg = response.text[:300]
            logger.error(f"DashScope API {response.status_code}: {err_msg}")
            return _default_result(False, f"API调用失败({response.status_code}): {err_msg}")

        result = response.json()
        duration = int((_time.time() - start) * 1000)
        # 记录 LLM 用量
        try:
            from core.llm_client import _log_llm_usage
            _log_llm_usage("qwen3.5-plus", "rectification_check", result, duration)
        except Exception:
            pass  # 日志失败不影响主流程

        content = result["choices"][0]["message"]["content"]

        # 解析 JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        ai_result = json.loads(content.strip())

        # 确保 suggestion 标准化（支持三种值：通过/驳回/人工复核）
        suggestion = ai_result.get("suggestion", "驳回")
        if "人工复核" in suggestion:
            ai_result["suggestion"] = "人工复核"
        elif "通过" in suggestion and "驳回" not in suggestion:
            ai_result["suggestion"] = "通过"
        else:
            ai_result["suggestion"] = "驳回"

        # Jev 交叉验证：判断模型复核视觉模型结论（shadow 仅记录 / active 参与路由），失败静默跳过
        try:
            from core.jev_client import jev_available, jev_system_one
            if jev_available():
                jev_answers = await jev_system_one(
                    _build_jev_state(
                        issue_description, issue_severity, issue_location,
                        rectification_note, expected_location, ai_result
                    ),
                    {
                        "verdict_correct": {
                            "type": "noul",
                            "instructions": "视觉模型的核查结论正确，该整改应按该结论处置",
                        },
                        "independent": {
                            "type": "choice",
                            "instructions": "仅依据上述文字材料，独立判断该整改应如何处置",
                            "criteria": {
                                "通过": "整改合格，证据充分",
                                "驳回": "整改不合格或证据明显矛盾",
                                "人工复核": "证据不足或存在疑点，需人工判断",
                            },
                        },
                    },
                    call_type="jev_rectification",
                )
                if jev_answers:
                    alt = jev_answers.get("independent", {}).get("choice")
                    ai_result["jev"] = {
                        "verdict_p": jev_answers.get("verdict_correct", {}).get("noul"),
                        "alt": alt,
                        "alt_probs": jev_answers.get("independent", {}).get("probabilities"),
                        "agreement": alt in (None, ai_result.get("suggestion")),
                        "model": settings.JEV_MODEL,
                    }
                    logger.info(
                        f"Jev 交叉验证: suggestion={ai_result.get('suggestion')}, "
                        f"verdict_p={ai_result['jev']['verdict_p']}, alt={alt}"
                    )
        except Exception as e:
            logger.warning(f"Jev 交叉验证失败（不影响核查结果）: {e}")

        return ai_result

    except json.JSONDecodeError:
        return _default_result(False, "AI返回格式解析失败")
    except Exception as e:
        return _default_result(False, f"AI核查异常: {str(e)}")


def _build_jev_state(issue_description: str, issue_severity: str, issue_location: str,
                     rectification_note: str, expected_location: str,
                     ai_result: Dict[str, Any]) -> str:
    """构造整改复核 Jev state：文字材料 + 视觉模型核查摘要（Jev 不能看图，视觉证据靠文字转述）"""
    return (
        "物业品质检查整改复核交叉验证。\n"
        f"【原问题】[{issue_severity}] {issue_description}（位置：{issue_location or '未指定'}）\n"
        f"【整改说明】{rectification_note or '无说明'}（预期地点：{expected_location or '未指定'}）\n"
        "【视觉模型核查摘要】\n"
        f"- 照片核查：{'有效' if ai_result.get('photo_valid') else '无效'}；{ai_result.get('photo_info', '')}\n"
        f"- 说明核查：{'合格' if ai_result.get('note_qualified') else '不合格'}；{ai_result.get('note_info', '')}\n"
        f"- 整改深度：{ai_result.get('rectification_depth', '')}\n"
        f"- 综合分析：{(ai_result.get('analysis') or '')[:1500]}\n"
        f"【视觉模型结论】{ai_result.get('suggestion')}（自报置信度{ai_result.get('confidence_score')}）"
    )


def _encode_image(file_path: str, max_size: int = 1024, quality: int = 75) -> Optional[str]:
    """将图片文件压缩后编码为 base64（避免原始照片过大导致 API 400）"""
    import os
    from io import BytesIO
    from PIL import Image

    if not os.path.exists(file_path):
        return None

    try:
        img = Image.open(file_path)
        # 转换 RGBA/P 为 RGB
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # 等比缩放，长边不超过 max_size
        w, h = img.size
        if max(w, h) > max_size:
            ratio = max_size / max(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as e:
        # 回退：直接读取原始文件
        try:
            with open(file_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            return None


def _default_result(qualified: bool, reason: str) -> Dict[str, Any]:
    """生成默认结果（AI调用失败时使用）"""
    return {
        "photo_valid": False,
        "photo_info": "",
        "note_qualified": qualified,
        "note_info": "",
        "confidence_score": 0,
        "rectification_depth": "无法判断",
        "analysis": f"AI核查未执行: {reason}",
        "suggestion": "驳回"
    }
