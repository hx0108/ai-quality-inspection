"""
数据备份与恢复 API
支持 SQLite 数据库备份和完整数据备份（DB + 照片 + 报告）
包含自动定时备份调度器
"""
import os
import logging
import shutil
import sqlite3
import tarfile
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from database import get_db
from models.models import User
from api.deps import get_current_user, check_role
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

BACKUP_DIR = settings.DATA_DIR / "backups"

# 自动备份保留策略：按天数清理，避免无限堆积撑满磁盘
# 注意：daily/full 备份含照片+报告（每个约270MB），保留天数不宜过多
RETENTION_DAYS = {
    "hourly": 7,        # 保留最近 7 天的每小时备份（仅DB，每个~3MB）
    "daily": 7,         # 保留最近 7 天的每日完整备份（含照片报告，每个~270MB）
    "full": 7,          # 保留最近 7 天的完整备份
    "pre_restore": 7,   # 保留最近 7 天的恢复前备份
}


def _ensure_backup_dir():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _dir_size_mb(path: Path) -> float:
    if not path.exists():
        return 0
    total = 0
    for f in path.rglob("*"):
        if f.is_file():
            total += f.stat().st_size
    return round(total / 1024 / 1024, 1)


def _db_path() -> Path:
    """从 DATABASE_URL 提取 SQLite 文件路径"""
    url = settings.DATABASE_URL
    if ":///" in url:
        return Path(url.split("sqlite:///")[1])
    elif "://" in url:
        return Path(url.split("://")[1])
    return Path(url)


def _safe_db_snapshot() -> str:
    """使用 SQLite backup API 生成生产数据库的一致性快照（在线安全备份）。
    返回临时快照文件路径。调用方负责删除。
    相比直接复制文件：不会拷到写一半的脏数据，不会损坏生产库，备份内容保证一致。"""
    db_file = _db_path()
    src = sqlite3.connect(str(db_file))
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db", dir=str(BACKUP_DIR))
    os.close(tmp_fd)
    try:
        dst = sqlite3.connect(tmp_path)
        src.backup(dst)  # 在线一致性拷贝，不锁生产库
        dst.close()
    except Exception:
        src.close()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
    src.close()
    return tmp_path


def _do_backup(btype: str) -> str:
    """执行备份，返回文件名"""
    _ensure_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{btype}_{timestamp}.tar.gz"
    filepath = BACKUP_DIR / filename

    db_file = _db_path()
    include_files = btype in ("full", "daily", "pre_restore")

    with tarfile.open(filepath, "w:gz") as tar:
        # 使用 backup API 安全读取生产库（替代直接 tar.add 文件）
        tmp_db = None
        try:
            if db_file.exists():
                tmp_db = _safe_db_snapshot()
                tar.add(tmp_db, arcname=f"data/{db_file.name}")
        finally:
            if tmp_db and os.path.exists(tmp_db):
                os.remove(tmp_db)
        if include_files:
            if settings.PHOTOS_DIR.exists():
                tar.add(settings.PHOTOS_DIR, arcname="data/photos")
            if settings.REPORTS_DIR.exists():
                tar.add(settings.REPORTS_DIR, arcname="data/reports")

    size_mb = round(filepath.stat().st_size / 1024 / 1024, 1)
    logger.info(f"自动备份完成: {filename} ({size_mb} MB)")

    # 每次备份后立即清理超期备份（防止无限堆积撑满磁盘）
    _cleanup_old_backups(btype)

    return filename


def _cleanup_old_backups(btype: str):
    """清理超期备份：按天数删除，删除超过保留期的备份文件；同时删除0字节垃圾文件"""
    from datetime import timedelta
    _ensure_backup_dir()
    keep_days = RETENTION_DAYS.get(btype, 7)
    cutoff = datetime.now() - timedelta(days=keep_days)
    removed = 0
    for f in BACKUP_DIR.glob(f"backup_{btype}_*.tar.gz"):
        try:
            # 删除0字节垃圾文件（磁盘满时写失败的空备份）
            if f.stat().st_size == 0:
                f.unlink()
                removed += 1
                continue
            # 按修改时间判断是否超期
            if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                f.unlink()
                removed += 1
        except Exception as e:
            logger.warning(f"清理备份失败 {f.name}: {e}")
    if removed:
        logger.info(f"清理了 {removed} 个 {btype} 备份（超期或空文件，保留 {keep_days} 天）")


# ==================== 自动备份调度器 ====================

_scheduler_running = False


def start_backup_scheduler():
    """启动自动备份调度器（后台守护线程）"""
    global _scheduler_running
    if _scheduler_running:
        return
    _scheduler_running = True

    def _scheduler_loop():
        import time
        # 启动后等 60 秒再开始（等应用完全就绪）
        time.sleep(60)
        logger.info("自动备份调度器已启动")

        last_hourly = 0
        last_daily_date = None

        while True:
            try:
                now = time.time()
                dt = datetime.now()

                # 每小时 DB 备份
                if now - last_hourly >= 3600:
                    try:
                        _do_backup("hourly")
                        last_hourly = now
                    except Exception as e:
                        logger.error(f"每小时备份失败: {e}")

                # 每日完整备份（凌晨 3:00）
                today = dt.strftime("%Y-%m-%d")
                if dt.hour == 3 and last_daily_date != today:
                    try:
                        _do_backup("daily")
                        last_daily_date = today
                    except Exception as e:
                        logger.error(f"每日备份失败: {e}")

                # 每 10 分钟检查一次
                time.sleep(600)
            except Exception as e:
                logger.error(f"调度器循环异常，10分钟后重试: {e}")
                time.sleep(600)

    t = threading.Thread(target=_scheduler_loop, daemon=True)
    t.start()
    logger.info("自动备份调度器线程已创建")


