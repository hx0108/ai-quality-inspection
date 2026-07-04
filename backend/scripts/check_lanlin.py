import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
db = sqlite3.connect('/app/data/inspection.db')
c = db.cursor()

c.execute("SELECT t.task_id, p.name, t.status, t.check_date, t.total_score FROM inspection_tasks t JOIN projects p ON t.project_id=p.id WHERE p.name LIKE '%岚林%'")
rows = c.fetchall()
print('Tasks found: ' + str(len(rows)))
for r in rows:
    print('Task: ' + str(r))
    task_id = r[0]
    c.execute('SELECT module_name, status FROM inspection_records WHERE task_id=? ORDER BY id', (task_id,))
    for rec in c.fetchall():
        print('  ' + rec[0] + ': ' + rec[1])
    c.execute('SELECT COUNT(*) FROM scoring_results sr JOIN inspection_records r ON sr.record_id=r.record_id WHERE r.task_id=?', (task_id,))
    print('  ScoringResults: ' + str(c.fetchone()[0]))
    c.execute('SELECT report_id, version, total_score, generated_at FROM reports WHERE task_id=?', (task_id,))
    for rep in c.fetchall():
        print('  Report: ' + str(rep))
    # count completed modules
    c.execute('SELECT COUNT(*) FROM inspection_records WHERE task_id=? AND status=?', (task_id, 'completed'))
    print('  Completed modules: ' + str(c.fetchone()[0]))
    print()

db.close()
