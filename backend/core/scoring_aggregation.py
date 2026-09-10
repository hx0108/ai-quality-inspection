"""
按 standard_type 计算模块得分与项目总分（单一数据源）。
- weighted_5pt（蝶城/非蝶城）：逐行复刻既有逻辑
    模块百分制 = Σ(score×weight) / (5 × Σweight) × 100
    项目总分   = Σ(模块百分制 × 模块权重)
- point_cap（砺质）：
    计分模块得分 = min(Σ项分, max_score)   （封顶 25）
    扣分模块得分 = Σ项分                    （≤0）
    项目总分    = clamp(Σ各模块得分, 0, 100)
"""
from core import standards as stds


def aggregate(standard_type: str, modules_data: dict) -> dict:
    """
    Args:
        standard_type: 检查标准
        modules_data: {module_name: {"raw_score_sum": float, "weight_sum": float}}
            - weighted_5pt: raw_score_sum = Σ(score×weight), weight_sum = Σweight
            - point_cap:    raw_score_sum = Σ 项分（扣分模块为负）, weight_sum 忽略

    Returns:
        {"module_pct": {module_name: 得分}, "total": 项目总分}
        - weighted_5pt: module_pct 为百分制 0-100
        - point_cap:    module_pct 为模块得分（计分模块 0-25；扣分模块 ≤0）
    """
    model = stds.get_scoring_model(standard_type)
    module_pct = {}

    if model == "point_cap":
        total = 0.0
        for module_name in stds.get_modules(standard_type):
            cfg = stds.get_module_cfg(standard_type, module_name)
            data = modules_data.get(module_name)
            raw = float(data["raw_score_sum"]) if data else 0.0
            if cfg.get("role") == "deduction":
                mscore = raw  # 扣分模块：负分
            else:
                mscore = min(raw, cfg.get("max_score", 25))
            module_pct[module_name] = mscore
            total += mscore
        total = max(0.0, min(total, 100.0))
        return {"module_pct": module_pct, "total": round(total, 2)}

    # weighted_5pt —— 逐行复刻 api/scoring.py 既有逻辑
    total = 0.0
    for module_name in stds.get_modules(standard_type):
        cfg = stds.get_module_cfg(standard_type, module_name)
        module_weight = cfg.get("weight", 0)
        data = modules_data.get(module_name)
        if data and data.get("weight_sum", 0) > 0:
            max_score = 5 * data["weight_sum"]
            pct = (data["raw_score_sum"] / max_score * 100)
        else:
            pct = 0.0
        module_pct[module_name] = pct
        total += pct * module_weight
    return {"module_pct": module_pct, "total": round(total, 2)}


def total_module_count(standard_type: str) -> int:
    return len(stds.get_modules(standard_type))
