"""
系统设置服务
管理运行时可编辑的配置项（API KEY 等）
"""
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from config import settings, BASE_DIR
from core.logger import get_logger

logger = get_logger("settings_service")

# 允许通过 API 修改的 key 白名单
API_KEY_DEFINITIONS = {
    "DASHSCOPE_API_KEY": {"display_name": "通义千问 (Qwen)", "env_attr": "DASHSCOPE_API_KEY"},
    "DEEPSEEK_API_KEY": {"display_name": "DeepSeek", "env_attr": "DEEPSEEK_API_KEY"},
}

# .env 文件写入锁（防止并发写入冲突）
_env_write_lock = threading.Lock()


def mask_key(value: str) -> str:
    """脱敏 API KEY，只显示末 4 位"""
    if not value or len(value) < 4:
        return "****" if value else ""
    return "****" + value[-4:]


def get_api_keys(db) -> List[Dict]:
    """
    获取所有 API KEY 的脱敏信息。
    优先从 system_settings 表读取，无记录则回退到 .env 配置。
    """
    from models.system_settings import SystemSettings

    result = []
    for key_name, defn in API_KEY_DEFINITIONS.items():
        # 先查数据库
        row = db.query(SystemSettings).filter(SystemSettings.key == key_name).first()
        if row:
            raw_value = row.value
            updated_at = row.updated_at.isoformat() if row.updated_at else None
        else:
            # 回退到 settings 单例（来自 .env）
            raw_value = getattr(settings, defn["env_attr"], "")
            updated_at = None

        result.append({
            "name": key_name,
            "display_name": defn["display_name"],
            "masked_value": mask_key(raw_value),
            "is_set": bool(raw_value),
            "updated_at": updated_at,
        })
    return result


def update_api_key(db, key_name: str, new_value: str, user_id: int) -> Dict:
    """
    更新 API KEY：三处同步
    1. 写入 system_settings 表
    2. 更新内存中的 settings 单例（立即生效）
    3. 写入 .env 文件（重启后持久化）
    """
    if key_name not in API_KEY_DEFINITIONS:
        raise ValueError(f"不允许修改的配置项: {key_name}")
    if not new_value or not new_value.strip():
        raise ValueError("API KEY 不能为空")

    new_value = new_value.strip()
    defn = API_KEY_DEFINITIONS[key_name]

    # 1. 写入/更新数据库
    from models.system_settings import SystemSettings
    row = db.query(SystemSettings).filter(SystemSettings.key == key_name).first()
    if row:
        row.value = new_value
        row.updated_by = user_id
        row.updated_at = datetime.utcnow()
    else:
        row = SystemSettings(
            key=key_name,
            value=new_value,
            updated_by=user_id,
            updated_at=datetime.utcnow(),
        )
        db.add(row)
    db.commit()

    # 2. 更新内存中的 settings 单例（后续 AI 调用立即使用新 key）
    setattr(settings, defn["env_attr"], new_value)

    # 3. 同步写入 .env 文件
    _write_env_file(key_name, new_value)

    logger.info(f"[API KEY 更新] {defn['display_name']} 已由用户 {user_id} 更新")

    return {
        "name": key_name,
        "display_name": defn["display_name"],
        "masked_value": mask_key(new_value),
        "is_set": True,
    }


def _write_env_file(key_name: str, new_value: str):
    """更新 .env 文件中的指定行，保持其他内容不变"""
    with _env_write_lock:
        env_path = BASE_DIR / ".env"
        try:
            lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
            found = False
            for i, line in enumerate(lines):
                if line.startswith(f"{key_name}="):
                    lines[i] = f"{key_name}={new_value}"
                    found = True
                    break
            if not found:
                lines.append(f"{key_name}={new_value}")
            env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            logger.info(f".env 文件已更新: {key_name}")
        except Exception as e:
            logger.warning(f".env 文件写入失败（运行时已生效，重启后将回退到旧值）: {e}")
