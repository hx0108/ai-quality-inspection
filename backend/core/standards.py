"""
检查标准(standard_type)访问器
单一数据源：所有「取模块清单 / 取模块配置 / 取计分模型」都应通过此处，而非直读 settings.MODULE_WEIGHTS。
"""
from config import settings

DEFAULT_STANDARD = "diecheng"


def _norm(standard_type: str) -> str:
    if not standard_type or standard_type not in settings.STANDARDS:
        return DEFAULT_STANDARD
    return standard_type


def get_standard(standard_type: str) -> dict:
    """返回整份标准配置（含 label / scoring_model / modules）"""
    return settings.STANDARDS[_norm(standard_type)]


def get_modules(standard_type: str) -> list:
    """返回该标准的模块名列表（有序）"""
    return list(settings.STANDARDS[_norm(standard_type)]["modules"].keys())


def get_module_cfg(standard_type: str, module_name: str) -> dict:
    """返回单个模块配置：{weight} 或 {max_score, role}；未知模块返回 {}"""
    return settings.STANDARDS[_norm(standard_type)]["modules"].get(module_name, {})


def get_scoring_model(standard_type: str) -> str:
    """返回计分模型：'weighted_5pt' | 'point_cap'"""
    return settings.STANDARDS[_norm(standard_type)]["scoring_model"]


def is_deduction_module(standard_type: str, module_name: str) -> bool:
    return get_module_cfg(standard_type, module_name).get("role") == "deduction"


def get_module_max_score(standard_type: str, module_name: str) -> float:
    """计分模块的封顶分；非 point_cap 标准或无 max_score 时返回 None"""
    cfg = get_module_cfg(standard_type, module_name)
    if "max_score" in cfg:
        return cfg["max_score"]
    return None


def get_label(standard_type: str) -> str:
    return get_standard(standard_type).get("label", standard_type)
