"""
系统设置 API
管理 AI 模型 API KEY 等运行时配置
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models.models import User
from api.deps import check_role
from core.settings_service import get_api_keys, update_api_key
from core.logger import get_logger

logger = get_logger("settings_api")
router = APIRouter()


# ============== 请求/响应模型 ==============

class ApiKeyItem(BaseModel):
    name: str
    display_name: str
    masked_value: str
    is_set: bool
    updated_at: Optional[str] = None


class ApiKeyListResponse(BaseModel):
    keys: List[ApiKeyItem]


class UpdateApiKeyRequest(BaseModel):
    key_name: str
    new_value: str


class UpdateApiKeyResponse(BaseModel):
    name: str
    display_name: str
    masked_value: str
    is_set: bool


# ============== API 端点 ==============

@router.get("/api-keys", response_model=ApiKeyListResponse, summary="获取 API KEY 列表（脱敏）")
async def api_get_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role(["admin"]))
):
    """获取所有 AI 模型 API KEY 的脱敏信息，仅管理员可访问"""
    keys = get_api_keys(db)
    return {"keys": keys}


@router.put("/api-keys", response_model=UpdateApiKeyResponse, summary="更新 API KEY")
async def api_update_api_key(
    request: UpdateApiKeyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role(["admin"]))
):
    """更新指定的 API KEY，立即生效，仅管理员可访问"""
    try:
        result = update_api_key(db, request.key_name, request.new_value, current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
