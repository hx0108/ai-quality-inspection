"""
检查标准文件解析器
支持：Excel（openpyxl）/ Word（python-docx）→ 结构化标准 JSON
策略：
  1) 规范工作簿（每模块一个 sheet）→ 确定性解析，零 AI 参与
  2) 其他布局（混排 sheet / Word 文档）→ 提取纯文本后交给 LLM 结构化抽取
产出统一形状（parsed_standard）：
  {"scoring_model": "point_cap|weighted_5pt",
   "modules": [{"name", "max_score", "role", "weight",
                "items": [{"name", "standard", "scoring", "max_score"}]}]}
"""
import io
import json
import logging
import re
from typing import Any, Dict, List, Optional

import openpyxl

from config import settings

logger = logging.getLogger(__name__)

_MAX_LLM_CHARS = 12000  # 喂给 LLM 的文本上限（约 6K tokens）


# ==================== 文本抽取 ====================

def extract_workbook(path: str) -> List[Dict[str, Any]]:
    """Excel → [{sheet, rows: [[cell,...],...]}]（跳过全空行/列尾空白）"""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheets = []
    try:
        for sn in wb.sheetnames:
            ws = wb[sn]
            rows = []
            for row in ws.iter_rows(values_only=True):
                cells = ["" if c is None else str(c).strip() for c in row]
                while cells and cells[-1] == "":
                    cells.pop()
                rows.append(cells)
            # 去掉尾部全空行
            while rows and not rows[-1]:
                rows.pop()
            if rows:
                sheets.append({"sheet": sn, "rows": rows})
    finally:
        wb.close()
    return sheets


def extract_docx(path: str) -> str:
    """Word → 纯文本（段落 + 表格按行 TSV），供 LLM 抽取"""
    try:
        import docx
    except ImportError:
        raise RuntimeError("服务器未安装 python-docx，无法解析 Word 文件")

    d = docx.Document(path)
    lines: List[str] = []
    for para in d.paragraphs:
        t = para.text.strip()
        if t:
            # 标题样式视为潜在模块名
            style = (para.style.name or "").lower() if para.style is not None else ""
            prefix = "[标题] " if "heading" in style or "标题" in style else ""
            lines.append(prefix + t)
    for table in d.tables:
        for row in table.rows:
            cells = [c.text.strip().replace("\n", " ") for c in row.cells]
            lines.append("\t".join(cells))
    return "\n".join(lines)


# ==================== 确定性解析（规范工作簿） ====================

_HEADER_KEYS = {
    "item": ("检查内容", "检查点", "检查项", "条目"),
    "standard": ("检查要求", "检查标准", "标准", "要求"),
    "scoring": ("评分标准", "评分规则", "评分办法", "扣分"),
    "max": ("分值", "满分", "max", "最高分"),
}


def _match_header(cells: List[str]) -> Optional[Dict[str, int]]:
    """识别表头行 → {字段: 列索引}；识别失败返回 None"""
    mapping: Dict[str, int] = {}
    for idx, cell in enumerate(cells[:12]):
        c = cell.replace(" ", "")
        if not c:
            continue
        for field, keys in _HEADER_KEYS.items():
            if field in mapping:
                continue
            if any(k in c for k in keys):
                mapping[field] = idx
                break
    return mapping if {"item", "standard"} <= mapping.keys() else None


def deterministic_parse_workbook(path: str) -> Optional[Dict[str, Any]]:
    """确定性解析，两条策略：
    A. 每模块一个 sheet（规范工作簿）
    B. 单 sheet 混排、首列为模块名分组（月度行动标准常见形态：行动主题|检查内容|检查要求|评分标准）
    都不满足返回 None（调用方回落 LLM 抽取）"""
    try:
        sheets = extract_workbook(path)
    except Exception:
        return None
    if not sheets:
        return None

    # ---- 策略 A：每模块一 sheet ----
    if len(sheets) >= 2:
        parsed = _parse_per_sheet(sheets)
        if parsed:
            return parsed

    # ---- 策略 B：首列分组混排 ----
    for sh in sheets:
        parsed = _parse_grouped_sheet(sh)
        if parsed:
            return parsed
    return None


