"""
检查标准(standard_type)访问器
单一数据源：所有「取模块清单 / 取模块配置 / 取计分模型」都应通过此处，而非直读 settings.MODULE_WEIGHTS。

标准来源两级：
  1) 内置标准：config.settings.STANDARDS（diecheng / feidiecheng / lizhi）
  2) 自定义标准：custom_standards 表（「检查标准导入」功能生成，standard_type 形如 custom_xxxxxxxx）
解析顺序：自定义优先（TTL 缓存，30s），未命中回落内置；都未命中回落默认标准。
"""
import json
import logging
import time
from typing import Any, Dict, Optional

from config import settings

logger = logging.getLogger(__name__)

DEFAULT_STANDARD = "diecheng"

# ==================== 自定义标准运行时缓存 ====================
_custom_cache: Dict[str, Dict[str, Any]] = {}
_cache_ts: float = 0.0
_CACHE_TTL = 30.0  # 秒；导入/删除后可 force 刷新


def _refresh_custom(force: bool = False) -> None:
    """从 DB 预载自定义标准到内存缓存（表不存在/异常时静默降级为无自定义）"""
    global _cache_ts
    now = time.time()
    if not force and now - _cache_ts < _CACHE_TTL:
        return
    try:
        from database import SessionLocal
        from models.standard import CustomStandard

        db = SessionLocal()
        try:
            rows = db.query(CustomStandard).filter(CustomStandard.is_active == 1).all()
            fresh: Dict[str, Dict[str, Any]] = {}
            for r in rows:
                fresh[r.standard_type] = {
                    "standard_type": r.standard_type,
                    "label": r.label,
                    "scoring_model": r.scoring_model,
                    "modules": json.loads(r.modules_json or "{}"),
                    "file": r.template_file,
                    "custom": True,
                }
            _custom_cache.clear()
            _custom_cache.update(fresh)
            _cache_ts = now
        finally:
            db.close()
    except Exception as e:
        # 表未建（旧库首次启动）或 DB 异常：按无自定义处理，不影响内置标准
        logger.debug(f"自定义标准加载跳过: {e}")


def register_custom(cfg: Dict[str, Any]) -> None:
    """导入成功后立即注册（免等 TTL）"""
    _refresh_custom(True)
    _custom_cache[cfg["standard_type"]] = cfg
    _cache_ts = time.time()


def unregister_custom(standard_type: str) -> None:
    _custom_cache.pop(standard_type, None)
    _cache_ts = time.time()


def get_custom_config(standard_type: str) -> Optional[Dict[str, Any]]:
    """供 tasks.load_template_items 等取自定义标准完整配置（含 file），无则 None"""
    _refresh_custom()
    cfg = _custom_cache.get(standard_type)
    return dict(cfg) if cfg else None


# ==================== 统一解析 ====================

def _resolve_cfg(standard_type: str) -> Dict[str, Any]:
    """返回标准配置 dict；两级都未命中回落默认内置标准"""
    _refresh_custom()
    if standard_type and standard_type in _custom_cache:
        return _custom_cache[standard_type]
    if standard_type and standard_type in settings.STANDARDS:
        return settings.STANDARDS[standard_type]
    return settings.STANDARDS[DEFAULT_STANDARD]


def _resolve_name(standard_type: str) -> str:
    _refresh_custom()
    if standard_type and standard_type in _custom_cache:
        return standard_type
    if standard_type and standard_type in settings.STANDARDS:
        return standard_type
    return DEFAULT_STANDARD


def _norm(standard_type: str) -> str:
    return _resolve_name(standard_type)


# ==================== 对外访问器（签名不变） ====================

def get_standard(standard_type: str) -> dict:
    """返回整份标准配置（含 label / scoring_model / modules；自定义另含 file）"""
    return _resolve_cfg(standard_type)


def get_modules(standard_type: str) -> list:
    """返回该标准的模块名列表（有序）"""
    return list(_resolve_cfg(standard_type).get("modules", {}).keys())


def get_module_cfg(standard_type: str, module_name: str) -> dict:
    """返回单个模块配置：{weight} 或 {max_score, role}；未知模块返回 {}"""
    return _resolve_cfg(standard_type).get("modules", {}).get(module_name, {})


def get_scoring_model(standard_type: str) -> str:
    """返回计分模型：'weighted_5pt' | 'point_cap'"""
    return _resolve_cfg(standard_type).get("scoring_model", "weighted_5pt")


def is_deduction_module(standard_type: str, module_name: str) -> bool:
    return get_module_cfg(standard_type, module_name).get("role") == "deduction"


def get_module_max_score(standard_type: str, module_name: str) -> float:
    """计分模块的封顶分；非 point_cap 标准或无 max_score 时返回 None"""
    cfg = get_module_cfg(standard_type, module_name)
    if "max_score" in cfg:
        return cfg["max_score"]
    return None


def get_label(standard_type: str) -> str:
    return _resolve_cfg(standard_type).get("label", standard_type)
