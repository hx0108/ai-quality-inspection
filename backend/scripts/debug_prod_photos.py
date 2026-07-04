"""Debug: check photo data in production DB"""
import sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = '/app/data/inspection.db'
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

for task_id, label in [('Q-20260318-c2c1edef', '金域悦府'), ('Q-20260318-41b967ca', '田心康苑')]:
    print(f'\n=== {label} ({task_id}) ===')

    # Records
    c.execute('SELECT record_id, module_name FROM inspection_records WHERE task_id=?', (task_id,))
    records = c.fetchall()
    print(f'  Records: {len(records)}')

    for record_id, module_name in records:
        c.execute('SELECT issue_id, item_id FROM issues WHERE record_id=?', (record_id,))
        issues = c.fetchall()
        if not issues:
            continue

        issue_ids = [iss[0] for iss in issues]
        placeholders = ','.join(['?'] * len(issue_ids))
        c.execute(f'SELECT photo_id, file_path, issue_id FROM photos WHERE issue_id IN ({placeholders})', issue_ids)
        photos = c.fetchall()

        if photos:
            print(f'  {module_name} ({record_id}): {len(issues)} issues, {len(photos)} photos')
            for p in photos[:2]:
                exists = os.path.exists(p[1])
                print(f'    {p[0]} issue={p[2]} exists={exists}')

# Check: the scoring_results record_id vs inspection_records record_id
print('\n=== Scoring record_id check ===')
c.execute("""
SELECT DISTINCT sr.record_id, r.record_id, sr.module_name
FROM scoring_results sr
JOIN inspection_records r ON sr.task_id IS NOT NULL
WHERE sr.record_id NOT IN (SELECT record_id FROM inspection_records WHERE task_id='Q-20260318-c2c1edef')
AND sr.module_name = '安全管理'
LIMIT 5
""")
# Better: check what record_id scoring_results uses for this task
c.execute("""
SELECT DISTINCT sr.record_id
FROM scoring_results sr
JOIN inspection_records r ON sr.record_id = r.record_id
WHERE r.task_id = 'Q-20260318-c2c1edef'
AND sr.module_name = '安全管理'
""")
rec_ids = c.fetchall()
print(f'  scoring_results record_ids for 金域悦府/安全管理: {[r[0] for r in rec_ids]}')

# What record_ids do issues use?
c.execute("""
SELECT DISTINCT record_id FROM issues
WHERE record_id IN (SELECT record_id FROM inspection_records WHERE task_id='Q-20260318-c2c1edef')
AND module_name = '安全管理'
""")
iss_rec_ids = c.fetchall()
print(f'  issues record_ids for 金域悦府/安全管理: {[r[0] for r in iss_rec_ids]}')

conn.close()