_MODULE_COL_KEYS = ("行动主题", "模块", "类别", "分类", "板块", "主题", "专项行动")
_SKIP_ITEM_PAT = re.compile(r"^(小计|合计|总计|满分|总分|评分人|检查人|审核|日期|注[:：]?)")
_ITEM_MAX_PAT = re.compile(r"得\s*(\d+(?:\.\d+)?)\s*分")


def _parse_per_sheet(sheets: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    modules = []
    for sh in sheets:
        header_idx = None
        colmap: Dict[str, int] = {}
        for i, row in enumerate(sh["rows"][:6]):
            colmap = _match_header(row)
            if colmap:
                header_idx = i
                break
        if not colmap:
            return None  # 任一 sheet 无表头 → 整体交给下一策略/LLM

        def cell(row: List[str], field: str) -> str:
            idx = colmap.get(field)
            return row[idx] if idx is not None and idx < len(row) else ""

        items = []
        for row in sh["rows"][header_idx + 1:]:
            name = cell(row, "item")
            if not name or _SKIP_ITEM_PAT.match(name):
                continue
            max_raw = cell(row, "max")
            max_score = float(max_raw) if re.match(r"^\d+(\.\d+)?$", max_raw) else None
            items.append({
                "name": name,
                "standard": cell(row, "standard"),
                "scoring": cell(row, "scoring"),
                "max_score": max_score,
            })
        if items:
            modules.append({"name": sh["sheet"], "items": items})

    if not modules:
        return None
    return {"scoring_model": None, "modules": modules}


def _parse_grouped_sheet(sh: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """单 sheet 首列分组：模块列(前向填充) + 检查项/标准/评分列"""
    rows = sh["rows"]
    header_idx = None
    colmap: Dict[str, int] = {}
    for i, row in enumerate(rows[:6]):
        colmap = _match_header(row)
        if colmap:
            header_idx = i
            break
    if not colmap:
        return None

    # 模块列：表头命中关键词，或 = 未被映射的最左列
    header = rows[header_idx]
    mod_col = None
    for idx, cell_v in enumerate(header[:12]):
        if cell_v and any(k in cell_v.replace(" ", "") for k in _MODULE_COL_KEYS):
            mod_col = idx
            break
    if mod_col is None:
        mapped = set(colmap.values())
        for idx, cell_v in enumerate(header[:12]):
            if idx not in mapped and cell_v:
                mod_col = idx
                break
    if mod_col is None:
        return None

    def cell(row: List[str], field: str) -> str:
        idx = colmap.get(field)
        return row[idx] if idx is not None and idx < len(row) else ""

    def cellat(row: List[str], idx: int) -> str:
        return row[idx] if idx < len(row) else ""

    modules: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    for row in rows[header_idx + 1:]:
        mod_name = cellat(row, mod_col).strip()
        item_name = cell(row, "item").strip()
        if mod_name and mod_name != (current or {}).get("name"):
            current = {"name": mod_name, "items": []}
            modules.append(current)
        if not item_name or _SKIP_ITEM_PAT.match(item_name):
            continue
        if current is None:
            return None  # 首列分组前出现条目 → 布局不符
        scoring = cell(row, "scoring")
        # 评分文本中的「得X分」可确定单项满分
        m = _ITEM_MAX_PAT.search(scoring)
        max_raw = cell(row, "max")
        if re.match(r"^\d+(\.\d+)?$", max_raw):
            max_score = float(max_raw)
        elif m:
            max_score = float(m.group(1))
        else:
            max_score = None
        current["items"].append({
            "name": item_name,
            "standard": cell(row, "standard"),
            "scoring": scoring,
            "max_score": max_score,
        })

    modules = [m for m in modules if m["items"]]
    if len(modules) < 2:  # 单模块不成体系 → 交给 LLM
        return None

    # 计分模型推断：表头含权重列 → weighted_5pt；否则按封顶制处理（月度行动标准家族）
    has_weight = any("权重" in (c or "") for c in header)
    model = "weighted_5pt" if has_weight else "point_cap"

    # 扣分模块：模块名含 5S/扣分，或其全部条目评分都是扣分式表述
    for m in modules:
        if any(k in m["name"] for k in ("5S", "扣分")):
            m["role"] = "deduction"
        elif m["items"] and all("扣" in (it["scoring"] or "") for it in m["items"]):
            m["role"] = "deduction"
        else:
            m["role"] = "score"
    return {"scoring_model": model, "modules": modules}


# ==================== LLM 结构化抽取 ====================

_LLM_PROMPT = """你是物业检查标准结构化引擎。下面是一份检查标准文档的纯文本内容（可能来自 Excel 或 Word，列以制表符分隔）。
请抽取为严格 JSON，形状：
{{"scoring_model": "point_cap 或 weighted_5pt",
 "modules": [{{"name": "模块名", "max_score": 数值或null, "role": "score或deduction",
              "items": [{{"name": "检查项名称", "standard": "检查标准/要求", "scoring": "评分标准/规则", "max_score": 数值或null}}]}}]}}

判定规则：
- point_cap：按分值打分封顶（常见于「礼韵塑新颜」类，模块满分如25分）或扣分制（只减不加）
- weighted_5pt：每项 0-5 分 × 权重，加权汇总为百分制
- 模块名通常是「行动主题」列的去重值，或文档的章节标题；不要遗漏任何条目
- max_score：模块取其条目分值之和或文档标注的模块满分；条目取单项分值
- 只输出 JSON，不要输出任何解释文字

文档内容：
{content}"""


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if m:
        text = m.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


async def parse_with_llm(content: str) -> Optional[Dict[str, Any]]:
    """把纯文本标准交给 LLM 抽取为结构化 JSON（QwenClient 通用对话接口）"""
    from core.llm_client import QwenClient

    content = content[:_MAX_LLM_CHARS]
    client = QwenClient()
    try:
        resp = await client.chat([
            {"role": "system", "content": "你是严格的结构化信息抽取引擎，只输出 JSON。"},
            {"role": "user", "content": _LLM_PROMPT.replace("{content}", content)},
        ])
    except Exception as e:
        logger.error(f"LLM 标准抽取调用失败: {e}")
        return None
    raw = resp.get("content", "")
    parsed = _extract_json(raw)
    if not parsed or not isinstance(parsed.get("modules"), list) or not parsed["modules"]:
        logger.error(f"LLM 标准抽取结果不合法: {raw[:200]}")
        return None
    return _sanitize(parsed)


# ==================== 归一化 ====================

def _sanitize(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """清洗 LLM 输出：字段缺失补默认、分值转数值、role 合法化"""
    model = parsed.get("scoring_model")
    if model not in ("point_cap", "weighted_5pt"):
        model = "point_cap"
    modules = []
    for m in parsed.get("modules", []):
        name = str(m.get("name") or "").strip()
        if not name:
            continue
        items = []
        for it in m.get("items") or []:
            iname = str(it.get("name") or "").strip()
            if not iname:
                continue
            items.append({
                "name": iname,
                "standard": str(it.get("standard") or "").strip(),
                "scoring": str(it.get("scoring") or "").strip(),
                "max_score": _num(it.get("max_score")),
            })
        if not items:
            continue
        modules.append({
            "name": name,
            "max_score": _num(m.get("max_score")),
            "role": "deduction" if str(m.get("role") or "").strip() == "deduction" else "score",
            "weight": _num(m.get("weight")),
            "items": items,
        })
    return {"scoring_model": model, "modules": modules}


def _num(v) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


_PER_DEDUCT_PAT = re.compile(r"扣\s*(\d+(?:\.\d+)?)\s*分")


def _extract_per_deduction(scoring_text: str) -> float:
    """从扣分条目的评分规则提取每处扣分值（如「每发现1人不合格，扣3分」→3.0）；无匹配返回 0.0"""
    m = _PER_DEDUCT_PAT.search(scoring_text or "")
    return float(m.group(1)) if m else 0.0


def finalize(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """计分模型定稿 + 权重/满分补齐（导入入口统一调用）"""
    parsed = _sanitize(parsed)
    model = parsed["scoring_model"]
    n = len(parsed["modules"])
    if not n:
        raise ValueError("未识别到任何检查模块")

    if model == "point_cap":
        for m in parsed["modules"]:
            item_sum = sum(i["max_score"] or 0 for i in m["items"])
            if m["max_score"] is None:
                m["max_score"] = item_sum if item_sum > 0 else 25.0
            for i in m["items"]:
                if i["max_score"] is None:
                    if m["role"] == "deduction":
                        # 扣分条目：max_score 语义=每处扣分值（如「每发现1人不合格，扣3分」→3），
                        # 供 scoring_service 的 per = max_score or 3 直接使用；无匹配则 0（兜底3）
                        i["max_score"] = _extract_per_deduction(i.get("scoring", ""))
                    else:
                        i["max_score"] = 5.0
            if m["role"] == "deduction":
                m["max_score"] = 0.0
    else:
        weights = [m["weight"] for m in parsed["modules"]]
        total_w = sum(w for w in weights if w)
        for i, m in enumerate(parsed["modules"]):
            if not m["weight"]:
                m["weight"] = round((weights[i] or 1.0) / (total_w or n), 4)
            per_item = round(m["weight"] / len(m["items"]), 4) if m["items"] else 0.01
            for it in m["items"]:
                it["weight"] = per_item
                it["max_score"] = 5.0
        # 权重归一化到 1.0
        w_total = sum(m["weight"] for m in parsed["modules"])
        if w_total > 0:
            for m in parsed["modules"]:
                m["weight"] = round(m["weight"] / w_total, 4)

    parsed["items_total"] = sum(len(m["items"]) for m in parsed["modules"])
    return parsed


# ==================== 规范化模板落盘 ====================

def write_normalized_template(std_type: str, parsed: Dict[str, Any]) -> str:
    """生成规范化模板 xlsx（每模块一 sheet），写入 TEMPLATES_DIR；返回文件名"""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    is_cap = parsed["scoring_model"] == "point_cap"

    for m in parsed["modules"]:
        ws = wb.create_sheet(title=m["name"][:31])  # sheet 名上限 31 字符
        if is_cap:
            ws.append(["检查内容", "检查要求", "评分标准", "max_score"])
            for it in m["items"]:
                ws.append([it["name"], it["standard"], it["scoring"], it["max_score"] or 0])
        else:
            ws.append(["检查项", "检查标准", "检查方法", "评分规则", "", "", "", "weight"])
            for it in m["items"]:
                ws.append([it["name"], it["standard"], it["name"], it["scoring"] or "完全符合5分",
                           "", "", "", it["weight"]])

    filename = f"{std_type}.xlsx"
    buf = io.BytesIO()
    wb.save(buf)
    with open(str(settings.TEMPLATES_DIR / filename), "wb") as f:
        f.write(buf.getvalue())
    return filename


def summarize(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """模块/条目摘要（响应给前端确认）"""
    return {
        "scoring_model": parsed["scoring_model"],
        "module_count": len(parsed["modules"]),
        "items_total": parsed.get("items_total", 0),
        "modules": [
            {"name": m["name"], "item_count": len(m["items"]),
             "max_score": m.get("max_score"), "role": m.get("role", "score")}
            for m in parsed["modules"]
        ],
    }
