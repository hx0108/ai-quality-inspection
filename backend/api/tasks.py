"""
检查任务 API
任务创建、查询、模块分配
"""
import os
import json
import uuid as _uuid
from datetime import datetime
from collections import defaultdict
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, text
import openpyxl

from database import get_db
from models.models import User, Project, InspectionTask, TaskAssignment, InspectionRecord, Issue, Photo, ScoringResult, Report, Rectification
from api.deps import get_current_user, check_role, get_user_project_filter, apply_task_visibility
from config import settings
from core.logger import get_logger
from core import standards as stds

logger = get_logger("tasks")

router = APIRouter()


# ==================== 模板数据缓存 ====================
_template_cache: Dict[str, List[Dict[str, Any]]] = {}
_template_mtime: Dict[str, float] = {}  # 缓存文件修改时间，用于热更新检测

# 检查标准配置
STANDARD_TYPES = {
    "diecheng": {"label": "蝶城版", "file": "内审检查表V3.0.xlsx"},
    "feidiecheng": {"label": "非蝶城版", "file": "内审检查表_简化版V3.0.xlsx"},
    "lizhi": {"label": "砺质版", "file": "砺质行动检查标准（8月）.xlsx"},
}


def clear_template_cache():
    """清除所有模板缓存（用于热更新）"""
    global _template_cache, _template_mtime
    _template_cache.clear()
    _template_mtime.clear()
    logger.info("模板缓存已清除")


def load_template_items(module_name: str, standard_type: str = "diecheng") -> List[Dict[str, Any]]:
    """从Excel模板加载检查项（支持热更新，文件修改后自动重新加载）

    item_id 格式: {sheet_prefix}-{row_idx:03d}
    例如: 客户-001, 安全-001
    """
    global _template_cache, _template_mtime

    cache_key = f"{standard_type}:{module_name}"
    std_config = STANDARD_TYPES.get(standard_type)
    if not std_config:
        return []

    template_path = settings.TEMPLATES_DIR / std_config["file"]
    if not os.path.exists(template_path):
        logger.warning(f"模板文件不存在: {template_path} (TEMPLATES_DIR={settings.TEMPLATES_DIR}, 绝对路径={template_path.resolve()})")
        return []

    # 检查文件修改时间，实现热更新
    try:
        current_mtime = os.path.getmtime(template_path)
    except OSError:
        return []

    # 缓存命中且文件未修改时直接返回
    if cache_key in _template_cache:
        if _template_mtime.get(cache_key) == current_mtime:
            return _template_cache[cache_key]
        # 文件已修改，清除旧缓存
        logger.info(f"检测到模板文件已修改，自动重新加载: {cache_key}")

    try:
        wb = openpyxl.load_workbook(str(template_path), read_only=True)

        # 查找对应的工作表
        sheet_name = module_name
        if sheet_name not in wb.sheetnames:
            # 尝试模糊匹配
            for name in wb.sheetnames:
                if module_name in name or name in module_name:
                    sheet_name = name
                    break

        if sheet_name not in wb.sheetnames:
            logger.warning(f"工作表 '{module_name}' 未找到，可用工作表: {wb.sheetnames}")
            wb.close()
            return []

        ws = wb[sheet_name]
        items = []

        # 砺质标准：列布局为 A检查内容 / B检查要求 / C评分标准 / D max_score（无权重列）
        is_lizhi = (standard_type == "lizhi")
        is_deduction_module = stds.is_deduction_module(standard_type, sheet_name) if is_lizhi else False

        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=1):
            if not row[0]:  # 检查点为空则跳过
                continue

            item_id = f"{sheet_name[:2]}-{row_idx:03d}"

            if is_lizhi:
                check_req = str(row[1]) if len(row) > 1 and row[1] else ""
                max_score = float(row[3]) if len(row) > 3 and row[3] not in (None, "") else (
                    stds.get_module_max_score(standard_type, sheet_name) or 0
                )
                items.append({
                    "item_id": item_id,
                    "item_name": str(row[0]) if row[0] else "",
                    "check_standard": check_req,
                    "check_method": check_req,
                    "scoring_rule": str(row[2]) if len(row) > 2 and row[2] else "",
                    "weight": 0.0,
                    "max_score": max_score,
                    "is_deduction": is_deduction_module,
                })
            else:
                items.append({
                    "item_id": item_id,
                    "item_name": str(row[0]) if row[0] else "",
                    "check_standard": str(row[1]) if row[1] else "",
                    "check_method": str(row[2]) if row[2] else "",
                    "scoring_rule": str(row[3]) if row[3] else "完全符合5分",
                    "weight": float(row[7]) if len(row) > 7 and row[7] else 0.01,
                    "max_score": 5,
                    "is_deduction": False,
                })

        wb.close()
        _template_cache[cache_key] = items
        _template_mtime[cache_key] = current_mtime
        logger.info(f"模板加载成功: {cache_key}, {len(items)} 项, 文件={template_path}")
        return items

    except Exception as e:
        logger.error(f"加载模板失败: {e}")
        return []


