import sqlite3, sys, uuid
sys.stdout.reconfigure(encoding='utf-8')
db = sqlite3.connect('/app/data/inspection.db')
c = db.cursor()

renames = {
    'Q-20260531-2e2d3f90': 'Q-20260318-' + uuid.uuid4().hex[:8],
    'Q-20260531-df8d2e00': 'Q-20260318-' + uuid.uuid4().hex[:8],
}
new_date = '2026-03-18'

for old_tid, new_tid in renames.items():
    c.execute('SELECT COUNT(*) FROM inspection_tasks WHERE task_id=?', (old_tid,))
    cnt = c.fetchone()[0]
    print(f'{old_tid} exists: {cnt}')

    c.execute('UPDATE inspection_records SET task_id=?, check_date=? WHERE task_id=?',
              (new_tid, new_date, old_tid))
    print(f'  records: {c.rowcount}')

    c.execute('UPDATE inspection_tasks SET task_id=?, check_date=? WHERE task_id=?',
              (new_tid, new_date, old_tid))
    print(f'  task: {c.rowcount}')

db.commit()

c.execute("SELECT t.task_id, p.name, t.check_date, t.total_score FROM inspection_tasks t JOIN projects p ON t.project_id=p.id WHERE t.task_id LIKE 'Q-20260318%'")
for r in c.fetchall():
    print(f'  {r[0]} | {r[1]} | {r[2]} | {r[3]}')
db.close()
print('Done')