# ==================== 请求模型 ====================

class BackupCreate(BaseModel):
    type: str = "full"  # full | hourly | daily | pre_restore


class RestoreRequest(BaseModel):
    filename: str
    backup_type: Optional[str] = None


# ==================== API 端点 ====================

@router.get("/status", summary="备份状态概览")
async def get_backup_status(
    current_user: User = Depends(check_role(["admin"])),
):
    _ensure_backup_dir()
    db_file = _db_path()
    db_size = round(db_file.stat().st_size / 1024 / 1024, 1) if db_file.exists() else 0
    photos_size = _dir_size_mb(settings.PHOTOS_DIR)
    reports_size = _dir_size_mb(settings.REPORTS_DIR)
    total = round(db_size + photos_size + reports_size, 1)

    # 列出备份文件
    backups = sorted(BACKUP_DIR.glob("*.tar.gz"), key=lambda f: f.stat().st_mtime, reverse=True)
    last_backup = None
    if backups:
        f = backups[0]
        last_backup = {
            "filename": f.name,
            "size_mb": round(f.stat().st_size / 1024 / 1024, 1),
            "created_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        }

    return {
        "db_size_mb": db_size,
        "photos_size_mb": photos_size,
        "reports_size_mb": reports_size,
        "total_data_size_mb": total,
        "external_backup_count": len(backups),
        "last_backup": last_backup,
    }


@router.get("/list", summary="备份文件列表")
async def list_backups(
    type: Optional[str] = None,
    current_user: User = Depends(check_role(["admin"])),
):
    _ensure_backup_dir()
    backups = sorted(BACKUP_DIR.glob("*.tar.gz"), key=lambda f: f.stat().st_mtime, reverse=True)

    items = []
    for f in backups:
        # 从文件名解析类型: backup_{type}_{timestamp}.tar.gz
        fname = f.name
        if type and type not in fname:
            continue
        btype = "full"
        for t in ["full", "daily", "hourly", "pre_restore"]:
            if t in fname:
                btype = t
                break

        items.append({
            "filename": fname,
            "type": btype,
            "size_mb": round(f.stat().st_size / 1024 / 1024, 1),
            "created_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })

    return {"items": items}


@router.post("/create", summary="创建备份")
async def create_backup(
    req: BackupCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(check_role(["admin"])),
):
    btype = req.type or "full"

    def _run():
        _do_backup(btype)

    background_tasks.add_task(_run)
    return {"message": f"备份创建中 ({btype})"}


@router.post("/restore", summary="恢复备份")
async def restore_backup(
    req: dict,
    current_user: User = Depends(check_role(["admin"])),
):
    filename = req.get("filename") or req.get("file")
    if not filename:
        raise HTTPException(status_code=400, detail="缺少 filename")

    filepath = BACKUP_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="备份文件不存在")

    # 创建恢复前备份
    pre_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pre_filename = f"backup_pre_restore_{pre_timestamp}.tar.gz"
    pre_filepath = BACKUP_DIR / pre_filename
    db_file = _db_path()
    with tarfile.open(pre_filepath, "w:gz") as tar:
        tmp_db = None
        try:
            if db_file.exists():
                tmp_db = _safe_db_snapshot()
                tar.add(tmp_db, arcname=f"data/{db_file.name}")
        finally:
            if tmp_db and os.path.exists(tmp_db):
                os.remove(tmp_db)
        if settings.PHOTOS_DIR.exists():
            tar.add(settings.PHOTOS_DIR, arcname="data/photos")
        if settings.REPORTS_DIR.exists():
            tar.add(settings.REPORTS_DIR, arcname="data/reports")

    # 解压恢复
    restore_dir = settings.DATA_DIR / "_restore_tmp"
    if restore_dir.exists():
        shutil.rmtree(restore_dir)
    restore_dir.mkdir(parents=True)

    with tarfile.open(filepath, "r:gz") as tar:
        tar.extractall(restore_dir)

    # 恢复数据库文件
    restored_db = restore_dir / "data" / db_file.name
    if restored_db.exists():
        shutil.copy2(restored_db, db_file)

    # 恢复照片
    restored_photos = restore_dir / "data" / "photos"
    if restored_photos.exists():
        if settings.PHOTOS_DIR.exists():
            shutil.rmtree(settings.PHOTOS_DIR)
        shutil.copytree(restored_photos, settings.PHOTOS_DIR)

    # 恢复报告
    restored_reports = restore_dir / "data" / "reports"
    if restored_reports.exists():
        if settings.REPORTS_DIR.exists():
            shutil.rmtree(settings.REPORTS_DIR)
        shutil.copytree(restored_reports, settings.REPORTS_DIR)

    # 清理临时目录
    shutil.rmtree(restore_dir, ignore_errors=True)

    return {"message": f"已从 {filename} 恢复数据，恢复前备份: {pre_filename}"}


@router.delete("/{filename}", summary="删除备份")
async def delete_backup(
    filename: str,
    current_user: User = Depends(check_role(["admin"])),
):
    filepath = BACKUP_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="备份文件不存在")
    filepath.unlink()
    return {"message": f"已删除备份: {filename}"}