# ==================== 请求/响应模型 ====================
class TaskCreate(BaseModel):
    project_id: int
    check_date: str  # YYYY-MM-DD
    standard_type: str = "diecheng"  # diecheng / feidiecheng


class TaskBatchCreate(BaseModel):
    project_ids: List[int]
    check_date: str  # YYYY-MM-DD
    standard_type: str = "diecheng"


class TaskAssign(BaseModel):
    module_name: str
    inspector_id: int


class TaskBatchAssign(BaseModel):
    task_ids: List[str]
    assignments: List[TaskAssign]


class TaskResponse(BaseModel):
    id: int
    task_id: str
    project_id: int
    project_name: str
    check_date: str
    standard_type: str = "diecheng"
    status: str
    total_score: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


class TaskDetail(BaseModel):
    id: int
    task_id: str
    project_id: int
    project_name: str
    check_date: str
    status: str
    total_score: Optional[float]
    created_at: datetime
    modules: List[dict]

    class Config:
        from_attributes = True


# ==================== 模块列表 ====================
# 向后兼容：蝶城默认模块清单。按标准取模块请用 get_module_names(standard_type)。
MODULE_NAMES = list(settings.MODULE_WEIGHTS.keys())


def get_module_names(standard_type: str) -> List[str]:
    """按检查标准返回模块名列表"""
    return stds.get_modules(standard_type)


# ==================== API 端点 ====================
# 注意：路由顺序很重要！更具体的路由要放在前面

@router.get("/projects", summary="获取所有项目列表")
async def get_projects(db: Session = Depends(get_db)):
    """获取所有项目列表（公开接口，供注册页使用）"""
    projects = db.query(Project).all()
    return {
        "total": len(projects),
        "items": [{"id": p.id, "name": p.name, "code": p.code} for p in projects]
    }


@router.get("/standard-types", summary="获取检查标准类型列表")
async def get_standard_types():
    """获取可用的检查标准类型"""
    return {
        "items": [
            {"value": key, "label": cfg["label"]}
            for key, cfg in STANDARD_TYPES.items()
        ]
    }


@router.post("/template-cache/clear", summary="清除模板缓存（热更新）")
async def clear_cache(current_user: User = Depends(check_role("admin"))):
    """
    清除所有模板缓存，使下次访问时重新加载文件。
    用于管理员修改Excel模板后无需重启服务即可生效。
    """
    clear_template_cache()
    return {"message": "模板缓存已清除", "timestamp": datetime.now().isoformat()}


@router.get("/template-diagnose", summary="诊断模板文件状态（管理员）")
async def diagnose_templates(current_user: User = Depends(check_role("admin"))):
    """检查模板文件是否存在、可读取，用于排查检查项为空的问题"""
    result = {}
    for key, cfg in STANDARD_TYPES.items():
        path = settings.TEMPLATES_DIR / cfg["file"]
        info = {
            "file": cfg["file"],
            "path": str(path),
            "abs_path": str(path.resolve()),
            "exists": os.path.exists(path),
        }
        if os.path.exists(path):
            try:
                import openpyxl as _oxl
                wb = _oxl.load_workbook(str(path), read_only=True)
                info["sheets"] = wb.sheetnames
                info["readable"] = True
                wb.close()
            except Exception as e:
                info["readable"] = False
                info["error"] = str(e)
        else:
            info["readable"] = False
            info["error"] = "文件不存在"
        result[key] = info

    return {
        "templates_dir": str(settings.TEMPLATES_DIR),
        "templates_dir_abs": str(settings.TEMPLATES_DIR.resolve()),
        "module_names": MODULE_NAMES,
        "standards": result
    }


