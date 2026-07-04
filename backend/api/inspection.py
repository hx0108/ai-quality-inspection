"""
检查记录 API
模块检查录入、问题记录、照片上传
"""
import os
import json
import uuid as _uuid
import threading
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func

from database import get_db
from models.models import User, InspectionTask, TaskAssignment, InspectionRecord, Issue, Photo
from api.deps import get_current_user, check_role, get_user_project_filter, get_user_project_ids
from config import settings

router = APIRouter()


def _gen_id(prefix: str) -> str:
    """生成唯一ID，格式: {PREFIX}-{YYYYMMDD}-{uuid8}"""
    today = datetime.now().strftime("%Y%m%d")
    short = _uuid.uuid4().hex[:8]
    return f"{prefix}-{today}-{short}"


def _validate_image_content(content: bytes) -> bool:
    """通过文件头 magic bytes 校验真实图片类型"""
    if len(content) < 4:
        return False
    signatures = [b'\xff\xd8\xff', b'\x89PNG', b'GIF8']
    return any(content[:len(sig)] == sig for sig in signatures)


def _verify_watermark_hash(meta: dict, content: bytes):
    """
    校验水印签名（防篡改）
    前端生成方式: HMAC-SHA256(lat|lng|time|name + 图片前8KB, secret)
    如果前端没传 hash 或定位失败则跳过校验（不阻塞上传）
    """
    import hashlib, hmac as _hmac
    wm_hash = meta.get("watermark_hash")
    if not wm_hash:
        return  # 非水印照片，跳过

    lat = meta.get("latitude", "")
    lng = meta.get("longitude", "")
    cap_time = meta.get("capture_time", "")
    inspector = meta.get("inspector_name", "")

    # 构造签名原文
    payload = f"{lat}|{lng}|{cap_time}|{inspector}".encode()
    payload += content[:8192]  # 取图片前 8KB 参与签名

    expected = _hmac.new(
        settings.SECRET_KEY.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    if wm_hash != expected:
        import logging
        logging.getLogger("inspection").warning(
            f"Photo watermark hash mismatch: expected={expected[:16]}... got={wm_hash[:16]}..."
        )


def _migrate_data_json_keys(record: InspectionRecord, standard_type: str) -> bool:
    """迁移和修复 data_json 中的检查项数据

    1. 移除错误添加的 dc/fdc 前缀（还原为原始格式 如 客户-038）
    2. 检测模板项数不一致时，补齐缺失的检查项为 checked 状态

    返回 True 如果发生了修改（需要 commit）
    """
    if not record.data_json:
        return False

    data = json.loads(record.data_json)
    items_map = data.get("items", {})
    if not items_map:
        return False

    changed = False

    # 1. 移除 dc/fdc 前缀：fdc客户-001 → 客户-001, dc安全-001 → 安全-001
    needs_prefix_removal = any(
        (key.startswith("dc") or key.startswith("fdc")) and "-" in key
        for key in items_map.keys()
    )
    if needs_prefix_removal:
        new_items = {}
        for key, value in items_map.items():
            if key.startswith("fdc") and "-" in key:
                new_key = key[3:]  # 去掉 fdc
                new_items[new_key] = value
            elif key.startswith("dc") and "-" in key:
                new_key = key[2:]  # 去掉 dc
                new_items[new_key] = value
            else:
                new_items[key] = value
        items_map = new_items
        data["items"] = items_map
        changed = True

    # 2. 检测模板项数不一致：data_json 的项数少于模板项数
    #    场景：之前前端加载了标准模板（58项）保存，但实际是简化版任务（63项）
    #    补齐缺失的检查项为 pending 状态（未检查），不能默认为合格
    from api.tasks import load_template_items
    template_items = load_template_items(record.module_name, standard_type)
    if template_items and len(items_map) > 0 and len(items_map) < len(template_items):
        missing_count = 0
        for tmpl in template_items:
            if tmpl["item_id"] not in items_map:
                items_map[tmpl["item_id"]] = {
                    "status": "pending",
                    "qualified": False
                }
                missing_count += 1
        if missing_count > 0:
            data["items"] = items_map
            changed = True

    if changed:
        record.data_json = json.dumps(data, ensure_ascii=False)
    return changed


# ==================== 权限检查 ====================
def _check_record_access(record: InspectionRecord, current_user: User, db: Session):
    """检查用户是否有权操作此检查记录

    允许操作的条件（满足其一即可）：
    1. 用户是记录的创建者（inspector_id）
    2. 用户是 admin 或 site_supervisor
    3. 用户被分配了该任务中的该模块（TaskAssignment）
    4. 用户是 field_supervisor/project_staff 且关联项目匹配
    """
    if record.inspector_id == current_user.id:
        return
    if current_user.role in ("admin", "site_supervisor"):
        return
    # 检查是否有任务模块分配
    assignment = db.query(TaskAssignment).filter(
        TaskAssignment.task_id == record.task_id,
        TaskAssignment.module_name == record.module_name,
        TaskAssignment.inspector_id == current_user.id
    ).first()
    if assignment:
        return
    # field_supervisor / project_staff 检查项目归属
    if current_user.role in ("field_supervisor", "project_staff"):
        allowed_ids = get_user_project_ids(current_user, db)
        if allowed_ids and record.project_id in allowed_ids:
            return
    raise HTTPException(status_code=403, detail="无权限操作此记录")


# ==================== 请求/响应模型 ====================
class RecordCreate(BaseModel):
    task_id: str
    module_name: str


class IssueCreate(BaseModel):
    item_id: str
    item_name: Optional[str] = None
    description: str
    location: Optional[str] = None
    severity: str = "一般"


class ItemUpdate(BaseModel):
    status: str  # checked / skipped
    issue_description: Optional[str] = None


class IssueUpdate(BaseModel):
    description: Optional[str] = None
    severity: Optional[str] = None


# ==================== API 端点 ====================
@router.post("", summary="创建模块检查记录")
async def create_record(
    request: RecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建模块检查记录
    - 检查员开始检查某个模块时调用
    """
    # 验证任务存在
    task = db.query(InspectionTask).filter(InspectionTask.task_id == request.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 验证模块已分配给当前用户
    assignment = db.query(TaskAssignment).filter(
        TaskAssignment.task_id == request.task_id,
        TaskAssignment.module_name == request.module_name,
        TaskAssignment.inspector_id == current_user.id
    ).first()

    if not assignment and current_user.role not in ["admin", "site_supervisor", "field_supervisor"]:
        raise HTTPException(status_code=403, detail="该模块未分配给您")

    # 检查该模块是否已有记录（同一任务同一模块共享一条记录）
    existing = db.query(InspectionRecord).filter(
        InspectionRecord.task_id == request.task_id,
        InspectionRecord.module_name == request.module_name
    ).first()

    if existing:
        return {
            "message": "记录已存在",
            "record_id": existing.record_id,
            "status": existing.status
        }

    # 生成记录ID（UUID，无冲突）
    record_id = _gen_id("REC")

    # 创建记录
    record = InspectionRecord(
        record_id=record_id,
        task_id=request.task_id,
        project_id=task.project_id,
        module_name=request.module_name,
        inspector_id=current_user.id,
        check_date=task.check_date,
        status="in_progress"
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "message": "记录创建成功",
        "record_id": record.record_id,
        "status": record.status
    }


def _generate_photo_sign(photo_id: str) -> dict:
    """生成照片访问的短期签名参数（5分钟有效）"""
    import hashlib, time as _time
    expires = int(_time.time()) + 300  # 5分钟
    raw = f"{photo_id}:{expires}:{settings.SECRET_KEY}"
    sign = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return {"sign": sign, "expires": str(expires)}


def _verify_photo_sign(photo_id: str, sign: str, expires: str) -> bool:
    """验证照片访问签名"""
    import hashlib, time as _time
    try:
        if int(_time.time()) > int(expires):
            return False
        raw = f"{photo_id}:{expires}:{settings.SECRET_KEY}"
        expected = hashlib.sha256(raw.encode()).hexdigest()[:24]
        return sign == expected
    except (ValueError, TypeError):
        return False


@router.get("/photos/{photo_id}/sign", summary="获取照片签名URL")
async def get_photo_sign(
    photo_id: str,
    current_user: User = Depends(get_current_user)
):
    """为指定照片生成短期签名URL参数（5分钟有效）"""
    sign_data = _generate_photo_sign(photo_id)
    return {"photo_id": photo_id, **sign_data}


@router.post("/photos/batch-sign", summary="批量获取照片签名URL")
async def batch_get_photo_sign(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    批量获取照片签名URL（一次请求签发多张照片）
    请求体: {"photo_ids": ["PHO-xxx", "PHO-yyy", ...]}
    返回: {"signs": [{"photo_id": "...", "sign": "...", "expires": "..."}, ...]}
    """
    body = await request.json()
    photo_ids = body.get("photo_ids", [])
    if not photo_ids or len(photo_ids) > 50:
        raise HTTPException(status_code=400, detail="photo_ids不能为空且最多50个")
    signs = []
    for pid in photo_ids:
        sign_data = _generate_photo_sign(pid)
        signs.append({"photo_id": pid, **sign_data})
    return {"signs": signs}


@router.get("/photos/{photo_id}", summary="获取照片")
async def get_photo(
    photo_id: str,
    sign: Optional[str] = None,
    expires: Optional[str] = None,
    token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取照片文件
    支持两种认证方式:
    1. 短期签名: ?sign=xxx&expires=xxx（5分钟有效，推荐）
    2. JWT token: ?token=xxx（24小时有效，兼容旧前端）
    """
    from fastapi.responses import FileResponse

    authenticated = False

    # 方式1: 短期签名验证（推荐）
    if sign and expires and _verify_photo_sign(photo_id, sign, expires):
        authenticated = True

    # 方式2: JWT token（兼容旧方式）
    if not authenticated and token:
        from jose import jwt as _jwt
        try:
            payload = _jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            username = payload.get("sub")
            from models.models import User as UserModel
            user = db.query(UserModel).filter(UserModel.username == username).first()
            if user:
                authenticated = True
        except Exception:
            pass

    if not authenticated:
        raise HTTPException(status_code=401, detail="未登录或签名已过期")

    photo = db.query(Photo).filter(Photo.photo_id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")

    if not os.path.exists(photo.file_path):
        raise HTTPException(status_code=404, detail="照片文件不存在")

    # 安全校验：确保文件路径在 PHOTOS_DIR 内（防止路径遍历）
    real_path = os.path.realpath(photo.file_path)
    allowed_dir = os.path.realpath(str(settings.PHOTOS_DIR))
    if not real_path.startswith(allowed_dir):
        raise HTTPException(status_code=403, detail="禁止访问")

    return FileResponse(
        photo.file_path,
        media_type="image/jpeg",
        filename=photo.file_name
    )


@router.get("/{record_id}", summary="获取检查记录详情")
async def get_record_detail(
    record_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取检查记录详情，含所有检查项"""
    record = db.query(InspectionRecord).options(
        selectinload(InspectionRecord.issues).selectinload(Issue.photos),
        joinedload(InspectionRecord.task).joinedload(InspectionTask.project),
        joinedload(InspectionRecord.inspector),
    ).filter(InspectionRecord.record_id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 权限校验
    _check_record_access(record, current_user, db)

    # 获取问题列表
    issues = db.query(Issue).filter(Issue.record_id == record_id).all()

    # 构建检查项状态
    issues_by_item = {}
    for issue in issues:
        if issue.item_id not in issues_by_item:
            issues_by_item[issue.item_id] = []
        issues_by_item[issue.item_id].append({
            "issue_id": issue.issue_id,
            "description": issue.description,
            "severity": issue.severity,
            "location": issue.location,
            "photos": [
                {
                    "photo_id": p.photo_id,
                    "file_path": p.file_path,
                    "latitude": p.latitude,
                    "longitude": p.longitude,
                    "address": p.address,
                    "capture_time": p.capture_time.isoformat() if p.capture_time else None,
                    "inspector_name": p.inspector_name,
                }
                for p in issue.photos
            ]
        })

    return {
        "record_id": record.record_id,
        "task_id": record.task_id,
        "module_name": record.module_name,
        "project_id": record.project_id,
        "project_name": record.task.project.name if record.task and record.task.project else "",
        "project_address": record.task.project.address if record.task and record.task.project else "",
        "check_date": record.check_date,
        "standard_type": record.task.standard_type if record.task else "diecheng",
        "status": record.status,
        "inspector_id": record.inspector_id,
        "inspector_name": record.inspector.real_name if record.inspector else "",
        "issues": issues_by_item,
        "item_statuses": json.loads(record.data_json).get("items", {}) if record.data_json else {},
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat()
    }


@router.post("/{record_id}/issues", summary="记录问题点")
async def create_issue(
    record_id: str,
    request: IssueCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """记录问题点"""
    # 验证记录存在
    record = db.query(InspectionRecord).filter(InspectionRecord.record_id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 验证权限
    _check_record_access(record, current_user, db)

    # 生成问题ID（UUID）
    issue_id = _gen_id("ISS")

    # 创建问题
    issue = Issue(
        issue_id=issue_id,
        record_id=record_id,
        module_name=record.module_name,
        item_id=request.item_id,
        item_name=request.item_name,
        description=request.description,
        location=request.location,
        severity=request.severity
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)

    return {
        "message": "问题记录成功",
        "issue_id": issue.issue_id
    }


@router.post("/{record_id}/issues/{issue_id}/photos", summary="上传问题照片")
async def upload_photo(
    record_id: str,
    issue_id: str,
    file: UploadFile = File(...),
    metadata: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传问题照片
    支持水印相机元数据：metadata JSON 字符串包含 { latitude, longitude, address, capture_time, inspector_name, watermark_hash }
    """
    # 验证问题和记录
    issue = db.query(Issue).filter(
        Issue.issue_id == issue_id,
        Issue.record_id == record_id
    ).first()
    if not issue:
        raise HTTPException(status_code=404, detail="问题不存在")

    # 验证权限
    record = db.query(InspectionRecord).filter(InspectionRecord.record_id == record_id).first()
    _check_record_access(record, current_user, db)

    # 验证文件类型
    if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
        raise HTTPException(status_code=400, detail="只支持 jpg/png/gif 格式")

    # 读取文件内容并校验大小
    content = await file.read()
    if len(content) > settings.MAX_PHOTO_SIZE:
        raise HTTPException(status_code=400, detail=f"文件大小超过限制({settings.MAX_PHOTO_SIZE // 1024 // 1024}MB)")
    if not _validate_image_content(content):
        raise HTTPException(status_code=400, detail="不支持的图片格式或文件已损坏")

    # 解析水印元数据
    photo_meta = {}
    if metadata:
        try:
            photo_meta = json.loads(metadata)
        except (json.JSONDecodeError, TypeError):
            photo_meta = {}

    # 校验水印签名（防篡改）
    _verify_watermark_hash(photo_meta, content)

    # 生成文件名（UUID，无冲突）
    file_ext = os.path.splitext(file.filename)[1]
    photo_id = _gen_id("PHO")
    filename = f"{photo_id}{file_ext}"

    # 创建保存目录
    save_dir = settings.PHOTOS_DIR / record_id
    save_dir.mkdir(parents=True, exist_ok=True)

    # 保存文件
    file_path = save_dir / filename
    with open(file_path, "wb") as f:
        f.write(content)

    # 解析拍摄时间
    capture_time = None
    if photo_meta.get("capture_time"):
        try:
            capture_time = datetime.fromisoformat(photo_meta["capture_time"])
        except (ValueError, TypeError):
            capture_time = None

    # 创建照片记录（含水印元数据）
    photo = Photo(
        photo_id=photo_id,
        issue_id=issue_id,
        file_path=str(file_path),
        file_name=filename,
        photo_type="问题照片",
        latitude=photo_meta.get("latitude"),
        longitude=photo_meta.get("longitude"),
        address=photo_meta.get("address"),
        capture_time=capture_time,
        inspector_name=photo_meta.get("inspector_name"),
        watermark_hash=photo_meta.get("watermark_hash"),
    )
    db.add(photo)
    db.commit()

    return {
        "message": "照片上传成功",
        "photo_id": photo.photo_id,
        "file_path": f"/api/v1/photos/{photo.photo_id}"
    }


@router.put("/{record_id}/issues/{issue_id}", summary="更新问题")
async def update_issue(
    record_id: str,
    issue_id: str,
    request: IssueUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新问题描述和严重程度"""
    issue = db.query(Issue).filter(
        Issue.issue_id == issue_id,
        Issue.record_id == record_id
    ).first()
    if not issue:
        raise HTTPException(status_code=404, detail="问题不存在")

    record = db.query(InspectionRecord).filter(InspectionRecord.record_id == record_id).first()
    _check_record_access(record, current_user, db)

    if record.status == "completed":
        raise HTTPException(status_code=400, detail="检查已完成，无法修改")

    if request.description is not None:
        issue.description = request.description
    if request.severity is not None:
        issue.severity = request.severity
    db.commit()

    return {"message": "更新成功", "issue_id": issue_id}


@router.delete("/{record_id}/issues/{issue_id}", summary="删除问题")
async def delete_issue(
    record_id: str,
    issue_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除问题及其照片，将检查项恢复为待检查状态"""
    issue = db.query(Issue).filter(
        Issue.issue_id == issue_id,
        Issue.record_id == record_id
    ).first()
    if not issue:
        raise HTTPException(status_code=404, detail="问题不存在")

    record = db.query(InspectionRecord).filter(InspectionRecord.record_id == record_id).first()
    _check_record_access(record, current_user, db)

    if record.status == "completed":
        raise HTTPException(status_code=400, detail="检查已完成，无法修改")

    # 删除照片文件
    photos = db.query(Photo).filter(Photo.issue_id == issue_id).all()
    for photo in photos:
        if os.path.exists(photo.file_path):
            os.remove(photo.file_path)
    db.query(Photo).filter(Photo.issue_id == issue_id).delete()

    # 删除问题
    item_id = issue.item_id
    db.delete(issue)

    # 迁移旧格式 keys
    task = db.query(InspectionTask).filter(InspectionTask.task_id == record.task_id).first()
    standard_type = task.standard_type if task else "diecheng"
    if _migrate_data_json_keys(record, standard_type):
        db.commit()

    # 恢复 data_json 中该检查项为 pending
    data = json.loads(record.data_json) if record.data_json else {}
    items_map = data.get("items", {})
    if item_id in items_map:
        items_map[item_id] = {"status": "pending", "qualified": False}
        data["items"] = items_map
        record.data_json = json.dumps(data, ensure_ascii=False)

    db.commit()

    return {"message": "问题已删除", "issue_id": issue_id, "item_id": item_id}


@router.delete("/{record_id}/issues/{issue_id}/photos/{photo_id}", summary="删除问题照片")
async def delete_photo(
    record_id: str,
    issue_id: str,
    photo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除单张问题照片"""
    photo = db.query(Photo).filter(
        Photo.photo_id == photo_id,
        Photo.issue_id == issue_id
    ).first()
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")

    record = db.query(InspectionRecord).filter(InspectionRecord.record_id == record_id).first()
    _check_record_access(record, current_user, db)

    if record.status == "completed":
        raise HTTPException(status_code=400, detail="检查已完成，无法修改")

    if os.path.exists(photo.file_path):
        os.remove(photo.file_path)
    db.delete(photo)
    db.commit()

    return {"message": "照片已删除"}


class BatchItemUpdate(BaseModel):
    item_ids: List[str] = []
    status: str  # checked / skipped


@router.put("/{record_id}/items/batch", summary="批量更新检查项状态")
async def batch_update_items(
    record_id: str,
    request: BatchItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量更新检查项 — 用于"全部合格"一键操作"""
    record = db.query(InspectionRecord).filter(InspectionRecord.record_id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    _check_record_access(record, current_user, db)

    # 迁移旧格式 data_json keys（加 standard_type 前缀）
    task = db.query(InspectionTask).filter(InspectionTask.task_id == record.task_id).first()
    standard_type = task.standard_type if task else "diecheng"
    if _migrate_data_json_keys(record, standard_type):
        db.commit()

    # 解析 data_json
    data = json.loads(record.data_json) if record.data_json else {}
    items_map = data.get("items", {})

    qualified = request.status == "checked"

    # 如果 item_ids 为空，获取模板中所有项
    if not request.item_ids:
        from api.tasks import load_template_items
        task = db.query(InspectionTask).filter(InspectionTask.task_id == record.task_id).first()
        standard_type = task.standard_type if task else "diecheng"
        template_items = load_template_items(record.module_name, standard_type)
        target_ids = [
            item["item_id"] for item in template_items
            if items_map.get(item["item_id"], {}).get("status") != "checked"
        ]
    else:
        target_ids = request.item_ids

    for item_id in target_ids:
        items_map[item_id] = {
            "status": request.status,
            "qualified": qualified
        }

    data["items"] = items_map
    record.data_json = json.dumps(data, ensure_ascii=False)
    db.commit()

    return {
        "message": f"已更新 {len(target_ids)} 项",
        "updated_count": len(target_ids),
        "status": request.status
    }


@router.put("/{record_id}/items/{item_id}", summary="更新检查项状态")
async def update_item(
    record_id: str,
    item_id: str,
    request: ItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新检查项状态（checked/skipped），持久化到 data_json"""
    record = db.query(InspectionRecord).filter(InspectionRecord.record_id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    _check_record_access(record, current_user, db)

    # 解析 data_json
    data = json.loads(record.data_json) if record.data_json else {}
    items_map = data.get("items", {})

    qualified = request.status == "checked" and not request.issue_description

    items_map[item_id] = {
        "status": request.status,
        "qualified": qualified
    }
    data["items"] = items_map
    record.data_json = json.dumps(data, ensure_ascii=False)

    # 如果有问题描述，创建 Issue（UUID）
    if request.status == "checked" and request.issue_description:
        issue_id = _gen_id("ISS")
        issue = Issue(
            issue_id=issue_id,
            record_id=record_id,
            module_name=record.module_name,
            item_id=item_id,
            item_name=request.issue_description[:50],
            description=request.issue_description,
            severity="一般"
        )
        db.add(issue)

    db.commit()

    return {
        "message": "状态更新成功",
        "item_id": item_id,
        "status": request.status,
        "qualified": qualified
    }


@router.post("/{record_id}/batch-sync", summary="批量同步离线数据")
async def batch_sync_offline(
    record_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    批量同步离线数据 — 一次性上传多个问题+照片
    请求格式: multipart/form-data
      - metadata: JSON字符串, { issues: [{ temp_issue_id, item_id, ... }] }
      - photo_{temp_issue_id}_{index}: 照片文件
    """
    # 验证记录存在
    record = db.query(InspectionRecord).filter(InspectionRecord.record_id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    _check_record_access(record, current_user, db)

    if record.status == "completed":
        raise HTTPException(status_code=400, detail="检查已完成，无法同步")

    # 从 request 手动解析 multipart form
    form = await request.form()
    metadata = form.get("metadata")
    if not metadata:
        raise HTTPException(status_code=400, detail="缺少 metadata 字段")

    # 解析 metadata
    try:
        meta_str = metadata if isinstance(metadata, str) else await metadata.read()
        if isinstance(meta_str, bytes):
            meta_str = meta_str.decode('utf-8')
        meta = json.loads(meta_str)
        issues_data = meta.get("issues", [])
    except (json.JSONDecodeError, AttributeError) as e:
        raise HTTPException(status_code=400, detail="metadata 格式错误，请检查数据格式")

    if not issues_data:
        return {"results": [], "synced_count": 0, "conflict_count": 0}

    # 读取所有上传的文件（动态文件名）
    file_map = {}
    for key, value in form.multi_items():
        if key.startswith("photo_") and hasattr(value, 'read'):
            file_map[key] = value

    # 解析 data_json
    data = json.loads(record.data_json) if record.data_json else {}
    items_map = data.get("items", {})

    results = []
    for issue_info in issues_data:
        temp_issue_id = issue_info.get("temp_issue_id", "")
        item_id = issue_info.get("item_id", "")
        item_name = issue_info.get("item_name", "")
        description = issue_info.get("description", "")
        severity = issue_info.get("severity", "一般")
        item_status = issue_info.get("item_status", "checked")

        # 冲突检测: 是否已有同一 item 的问题
        existing = db.query(Issue).filter(
            Issue.record_id == record_id,
            Issue.item_id == item_id
        ).first()

        if existing:
            results.append({
                "temp_issue_id": temp_issue_id,
                "status": "conflict",
                "reason": "该检查项已有问题记录"
            })
            continue

        # 创建 Issue
        issue_id = _gen_id("ISS")
        issue = Issue(
            issue_id=issue_id,
            record_id=record_id,
            module_name=record.module_name,
            item_id=item_id,
            item_name=item_name,
            description=description,
            severity=severity
        )
        db.add(issue)
        db.flush()  # 确保 issue 写入以便关联 photo

        # 保存照片
        photo_ids = []
        photo_idx = 0
        while True:
            file_key = f"photo_{temp_issue_id}_{photo_idx}"
            if file_key not in file_map:
                break

            upload_file = file_map[file_key]

            # 验证文件类型
            filename = upload_file.filename or f"photo_{photo_idx}.jpg"
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                photo_idx += 1
                continue

            # 读取内容并校验大小和格式
            content = await upload_file.read()
            if len(content) > settings.MAX_PHOTO_SIZE:
                photo_idx += 1
                continue  # 跳过超大文件
            if not _validate_image_content(content):
                photo_idx += 1
                continue  # 跳过非图片文件

            # 生成文件名
            file_ext = os.path.splitext(filename)[1]
            photo_id = _gen_id("PHO")
            save_filename = f"{photo_id}{file_ext}"

            # 保存到磁盘
            save_dir = settings.PHOTOS_DIR / record_id
            save_dir.mkdir(parents=True, exist_ok=True)
            file_path = save_dir / save_filename

            with open(file_path, "wb") as f:
                f.write(content)

            # 解析该照片的水印元数据（从 issue_info 的 photo_metas 列表中取）
            photo_metas = issue_info.get("photo_metas", [])
            photo_meta = photo_metas[photo_idx] if photo_idx < len(photo_metas) else {}

            # 校验水印签名
            _verify_watermark_hash(photo_meta, content)

            # 解析拍摄时间
            capture_time = None
            if photo_meta.get("capture_time"):
                try:
                    capture_time = datetime.fromisoformat(photo_meta["capture_time"])
                except (ValueError, TypeError):
                    capture_time = None

            # 创建 Photo 记录（含水印元数据）
            photo = Photo(
                photo_id=photo_id,
                issue_id=issue_id,
                file_path=str(file_path),
                file_name=save_filename,
                photo_type="问题照片",
                latitude=photo_meta.get("latitude"),
                longitude=photo_meta.get("longitude"),
                address=photo_meta.get("address"),
                capture_time=capture_time,
                inspector_name=photo_meta.get("inspector_name"),
                watermark_hash=photo_meta.get("watermark_hash"),
            )
            db.add(photo)
            photo_ids.append(photo_id)
            photo_idx += 1

        # 更新 data_json 中 item 状态
        items_map[item_id] = {
            "status": item_status,
            "qualified": False  # 有问题项不合格
        }
        data["items"] = items_map
        record.data_json = json.dumps(data, ensure_ascii=False)

        db.commit()  # 每条 issue 独立提交

        results.append({
            "temp_issue_id": temp_issue_id,
            "status": "created",
            "issue_id": issue_id,
            "photo_ids": photo_ids
        })

    synced_count = sum(1 for r in results if r["status"] == "created")
    conflict_count = sum(1 for r in results if r["status"] == "conflict")

    return {
        "results": results,
        "synced_count": synced_count,
        "conflict_count": conflict_count
    }


@router.put("/{record_id}/complete", summary="完成模块检查")
async def complete_record(
    record_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """标记模块检查完成"""
    record = db.query(InspectionRecord).filter(InspectionRecord.record_id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    _check_record_access(record, current_user, db)

    # 迁移旧格式 data_json keys（加 standard_type 前缀）
    task = db.query(InspectionTask).filter(InspectionTask.task_id == record.task_id).first()
    standard_type = task.standard_type if task else "diecheng"
    if _migrate_data_json_keys(record, standard_type):
        db.commit()

    # 检查所有检查项是否都已完成
    data = json.loads(record.data_json) if record.data_json else {}
    items_map = data.get("items", {})

    # 获取模板中所有检查项
    from api.tasks import load_template_items
    task = db.query(InspectionTask).filter(InspectionTask.task_id == record.task_id).first()
    standard_type = task.standard_type if task else "diecheng"
    template_items = load_template_items(record.module_name, standard_type)

    unchecked_items = []
    for tmpl in template_items:
        item_id = tmpl["item_id"]
        status = items_map.get(item_id, {}).get("status")
        if status != "checked":
            unchecked_items.append(tmpl.get("item_name", item_id))

    if unchecked_items:
        raise HTTPException(
            status_code=400,
            detail=f"还有 {len(unchecked_items)} 项检查未完成：{', '.join(unchecked_items)}"
        )

    record.status = "completed"
    record.updated_at = datetime.utcnow()
    db.commit()

    # === 自动为所有问题创建整改记录（批量查询优化） ===
    issues = db.query(Issue).filter(Issue.record_id == record_id).all()
    from models.models import Rectification
    issue_ids = [issue.issue_id for issue in issues]
    existing_rects = db.query(Rectification).filter(
        Rectification.issue_id.in_(issue_ids)
    ).all() if issue_ids else []
    existing_rect_map = {r.issue_id: r for r in existing_rects}

    # 计算整改截止日期 = 检查日期 + 30天
    from datetime import timedelta
    deadline = None
    if task and task.check_date:
        try:
            check_dt = datetime.strptime(task.check_date, "%Y-%m-%d")
            deadline = (check_dt + timedelta(days=30)).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass

    for issue in issues:
        if issue.issue_id not in existing_rect_map:
            rect = Rectification(
                rectification_id=_gen_id("RECT"),
                issue_id=issue.issue_id,
                record_id=record_id,
                task_id=record.task_id,
                status="pending",
                deadline=deadline
            )
            db.add(rect)
    db.commit()

    task_id = record.task_id

    # === 触发该模块的AI评分（无论是否最后一个模块）===
    # 评分完成后，_check_and_trigger_report 安全网会自动检测并触发 Agent 3
    from api.scoring import trigger_single_module_scoring_compat
    trigger_single_module_scoring_compat(task_id, record.module_name, record_id)

    # 检查是否所有已分配模块都完成（task 已在上方查询）
    all_modules_done = False
    if task:
        assigned_count = db.query(TaskAssignment).filter(
            TaskAssignment.task_id == task.task_id
        ).count()

        if assigned_count > 0:
            completed_count = db.query(InspectionRecord).filter(
                InspectionRecord.task_id == task.task_id,
                InspectionRecord.status == "completed"
            ).count()

            if completed_count >= assigned_count:
                all_modules_done = True

    return {
        "message": "模块检查完成",
        "record_id": record_id,
        "status": "completed",
        "all_modules_done": all_modules_done,
        "scoring_triggered": True
    }


@router.put("/{record_id}/recall", summary="退回模块（管理员）")
async def recall_module(
    record_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    退回已完成的模块，让检查人员重新填写。
    仅管理员/督导可操作。会清除评分、整改、问题记录，恢复模块为进行中状态。
    """
    # 权限校验
    if current_user.role not in ["admin", "site_supervisor"]:
        raise HTTPException(status_code=403, detail="仅管理员或督导可退回模块")

    record = db.query(InspectionRecord).filter(InspectionRecord.record_id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    if record.status != "completed":
        raise HTTPException(status_code=400, detail="只能退回已完成的模块")

    from models.models import Rectification, ScoringResult

    task_id = record.task_id
    module_name = record.module_name

    # 1. 删除该模块的整改记录（含整改照片）
    issues = db.query(Issue).filter(Issue.record_id == record_id).all()
    issue_ids = [i.issue_id for i in issues]

    if issue_ids:
        # 删除整改照片（磁盘文件 + 数据库）
        rects = db.query(Rectification).filter(Rectification.issue_id.in_(issue_ids)).all()
        for rect in rects:
            rect_photos = db.query(Photo).filter(
                Photo.issue_id == rect.issue_id,
                Photo.photo_type == "整改照片"
            ).all()
            for photo in rect_photos:
                if photo.file_path and os.path.exists(photo.file_path):
                    try:
                        os.remove(photo.file_path)
                    except Exception:
                        pass
                db.delete(photo)
        # 删除整改记录
        db.query(Rectification).filter(Rectification.issue_id.in_(issue_ids)).delete(synchronize_session=False)

    # 2. 删除评分结果
    db.query(ScoringResult).filter(
        ScoringResult.record_id == record_id,
        ScoringResult.module_name == module_name
    ).delete()

    # 3. 删除问题照片（磁盘文件 + 数据库）和问题记录
    for issue in issues:
        issue_photos = db.query(Photo).filter(
            Photo.issue_id == issue.issue_id,
            Photo.photo_type == "问题照片"
        ).all()
        for photo in issue_photos:
            if photo.file_path and os.path.exists(photo.file_path):
                try:
                    os.remove(photo.file_path)
                except Exception:
                    pass
            db.delete(photo)
    db.query(Issue).filter(Issue.record_id == record_id).delete()

    # 4. 重置 data_json 中所有检查项状态为 pending
    data = json.loads(record.data_json) if record.data_json else {}
    items_map = data.get("items", {})
    for item_id in items_map:
        items_map[item_id]["status"] = "pending"
        items_map[item_id]["qualified"] = False
    record.data_json = json.dumps(data, ensure_ascii=False)

    # 5. 恢复状态
    record.status = "in_progress"
    record.updated_at = datetime.utcnow()
    db.commit()

    # 6. 重算任务总分 + 修正任务状态
    try:
        from api.scoring import _compute_and_save_total_score, _invalidate_scoring_cache
        _compute_and_save_total_score(task_id)
        _invalidate_scoring_cache(task_id)
    except Exception:
        pass

    # 7. 修正任务状态：如果还有未完成的模块，任务应回到 in_progress
    task = db.query(InspectionTask).filter(InspectionTask.task_id == task_id).first()
    if task and task.status == "completed":
        assigned_count = db.query(TaskAssignment).filter(
            TaskAssignment.task_id == task_id
        ).count()
        if assigned_count > 0:
            completed_count = db.query(InspectionRecord).filter(
                InspectionRecord.task_id == task_id,
                InspectionRecord.status == "completed"
            ).count()
            # 统计有多少个不同的模块已完成（一个模块可能有多个检查员）
            completed_modules = set()
            completed_records = db.query(InspectionRecord.module_name).filter(
                InspectionRecord.task_id == task_id,
                InspectionRecord.status == "completed"
            ).all()
            for cr in completed_records:
                completed_modules.add(cr[0])

            assigned_modules = set()
            assigned = db.query(TaskAssignment.module_name).filter(
                TaskAssignment.task_id == task_id
            ).all()
            for a in assigned:
                assigned_modules.add(a[0])

            if completed_modules != assigned_modules:
                task.status = "in_progress"
                db.commit()

    return {
        "message": f"模块「{module_name}」已退回，检查人员可重新填写",
        "record_id": record_id,
        "module_name": module_name,
        "status": "in_progress"
    }


class RecallItemRequest(BaseModel):
    item_id: str


@router.put("/{record_id}/recall-item", summary="退回单个检查项（管理员）")
async def recall_item(
    record_id: str,
    body: RecallItemRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    退回模块中的单个检查项，让检查人员重新填写该项。
    仅管理员/督导可操作。会清除该项的评分、整改、问题记录。
    """
    if current_user.role not in ["admin", "site_supervisor"]:
        raise HTTPException(status_code=403, detail="仅管理员或督导可退回检查项")

    record = db.query(InspectionRecord).filter(InspectionRecord.record_id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    if record.status != "completed":
        raise HTTPException(status_code=400, detail="只能退回已完成模块中的检查项")

    from models.models import Rectification, ScoringResult

    item_id = body.item_id
    task_id = record.task_id
    module_name = record.module_name

    # 1. 删除该项的整改记录（含整改照片）
    issue = db.query(Issue).filter(
        Issue.record_id == record_id,
        Issue.item_id == item_id
    ).first()
    if issue:
        # 删除整改照片
        rects = db.query(Rectification).filter(Rectification.issue_id == issue.issue_id).all()
        for rect in rects:
            rect_photos = db.query(Photo).filter(
                Photo.issue_id == rect.issue_id,
                Photo.photo_type == "整改照片"
            ).all()
            for photo in rect_photos:
                if photo.file_path and os.path.exists(photo.file_path):
                    try:
                        os.remove(photo.file_path)
                    except Exception:
                        pass
                db.delete(photo)
        db.query(Rectification).filter(Rectification.issue_id == issue.issue_id).delete(synchronize_session=False)

        # 删除问题照片
        issue_photos = db.query(Photo).filter(
            Photo.issue_id == issue.issue_id,
            Photo.photo_type == "问题照片"
        ).all()
        for photo in issue_photos:
            if photo.file_path and os.path.exists(photo.file_path):
                try:
                    os.remove(photo.file_path)
                except Exception:
                    pass
            db.delete(photo)
        # 删除问题记录
        db.delete(issue)

    # 2. 删除该项的评分结果
    db.query(ScoringResult).filter(
        ScoringResult.record_id == record_id,
        ScoringResult.module_name == module_name,
        ScoringResult.item_id == item_id
    ).delete()

    # 3. 重置 data_json 中该项状态为 pending
    data = json.loads(record.data_json) if record.data_json else {}
    items_map = data.get("items", {})
    if item_id in items_map:
        items_map[item_id]["status"] = "pending"
        items_map[item_id]["qualified"] = False
        record.data_json = json.dumps(data, ensure_ascii=False)

    db.commit()

    # 4. 重算任务总分 + 清缓存
    try:
        from api.scoring import _compute_and_save_total_score, _invalidate_scoring_cache
        _compute_and_save_total_score(task_id)
        _invalidate_scoring_cache(task_id)
    except Exception:
        pass

    item_name = items_map.get(item_id, {}).get("item_name", item_id) if item_id in items_map else item_id

    return {
        "message": f"检查项「{item_name}」已退回，检查人员可重新填写",
        "record_id": record_id,
        "item_id": item_id,
        "item_name": item_name
    }
