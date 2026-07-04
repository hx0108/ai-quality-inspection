"""为金域悦府和田心康苑执行评分（规则回退评分+计算总分）"""
import sys, os, json, uuid
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "inspection.db")
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "templates", "内审检查表V3.0.xlsx")

MODULE_WEIGHTS = {
    "客户服务": 0.15, "安全管理": 0.15, "EHS及风险管理": 0.10,
    "环境管理": 0.15, "机电运维": 0.15, "设施维护": 0.15,
    "综合管理": 0.10, "财务管理": 0.05,
}
PREFIX_MAP = {
    "客户服务": "客户", "安全管理": "安全", "EHS及风险管理": "EH",
    "环境管理": "环境", "机电运维": "机电", "设施维护": "设施",
    "综合管理": "综合", "财务管理": "财务",
}

import openpyxl


def load_template(module_name):
    wb = openpyxl.load_workbook(TEMPLATE_PATH, read_only=True)
    ws = wb[module_name]
    prefix = PREFIX_MAP[module_name]
    items = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=1):
        if not row[0]:
            continue
        item_id = f"{prefix}-{row_idx:03d}"
        items.append({
            "item_id": item_id,
            "item_name": str(row[0]),
            "weight": float(row[7]) if row[7] else 0.01,
            "scoring_rule": str(row[3])[:200] if row[3] else "",
        })
    wb.close()
    return items


def score_task(task_id):
    print(f"\n{'='*60}")
    print(f"开始评分: {task_id}")
    print(f"{'='*60}")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().isoformat()

    # 获取所有检查记录
    c.execute("SELECT record_id, module_name FROM inspection_records WHERE task_id=? ORDER BY id", (task_id,))
    records = c.fetchall()
    print(f"共 {len(records)} 个模块需要评分")

    for record_id, module_name in records:
        # 检查是否已有评分
        c.execute("SELECT COUNT(*) FROM scoring_results WHERE record_id=?", (record_id,))
        if c.fetchone()[0] > 0:
            print(f"  SKIP {module_name}: already scored")
            continue

        template_items = load_template(module_name)
        is_ehs = module_name == "EHS及风险管理"

        # 获取该模块的问题
        c.execute("SELECT item_id, description, severity FROM issues WHERE record_id=?", (record_id,))
        issues_rows = c.fetchall()
        issue_map = {}
        for item_id, desc, severity in issues_rows:
            issue_map[item_id] = {"desc": desc, "severity": severity}

        # 评分每个检查项
        results_to_insert = []
        for item in template_items:
            item_id = item["item_id"]
            weight = item["weight"]

            if is_ehs:
                # EHS模块：全部跳过，给5分
                score = 5.0
                scoring_basis = "EHS模块本次检查不参与评分"
                is_skipped = True
                is_fallback = False
                suggestion = ""
            elif item_id in issue_map:
                # 有问题：基于严重程度扣分
                issue = issue_map[item_id]
                severity = issue["severity"]
                if severity == "严重":
                    deduction = 2.0
                elif severity == "轻微":
                    deduction = 0.5
                else:
                    deduction = 1.0
                score = max(0, round(5.0 - deduction, 1))
                scoring_basis = f"发现{severity}问题：{issue['desc'][:80]}，扣{deduction}分，得{score}分"
                is_skipped = False
                is_fallback = True
                if severity == "严重":
                    suggestion = "建议立即整改严重问题并提交复查"
                else:
                    suggestion = "建议制定整改计划并在规定期限内完成"
            else:
                # 无问题：满分5分
                score = 5.0
                scoring_basis = "检查合格，无问题发现，给予满分5分"
                is_skipped = False
                is_fallback = False
                suggestion = ""

            weighted_score = round(score * weight, 6)
            results_to_insert.append((
                f"SCR-{uuid.uuid4().hex[:12]}",
                record_id, module_name, item_id, item["item_name"],
                score, weight, weighted_score,
                scoring_basis, suggestion,
                is_skipped, now, is_fallback,
                item.get("scoring_rule", ""),
            ))

        # 批量插入评分结果
        c.executemany("""
            INSERT INTO scoring_results (scoring_id, record_id, module_name, item_id, item_name,
                score, weight, weighted_score, scoring_basis, improvement_suggestion,
                is_skipped, scored_at, is_fallback, scoring_rule)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, results_to_insert)
        conn.commit()

        issue_count = len(issue_map)
        print(f"  ✓ {module_name}: {len(results_to_insert)} items scored ({issue_count} issues)")

    # 计算模块百分制得分和项目总分
    c.execute("""SELECT sr.module_name, sr.weighted_score, sr.weight
        FROM scoring_results sr
        JOIN inspection_records r ON sr.record_id = r.record_id
        WHERE r.task_id=?""", (task_id,))
    all_results = c.fetchall()

    modules_data = {}
    for module_name, ws, w in all_results:
        if module_name not in modules_data:
            modules_data[module_name] = {"raw_score_sum": 0, "weight_sum": 0}
        modules_data[module_name]["raw_score_sum"] += float(ws)
        modules_data[module_name]["weight_sum"] += float(w)

    # 更新 module_pct_score
    for module_name, data in modules_data.items():
        if data["weight_sum"] > 0:
            pct = round((data["raw_score_sum"] / (5 * data["weight_sum"])) * 100, 2)
            record_ids = [r[0] for r in records if r[1] == module_name]
            for rid in record_ids:
                c.execute("UPDATE scoring_results SET module_pct_score=? WHERE record_id=? AND module_name=?",
                          (pct, rid, module_name))
            print(f"  {module_name} pct_score: {pct}")

    # 计算项目总分
    project_total = 0
    for module_name, module_weight in MODULE_WEIGHTS.items():
        data = modules_data.get(module_name)
        if data and data["weight_sum"] > 0:
            module_pct = (data["raw_score_sum"] / (5 * data["weight_sum"])) * 100
            project_total += module_pct * module_weight

    project_total = round(project_total, 2)
    c.execute("UPDATE inspection_tasks SET total_score=?, status='completed', updated_at=? WHERE task_id=?",
              (project_total, now, task_id))
    conn.commit()

    print(f"\n  ★ 项目总分: {project_total}")

    # 最终验证
    c.execute("SELECT total_score, status FROM inspection_tasks WHERE task_id=?", (task_id,))
    t = c.fetchone()
    print(f"  验证: total_score={t[0]}, status={t[1]}")

    c.execute("""SELECT r.module_name, COUNT(sr.scoring_id) as cnt
        FROM inspection_records r
        LEFT JOIN scoring_results sr ON r.record_id = sr.record_id
        WHERE r.task_id=?
        GROUP BY r.module_name ORDER BY r.id""", (task_id,))
    for row in c.fetchall():
        print(f"    {row[0]}: {row[1]} scoring results")

    conn.close()
    return project_total


if __name__ == "__main__":
    score_jyyf = score_task("Q-20260601-963a3c44")
    score_txky = score_task("Q-20260601-b401e3f3")

    print(f"\n{'='*60}")
    print(f"金域悦府总分: {score_jyyf}")
    print(f"田心康苑总分: {score_txky}")
    print(f"{'='*60}")
