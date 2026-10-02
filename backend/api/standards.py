"""
检查标准管理：导入（Word/Excel）/ 列表 / 模块查询 / 删除
内置标准（diecheng/feidiecheng/lizhi）来自 settings.STANDARDS；
自定义标准来自上传解析，落库 custom_standards 表 + 规范化模板 xlsx。
"""
import json
import logging
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from api.deps import get_current_user
from config import settings
from core import standard_parser
from core.standards import register_custom, unregister_custom
from database import get_db
from models.models import User
from models.standard import CustomStandard

logger = logging.getLogger(__name__)

router = APIRouter()

BUILTIN_TYPES = ("diecheng", "feidiecheng", "lizhi")
ALLOWED_EXT = (".xlsx", ".docx")


def _require_admin(current_user: User = Depends(get_current_user)):
    if getattr(current_user, "role", "") != "admin":
        raise HTTPException(status_code=403, detail="仅系统管理员可管理检查标准")
    return current_user


@router.post("/import", summary="导入检查标准（Word/Excel，AI 自动识别结构）")
async def import_standard(
    file: UploadFile = File(...),
    label: str = Form(""),
    scoring_model: str = Form("auto"),  # auto | point_cap | weighted_5pt
    db: Session = Depends(get_db),
    current_user: Any = Depends(_require_admin),
):
    filename = file.filename or "standard"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 或 .docx 格式的检查标准文件")

    # 落临时文件供解析
    import os
    import tempfile
    suffix = ext if ext else ".xlsx"
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        content = await file.read()
        with os.fdopen(tmp_fd, "wb") as f:
            f.write(content)

        # 1) 解析：Excel 先走确定性（规范工作簿），失败/Word 走 LLM
        parsed = None
        if suffix == ".xlsx":
            parsed = standard_parser.deterministic_parse_workbook(tmp_path)
            source_text = None
        if parsed is None:
            try:
                source_text = (
                    "\n\n".join(
                        f"[{sh['sheet']}]\n" + "\n".join("\t".join(r) for r in sh["rows"])
                        for sh in standard_parser.extract_workbook(tmp_path)
                    )
                    if suffix == ".xlsx"
                    else standard_parser.extract_docx(tmp_path)
                )
            except RuntimeError as e:
                raise HTTPException(status_code=500, detail=str(e))
            parsed = await standard_parser.parse_with_llm(source_text)
        if parsed is None:
            raise HTTPException(
                status_code=422,
                detail="无法识别该文件的标准结构。请确认内容包含模块划分与检查项，或改用系统模板格式后重试。",
            )
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    # 2) 计分模型定稿 + 权重/满分补齐
    if scoring_model in ("point_cap", "weighted_5pt"):
        parsed["scoring_model"] = scoring_model
    try:
        parsed = standard_parser.finalize(parsed)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # 3) 注册：写规范化模板 + 落库
    std_type = "custom_" + uuid.uuid4().hex[:8]
    template_file = standard_parser.write_normalized_template(std_type, parsed)

    modules_cfg = {}
    for m in parsed["modules"]:
        if parsed["scoring_model"] == "point_cap":
            role = m.get("role", "score")
            modules_cfg[m["name"]] = (
                {"max_score": m["max_score"] or 0, "role": "deduction"}
                if role == "deduction"
                else {"max_score": m["max_score"] or 25}
            )
        else:
            modules_cfg[m["name"]] = {"weight": m["weight"]}

    label = (label or "").strip() or filename.rsplit(".", 1)[0]
    row = CustomStandard(
        standard_type=std_type,
        label=label,
        scoring_model=parsed["scoring_model"],
        modules_json=json.dumps(modules_cfg, ensure_ascii=False),
        module_count=len(parsed["modules"]),
        items_total=parsed.get("items_total", 0),
        template_file=template_file,
        source_filename=filename,
        created_by=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    # 注册进运行时缓存，任务创建立即可用
    register_custom({
        "standard_type": std_type,
        "label": label,
        "scoring_model": parsed["scoring_model"],
        "modules": modules_cfg,
        "file": template_file,
    })

    summary = standard_parser.summarize(parsed)
    logger.info(f"检查标准导入成功: {std_type} 「{label}」 {summary['module_count']}模块/{summary['items_total']}条目")
    return {
        "standard_type": std_type,
        "label": label,
        "scoring_model": parsed["scoring_model"],
        "source_filename": filename,
        **summary,
    }


@router.get("/list", summary="检查标准列表（内置 + 自定义）")
def list_standards(db: Session = Depends(get_db)):
    items = []
    for key, cfg in settings.STANDARDS.items():
        items.append({
            "standard_type": key,
            "label": cfg.get("label", key),
            "scoring_model": cfg.get("scoring_model"),
            "module_count": len(cfg.get("modules", {})),
            "is_custom": False,
            "source_filename": None,
            "created_at": None,
            "is_active": True,
        })
    rows = (
        db.query(CustomStandard)
        .filter(CustomStandard.is_active == 1)
        .order_by(CustomStandard.created_at.desc())
        .all()
    )
    for r in rows:
        items.append({
            "standard_type": r.standard_type,
            "label": r.label,
            "scoring_model": r.scoring_model,
            "module_count": r.module_count,
            "items_total": r.items_total,
            "is_custom": True,
            "source_filename": r.source_filename,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else None,
            "is_active": True,
        })
    return {"total": len(items), "items": items}


@router.get("/{standard_type}/modules", summary="查询标准的模块清单")
def get_standard_modules(standard_type: str, db: Session = Depends(get_db)):
    if standard_type in BUILTIN_TYPES:
        cfg = settings.STANDARDS[standard_type]
        return {"standard_type": standard_type, "module_count": len(cfg["modules"]), "modules": list(cfg["modules"].keys())}
    row = (
        db.query(CustomStandard)
        .filter(CustomStandard.standard_type == standard_type, CustomStandard.is_active == 1)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="检查标准不存在")
    modules = list(json.loads(row.modules_json).keys())
    return {"standard_type": standard_type, "module_count": len(modules), "modules": modules}


@router.delete("/{standard_type}", summary="删除自定义检查标准（软删除）")
def delete_standard(standard_type: str, db: Session = Depends(get_db), current_user: Any = Depends(_require_admin)):
    if standard_type in BUILTIN_TYPES:
        raise HTTPException(status_code=400, detail="内置检查标准不可删除")
    row = db.query(CustomStandard).filter(CustomStandard.standard_type == standard_type).first()
    if not row or not row.is_active:
        raise HTTPException(status_code=404, detail="检查标准不存在")

    # 有任务引用时禁止删除（避免历史任务评分/巡检失配）
    from models.models import InspectionTask
    used = db.query(InspectionTask).filter(InspectionTask.standard_type == standard_type).count()
    if used > 0:
        raise HTTPException(status_code=409, detail=f"有 {used} 个检查任务正在使用该标准，不可删除")

    row.is_active = 0
    db.commit()
    unregister_custom(standard_type)
    return {"message": "已删除", "standard_type": standard_type}
