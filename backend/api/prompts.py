"""
Prompt 版本管理 API
管理员在线查看、编辑 Prompt 模板
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from api.deps import check_role
from core.prompt_manager import prompt_manager

router = APIRouter(tags=["Prompt管理"])


class PromptUpdateRequest(BaseModel):
    template: str
    description: Optional[str] = ""


@router.get("/prompts", summary="列出所有Prompt模板")
def list_prompts(current_user=Depends(check_role(["admin"]))):
    """列出所有Prompt及其版本信息"""
    return {"prompts": prompt_manager.list_prompts()}


@router.get("/prompts/{prompt_key}", summary="获取Prompt详情")
def get_prompt_detail(
    prompt_key: str,
    current_user=Depends(check_role(["admin"]))
):
    """获取Prompt完整内容"""
    detail = prompt_manager.get_prompt_detail(prompt_key)
    if not detail:
        raise HTTPException(404, f"Prompt '{prompt_key}' 不存在")
    return detail


@router.put("/prompts/{prompt_key}", summary="更新Prompt")
def update_prompt(
    prompt_key: str,
    request: PromptUpdateRequest,
    current_user=Depends(check_role(["admin"]))
):
    """更新Prompt模板（自动创建新版本）"""
    result = prompt_manager.update_prompt(
        key=prompt_key,
        template=request.template,
        description=request.description,
        updated_by=current_user.id,
    )
    return {"status": "success", **result}


@router.post("/prompts/{prompt_key}/deactivate", summary="停用Prompt")
def deactivate_prompt(
    prompt_key: str,
    current_user=Depends(check_role(["admin"]))
):
    """停用Prompt（回退到代码默认值）"""
    success = prompt_manager.deactivate_prompt(prompt_key)
    if not success:
        raise HTTPException(404, f"Prompt '{prompt_key}' 不存在")
    return {"status": "success", "message": f"Prompt '{prompt_key}' 已停用"}


@router.post("/prompts/reload", summary="重新加载Prompt缓存")
def reload_prompts(current_user=Depends(check_role(["admin"]))):
    """手动刷新Prompt缓存"""
    prompt_manager.reload_cache()
    return {"status": "success", "message": "缓存已刷新"}