@router.get("/module-template/{module_name}", summary="获取模块检查项模板")
async def get_module_template(
    module_name: str,
    standard_type: str = "diecheng",
    current_user: User = Depends(get_current_user)
):
    """获取指定模块的检查项模板"""
    allowed = get_module_names(standard_type)
    if module_name not in allowed:
        raise HTTPException(status_code=400, detail=f"无效的模块名称，可选：{allowed}")

    items = load_template_items(module_name, standard_type)
    return {
        "module_name": module_name,
        "total": len(items),
        "items": items
    }


@router.get("/my-tasks/list", summary="获取我的检查任务")
async def get_my_tasks(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取分配给当前用户的检查任务（管理员可以看到自己创建的所有任务）"""
    # 管理员可以看到自己创建的所有任务
    if current_user.role == "admin":
        tasks = db.query(InspectionTask).filter(
            InspectionTask.created_by == current_user.id
        ).order_by(InspectionTask.created_at.desc()).all()

        return {
            "total": len(tasks),
            "items": [
                {
                    "task_id": t.task_id,
                    "project_name": t.project.name if t.project else "",
                    "check_date": t.check_date,
                    "standard_type": t.standard_type or "diecheng",
                    "status": t.status,
                    "total_score": float(t.total_score) if t.total_score else None
                }
                for t in tasks
            ]
        }

    # 阵地督导：可查看所有任务（与管理员视野一致）
    if current_user.role == "site_supervisor":
        all_tasks = db.query(InspectionTask).order_by(
            InspectionTask.created_at.desc()
        ).all()
        all_task_ids = [t.task_id for t in all_tasks]

        # 获取督导被分配的模块（用于 my_modules 展示）
        assignments = db.query(TaskAssignment).filter(
            TaskAssignment.inspector_id == current_user.id
        ).all()

        # 检查记录（不按 inspector_id 过滤，共享记录）
        records = db.query(InspectionRecord).filter(
            InspectionRecord.task_id.in_(all_task_ids)
        ).all() if all_task_ids else []
        record_map = {}
        for r in records:
            # 同一 task+module 只保留一条记录（优先保留已有内容的）
            key = (r.task_id, r.module_name)
            if key not in record_map:
                record_map[key] = r

        return {
            "total": len(all_tasks),
            "items": [
                {
                    "task_id": t.task_id,
                    "project_name": t.project.name if t.project else "",
                    "check_date": t.check_date,
                    "standard_type": t.standard_type or "diecheng",
                    "status": t.status,
                    "total_score": float(t.total_score) if t.total_score else None,
                    "my_modules": [
                        {
                            "module_name": a.module_name,
                            "status": record_map.get((a.task_id, a.module_name), None).status if record_map.get((a.task_id, a.module_name)) else "not_started",
                            "record_id": record_map.get((a.task_id, a.module_name), None).record_id if record_map.get((a.task_id, a.module_name)) else None
                        }
                        for a in assignments if a.task_id == t.task_id
                    ]
                }
                for t in all_tasks
            ]
        }

    # 驻场经理/项目人员：关联项目的任务（只读）
    if current_user.role in ("field_supervisor", "project_staff"):
        from api.deps import get_user_project_ids
        project_ids = get_user_project_ids(current_user, db)

        # 如果传了 project_id 且在该用户分管范围内，则只看该项目
        if project_id and project_id in project_ids:
            project_ids = [project_id]

        # 关联项目的任务
        project_tasks = db.query(InspectionTask).filter(
            InspectionTask.project_id.in_(project_ids)
        ).all() if project_ids else []

        # 被分配的任务
        assignments = db.query(TaskAssignment).filter(
            TaskAssignment.inspector_id == current_user.id
        ).all()
        assigned_task_ids = list(set([a.task_id for a in assignments]))
        assigned_tasks = db.query(InspectionTask).filter(
            InspectionTask.task_id.in_(assigned_task_ids)
        ).all() if assigned_task_ids else []

        # 合并去重
        all_task_ids = set(
            [t.task_id for t in project_tasks] +
            [t.task_id for t in assigned_tasks]
        )
        all_tasks = db.query(InspectionTask).filter(
            InspectionTask.task_id.in_(all_task_ids)
        ).order_by(InspectionTask.created_at.desc()).all()

        # 预加载所有检查记录（显示全部模块，不限于分配的）
        records = db.query(InspectionRecord).filter(
            InspectionRecord.task_id.in_(all_task_ids)
        ).all() if all_task_ids else []
        record_map = {}
        for r in records:
            key = (r.task_id, r.module_name)
            if key not in record_map:
                record_map[key] = r

        # 预加载评分结果（取每个 record 的 module_pct_score）
        from models.models import ScoringResult
        scoring_results = db.query(ScoringResult).filter(
            ScoringResult.record_id.in_([r.record_id for r in records]),
            ScoringResult.module_pct_score != None
        ).all() if records else []
        scoring_map = {}
        for sr in scoring_results:
            if sr.record_id not in scoring_map:
                scoring_map[sr.record_id] = float(sr.module_pct_score)

        return {
            "total": len(all_tasks),
            "items": [
                {
                    "task_id": t.task_id,
                    "project_name": t.project.name if t.project else "",
                    "check_date": t.check_date,
                    "standard_type": t.standard_type or "diecheng",
                    "status": t.status,
                    "total_score": float(t.total_score) if t.total_score else None,
                    "my_modules": [
                        {
                            "module_name": r.module_name,
                            "status": r.status,
                            "record_id": r.record_id,
                            "score": scoring_map.get(r.record_id)
                        }
                        for r in records if r.task_id == t.task_id
                    ]
                }
                for t in all_tasks
            ]
        }

    # 普通检查员只能看到分配给自己的任务
    assignments = db.query(TaskAssignment).filter(
        TaskAssignment.inspector_id == current_user.id
    ).all()

    task_ids = list(set([a.task_id for a in assignments]))

    tasks = db.query(InspectionTask).filter(
        InspectionTask.task_id.in_(task_ids)
    ).all() if task_ids else []

    # 预加载检查记录（不按 inspector_id 过滤，共享记录）
    records = db.query(InspectionRecord).filter(
        InspectionRecord.task_id.in_(task_ids)
    ).all() if task_ids else []
    record_map = {}
    for r in records:
        key = (r.task_id, r.module_name)
        if key not in record_map:
            record_map[key] = r

    return {
        "total": len(tasks),
        "items": [
            {
                "task_id": t.task_id,
                "project_name": t.project.name if t.project else "",
                "check_date": t.check_date,
                "standard_type": t.standard_type or "diecheng",
                "status": t.status,
                "my_modules": [
                    {
                        "module_name": a.module_name,
                        "status": record_map.get((a.task_id, a.module_name), None).status if record_map.get((a.task_id, a.module_name)) else "not_started",
                        "record_id": record_map.get((a.task_id, a.module_name), None).record_id if record_map.get((a.task_id, a.module_name)) else None
                    }
                    for a in assignments if a.task_id == t.task_id
                ]
            }
            for t in tasks
        ]
    }


@router.post("", response_model=TaskResponse, summary="创建检查任务")
async def create_task(
    request: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role(["admin"]))
):
    """
    创建检查任务
    - 仅管理员可创建
    """
    # 验证项目存在
    project = db.query(Project).filter(Project.id == request.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 生成任务ID（UUID，无冲突）— 按检查日期编号
    date_str = request.check_date.strftime("%Y%m%d") if hasattr(request.check_date, 'strftime') else str(request.check_date).replace('-', '')[:8]
    task_id = f"Q-{date_str}-{_uuid.uuid4().hex[:8]}"

    # 创建任务
    task = InspectionTask(
        task_id=task_id,
        project_id=request.project_id,
        check_date=request.check_date,
        standard_type=request.standard_type,
        status="pending",
        created_by=current_user.id
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return TaskResponse(
        id=task.id,
        task_id=task.task_id,
        project_id=task.project_id,
        project_name=project.name,
        check_date=task.check_date,
        standard_type=task.standard_type,
        status=task.status,
        total_score=task.total_score,
        created_at=task.created_at
    )


@router.post("/batch", summary="批量创建检查任务")
async def create_tasks_batch(
    request: TaskBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role(["admin"]))
):
    """
    批量创建检查任务：为多个项目创建同检查日期、同标准的任务
    - 仅管理员可创建
    - 同项目+同日期+同标准已有任务时跳过（skipped），同一请求内重复的项目id也跳过
    - 项目不存在记为 failed，其余照常创建；创建部分整体一次提交
    """
    date_str = request.check_date.strftime("%Y%m%d") if hasattr(request.check_date, 'strftime') else str(request.check_date).replace('-', '')[:8]

    created_tasks = []
    skipped, failed = [], []
    seen_ids = set()

    projects = {p.id: p for p in db.query(Project).filter(Project.id.in_(request.project_ids)).all()}

    for pid in request.project_ids:
        project = projects.get(pid)
        if not project:
            failed.append({"project_id": pid, "reason": "项目不存在"})
            continue
        if pid in seen_ids:
            skipped.append({"project_id": pid, "project_name": project.name, "existing_task_id": None, "reason": "本次请求内重复"})
            continue

        existing = db.query(InspectionTask).filter(
            InspectionTask.project_id == pid,
            InspectionTask.check_date == request.check_date,
            InspectionTask.standard_type == request.standard_type,
        ).first()
        if existing:
            skipped.append({"project_id": pid, "project_name": project.name, "existing_task_id": existing.task_id, "reason": "该项目当日同标准任务已存在"})
            continue

        seen_ids.add(pid)
        task = InspectionTask(
            task_id=f"Q-{date_str}-{_uuid.uuid4().hex[:8]}",
            project_id=pid,
            check_date=request.check_date,
            standard_type=request.standard_type,
            status="pending",
            created_by=current_user.id
        )
        db.add(task)
        created_tasks.append((task, project))

    if created_tasks:
        db.commit()
        for task, _ in created_tasks:
            db.refresh(task)

    return {
        "total": len(request.project_ids),
        "created_count": len(created_tasks),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "created": [
            TaskResponse(
                id=task.id,
                task_id=task.task_id,
                project_id=task.project_id,
                project_name=project.name,
                check_date=task.check_date,
                standard_type=task.standard_type,
                status=task.status,
                total_score=task.total_score,
                created_at=task.created_at
            )
            for task, project in created_tasks
        ],
        "skipped": skipped,
        "failed": failed,
    }


@router.post("/assign/batch", summary="批量分配检查员")
async def assign_tasks_batch(
    request: TaskBatchAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role(["admin"]))
):
    """
    批量分配：把同一套「模块→检查员」方案应用到多个任务
    - 仅管理员可用
    - 已有任何分配记录的任务整任务跳过（skipped），不覆盖既有派工
    - 模块名不属于任务自身检查标准的任务记为 failed（整任务失败，不建半套）
    - 方案内同一检查员最多2个模块（与单任务分配一致）；分配部分整体一次提交
    """
    # 入口预校验：方案本身合法才进循环
    if not request.assignments:
        raise HTTPException(status_code=400, detail="分配方案不能为空")
    inspector_ids = {a.inspector_id for a in request.assignments}
    inspectors = {u.id: u for u in db.query(User).filter(User.id.in_(inspector_ids)).all()}
    missing = inspector_ids - set(inspectors.keys())
    if missing:
        raise HTTPException(status_code=400, detail=f"检查员不存在: {sorted(missing)}")
    per_inspector = defaultdict(int)
    for a in request.assignments:
        per_inspector[a.inspector_id] += 1
    overloaded = [i for i, n in per_inspector.items() if n > 2]
    if overloaded:
        raise HTTPException(status_code=400, detail="每个检查员最多只能分配2个模块")

    module_names = [a.module_name for a in request.assignments]

    assigned, skipped, failed = [], [], []
    assigned_rows = []

    tasks = {t.task_id: t for t in db.query(InspectionTask).filter(InspectionTask.task_id.in_(request.task_ids)).all()}
    projects = {p.id: p.name for p in db.query(Project).all()}

    for tid in request.task_ids:
        task = tasks.get(tid)
        if not task:
            failed.append({"task_id": tid, "reason": "任务不存在"})
            continue

        allowed_modules = get_module_names(task.standard_type or "diecheng")
        invalid = [m for m in module_names if m not in allowed_modules]
        if invalid:
            failed.append({"task_id": tid, "reason": f"模块名不属于该任务的检查标准: {invalid[0]}"})
            continue

        has_assignment = db.query(TaskAssignment.id).filter(
            TaskAssignment.task_id == tid
        ).first()
        if has_assignment:
            skipped.append({"task_id": tid, "reason": "该任务已有分配记录"})
            continue

        for a in request.assignments:
            assigned_rows.append(TaskAssignment(
                task_id=tid,
                module_name=a.module_name,
                inspector_id=a.inspector_id,
            ))
        if task.status == "pending":
            task.status = "in_progress"
        assigned.append({"task_id": tid, "project_name": projects.get(task.project_id, ""), "module_count": len(request.assignments)})

    if assigned_rows:
        db.add_all(assigned_rows)
        db.commit()

    return {
        "total": len(request.task_ids),
        "assigned_count": len(assigned),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "assigned": assigned,
        "skipped": skipped,
        "failed": failed,
    }


@router.get("", summary="获取任务列表")
async def get_tasks(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取检查任务列表
    - admin/site_supervisor: 全部任务
    - inspector: 自己被分配的任务
    - field_supervisor/project_staff: 自己分管项目的任务（只读）
    """
    query = apply_task_visibility(db.query(InspectionTask), current_user, db)

    if project_id:
        query = query.filter(InspectionTask.project_id == project_id)
    if status:
        query = query.filter(InspectionTask.status == status)

    total = query.count()
    tasks = query.order_by(InspectionTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # 预计算每个任务的已完成模块数
    task_ids = [t.task_id for t in tasks]
    completed_counts = {}
    scored_task_ids = set()
    if task_ids:
        rows = db.query(
            InspectionRecord.task_id,
            func.count(InspectionRecord.record_id)
        ).filter(
            InspectionRecord.task_id.in_(task_ids),
            InspectionRecord.status == "completed"
        ).group_by(InspectionRecord.task_id).all()
        completed_counts = {r[0]: r[1] for r in rows}
        scored_task_ids = {
            row[0] for row in db.query(InspectionRecord.task_id).join(
                ScoringResult, ScoringResult.record_id == InspectionRecord.record_id
            ).filter(InspectionRecord.task_id.in_(task_ids)).distinct().all()
        }

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "task_id": t.task_id,
                "project_id": t.project_id,
                "project_name": t.project.name if t.project else "",
                "check_date": t.check_date,
                "status": t.status,
                "total_score": float(t.total_score) if t.total_score is not None else None,
                "has_scoring_result": t.task_id in scored_task_ids,
                "completed_modules": completed_counts.get(t.task_id, 0),
                "standard_type": t.standard_type or "diecheng",
                "created_at": t.created_at.isoformat()
            }
            for t in tasks
        ]
    }


