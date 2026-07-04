"""为金域悦府、田心康苑、金域蓝湾补充创建整改记录"""
import sqlite3, sys, os, uuid
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = os.environ.get('DB_PATH', '/app/data/inspection.db')

def gen_id(prefix):
    today = datetime.now().strftime('%Y%m%d')
    return f'{prefix}-{today}-{uuid.uuid4().hex[:8]}'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# 金域悦府和田心康苑: 为所有 issue 创建整改记录
TASKS_FULL = {
    'Q-20260318-c2c1edef': '金域悦府',
    'Q-20260318-41b967ca': '田心康苑',
}

# 金域蓝湾: 先查 task_id
c.execute("SELECT t.task_id FROM inspection_tasks t JOIN projects p ON t.project_id = p.id WHERE p.name = '金域蓝湾'")
jylw_row = c.fetchone()
jylw_task_id = jylw_row['task_id'] if jylw_row else None
print(f'金域蓝湾 task_id: {jylw_task_id}')

# 查金域蓝湾已有整改的模块
if jylw_task_id:
    c.execute("""
        SELECT DISTINCT r.module_name
        FROM rectifications rect
        JOIN issues i ON rect.issue_id = i.issue_id
        JOIN inspection_records r ON i.record_id = r.record_id
        WHERE rect.task_id = ?
    """, (jylw_task_id,))
    existing_modules = [row['module_name'] for row in c.fetchall()]
    print(f'金域蓝湾已有整改模块: {existing_modules}')

now_str = datetime.now().isoformat()

total_created = 0

# === 金域悦府 & 田心康苑 ===
for task_id, label in TASKS_FULL.items():
    print(f'\n=== {label} ({task_id}) ===')

    # Get all issues for this task
    c.execute("""
        SELECT i.issue_id, i.record_id
        FROM issues i
        JOIN inspection_records r ON i.record_id = r.record_id
        WHERE r.task_id = ?
    """, (task_id,))
    issues = c.fetchall()

    # Get existing rectifications
    issue_ids = [iss['issue_id'] for iss in issues]
    placeholders = ','.join(['?'] * len(issue_ids)) if issue_ids else ''
    existing_rects = set()
    if placeholders:
        c.execute(f"SELECT issue_id FROM rectifications WHERE issue_id IN ({placeholders})", issue_ids)
        existing_rects = {row['issue_id'] for row in c.fetchall()}

    created = 0
    for iss in issues:
        if iss['issue_id'] not in existing_rects:
            rect_id = gen_id('RECT')
            c.execute(
                "INSERT INTO rectifications (rectification_id, issue_id, record_id, task_id, status, round_number, created_at, updated_at) VALUES (?, ?, ?, ?, 'pending', 1, ?, ?)",
                (rect_id, iss['issue_id'], iss['record_id'], task_id, now_str, now_str),
            )
            created += 1

    print(f'  Issues: {len(issues)}, Already had rect: {len(existing_rects)}, Created: {created}')
    total_created += created

# === 金域蓝湾: 补充缺失模块 ===
if jylw_task_id:
    print(f'\n=== 金域蓝湾 ({jylw_task_id}) ===')

    # Get issues for modules that DON'T already have rectifications
    c.execute("""
        SELECT i.issue_id, i.record_id, r.module_name
        FROM issues i
        JOIN inspection_records r ON i.record_id = r.record_id
        WHERE r.task_id = ?
    """, (jylw_task_id,))
    all_issues = c.fetchall()

    # Filter to only modules not yet having rectifications
    missing_issues = [iss for iss in all_issues if iss['module_name'] not in existing_modules]

    # Also check if any individual issues in existing modules are missing
    if existing_modules:
        existing_placeholders = ','.join(['?'] * len(existing_modules))
        c.execute(f"""
            SELECT i.issue_id, i.record_id, r.module_name
            FROM issues i
            JOIN inspection_records r ON i.record_id = r.record_id
            WHERE r.task_id = ? AND r.module_name IN ({existing_placeholders})
        """, [jylw_task_id] + existing_modules)
        existing_module_issues = c.fetchall()

        # Check which of these already have rects
        em_issue_ids = [iss['issue_id'] for iss in existing_module_issues]
        if em_issue_ids:
            em_placeholders = ','.join(['?'] * len(em_issue_ids))
            c.execute(f"SELECT issue_id FROM rectifications WHERE issue_id IN ({em_placeholders})", em_issue_ids)
            covered = {row['issue_id'] for row in c.fetchall()}
            uncovered = [iss for iss in existing_module_issues if iss['issue_id'] not in covered]
            missing_issues.extend(uncovered)

    # Deduplicate
    seen = set()
    unique_missing = []
    for iss in missing_issues:
        if iss['issue_id'] not in seen:
            seen.add(iss['issue_id'])
            unique_missing.append(iss)

    # Show per-module breakdown
    from collections import Counter
    module_counts = Counter(iss['module_name'] for iss in unique_missing)
    for mod, cnt in sorted(module_counts.items()):
        print(f'  {mod}: {cnt} issues to create rectifications')

    created = 0
    for iss in unique_missing:
        rect_id = gen_id('RECT')
        c.execute(
            "INSERT INTO rectifications (rectification_id, issue_id, record_id, task_id, status, round_number, created_at, updated_at) VALUES (?, ?, ?, ?, 'pending', 1, ?, ?)",
            (rect_id, iss['issue_id'], iss['record_id'], jylw_task_id, now_str, now_str),
        )
        created += 1

    print(f'  Total created: {created}')
    total_created += created

conn.commit()
conn.close()

print(f'\n{"="*60}')
print(f'DONE. Total rectifications created: {total_created}')
print(f'IMPORTANT: Restart the backend container to clear cache')
print(f'{"="*60}')