@router.get("/{task_id}", summary="获取任务详情")
async def get_task_detail(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取任务详情，含8个模块分配状态（按项目隔离）"""
    task = db.query(InspectionTask).filter(InspectionTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 项目级隔离：field_supervisor/project_staff 只能看自己项目
    project_filter = get_user_project_filter(current_user, db)
    if project_filter is not None and len(project_filter) > 0:
        if task.project_id not in project_filter:
            raise HTTPException(status_code=403, detail="无权查看此任务")

    # 获取已分配的模块
    assignments = db.query(TaskAssignment).filter(TaskAssignment.task_id == task_id).all()
    assigned_modules = {a.module_name: a for a in assignments}

    # project_staff 只能看到自己项目的任务，隐藏其他项目的检查员姓名
    hide_inspector = (current_user.role == "project_staff")

    # 构建模块状态（按任务自身的检查标准取模块清单）
    task_modules = get_module_names(task.standard_type or "diecheng")
    modules = []
    for module_name in task_modules:
        assignment = assigned_modules.get(module_name)
        # 查找该模块的检查记录（不限制 inspector_id，支持管理员代检场景）
        record = db.query(InspectionRecord).filter(
            InspectionRecord.task_id == task_id,
            InspectionRecord.module_name == module_name
        ).order_by(InspectionRecord.updated_at.desc()).first()

        cfg = stds.get_module_cfg(task.standard_type or "diecheng", module_name)
        modules.append({
            "module_name": module_name,
            "weight": cfg.get("weight", 0),
            "max_score": cfg.get("max_score"),
            "role": cfg.get("role", "score"),
            "assigned": assignment is not None,
            "inspector_id": assignment.inspector_id if assignment else None,
            "inspector_name": ("" if hide_inspector else (assignment.inspector.real_name if assignment and assignment.inspector else None)),
            "status": record.status if record else "not_started",
            "record_id": record.record_id if record else None
        })

    return {
        "task_id": task.task_id,
        "project_id": task.project_id,
        "project_name": task.project.name if task.project else "",
        "project_address": task.project.address if task.project else "",
        "check_date": task.check_date,
        "standard_type": task.standard_type or "diecheng",
        "status": task.status,
        "total_score": float(task.total_score) if task.total_score else None,
        "created_at": task.created_at.isoformat(),
        "modules": modules
    }


@router.get("/{task_id}/assignments", summary="获取任务模块分配列表")
async def get_task_assignments(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定任务的模块分配情况（按项目隔离）"""
    task = db.query(InspectionTask).filter(InspectionTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 项目级隔离
    project_filter = get_user_project_filter(current_user, db)
    if project_filter is not None and len(project_filter) > 0:
        if task.project_id not in project_filter:
            raise HTTPException(status_code=403, detail="无权访问此任务")

    assignments = db.query(TaskAssignment).filter(
        TaskAssignment.task_id == task_id
    ).all()

    # project_staff 隐藏检查员姓名
    hide_inspector = (current_user.role == "project_staff")

    items = []
    for a in assignments:
        inspector = db.query(User).filter(User.id == a.inspector_id).first()
        items.append({
            "module_name": a.module_name,
            "inspector_id": a.inspector_id,
            "inspector_name": ("" if hide_inspector else (inspector.real_name if inspector else ""))
        })

    return {"items": items}


@router.post("/{task_id}/assign", summary="分配模块给检查员")
async def assign_module(
    task_id: str,
    request: TaskAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role(["admin"]))
):
    """
    分配模块给检查员
    - 每个检查员最多分配2个模块
    """
    # 验证任务存在
    task = db.query(InspectionTask).filter(InspectionTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 验证模块名称（按任务自身的检查标准）
    allowed = get_module_names(task.standard_type or "diecheng")
    if request.module_name not in allowed:
        raise HTTPException(status_code=400, detail=f"无效的模块名称，可选：{allowed}")

    # 验证检查员存在
    inspector = db.query(User).filter(User.id == request.inspector_id).first()
    if not inspector:
        raise HTTPException(status_code=404, detail="检查员不存在")

    # 检查该模块是否已分配
    existing = db.query(TaskAssignment).filter(
        TaskAssignment.task_id == task_id,
        TaskAssignment.module_name == request.module_name
    ).first()

    if existing:
        # 已分配给同一检查员，无需操作
        if existing.inspector_id == request.inspector_id:
            return {
                "message": "该模块已分配给此检查员",
                "task_id": task_id,
                "module_name": request.module_name,
                "inspector_id": request.inspector_id,
                "inspector_name": inspector.real_name
            }

        # 重新分配：检查新检查员的模块数
        new_count = db.query(TaskAssignment).filter(
            TaskAssignment.task_id == task_id,
            TaskAssignment.inspector_id == request.inspector_id
        ).count()
        if new_count >= 2:
            raise HTTPException(status_code=400, detail="目标检查员已分配2个模块，无法再接收")

        # 更新分配
        old_inspector = db.query(User).filter(User.id == existing.inspector_id).first()
        existing.inspector_id = request.inspector_id
        db.commit()
        return {
            "message": f"已从 {old_inspector.real_name if old_inspector else '未知'} 重新分配给 {inspector.real_name}",
            "task_id": task_id,
            "module_name": request.module_name,
            "inspector_id": request.inspector_id,
            "inspector_name": inspector.real_name
        }

    # 新分配：检查该检查员在该任务中已分配的模块数
    existing_count = db.query(TaskAssignment).filter(
        TaskAssignment.task_id == task_id,
        TaskAssignment.inspector_id == request.inspector_id
    ).count()

    if existing_count >= 2:
        raise HTTPException(status_code=400, detail="每个检查员最多只能分配2个模块")

    # 创建分配记录
    assignment = TaskAssignment(
        task_id=task_id,
        module_name=request.module_name,
        inspector_id=request.inspector_id
    )
    db.add(assignment)

    # 更新任务状态为进行中
    if task.status == "pending":
        task.status = "in_progress"

    db.commit()

    return {
        "message": "分配成功",
        "task_id": task_id,
        "module_name": request.module_name,
        "inspector_id": request.inspector_id,
        "inspector_name": inspector.real_name
    }


@router.delete("/{task_id}", summary="删除任务")
async def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role(["admin"]))
):
    """删除任务及其所有关联数据（仅管理员）"""
    # 清除主session的ORM缓存，避免级联冲突
    db.expire_all()

    # 使用独立session执行删除
    from database import SessionLocal
    del_db = SessionLocal()
    try:
        exists = del_db.execute(text("SELECT 1 FROM inspection_tasks WHERE task_id = :tid"), {"tid": task_id}).scalar()
        if not exists:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 1. 删除整改记录
        del_db.execute(text("DELETE FROM rectifications WHERE task_id = :tid"), {"tid": task_id})

        # 2. 获取关联的检查记录ID
        rows = del_db.execute(text("SELECT record_id FROM inspection_records WHERE task_id = :tid"), {"tid": task_id}).fetchall()
        record_ids = [r[0] for r in rows]

        # 删除评分结果
        for rid in record_ids:
            del_db.execute(text("DELETE FROM scoring_results WHERE record_id = :rid"), {"rid": rid})

        # 删除照片文件
        for rid in record_ids:
            irows = del_db.execute(text("SELECT issue_id FROM issues WHERE record_id = :rid"), {"rid": rid}).fetchall()
            issue_ids = [i[0] for i in irows]
            for iid in issue_ids:
                prows = del_db.execute(text("SELECT file_path FROM photos WHERE issue_id = :iid"), {"iid": iid}).fetchall()
                for p in prows:
                    if os.path.exists(p[0]):
                        os.remove(p[0])
            if issue_ids:
                for iid in issue_ids:
                    del_db.execute(text("DELETE FROM photos WHERE issue_id = :iid"), {"iid": iid})
                del_db.execute(text("DELETE FROM issues WHERE record_id = :rid"), {"rid": rid})

        # 3. 删除检查记录
        del_db.execute(text("DELETE FROM inspection_records WHERE task_id = :tid"), {"tid": task_id})

        # 4. 删除分配、报告
        del_db.execute(text("DELETE FROM task_assignments WHERE task_id = :tid"), {"tid": task_id})
        del_db.execute(text("DELETE FROM reports WHERE task_id = :tid"), {"tid": task_id})

        # 5. 删除任务本身
        del_db.execute(text("DELETE FROM inspection_tasks WHERE task_id = :tid"), {"tid": task_id})

        del_db.commit()
    finally:
        del_db.close()

    return {"message": "任务已删除"}
