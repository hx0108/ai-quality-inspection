import sqlite3, sys, uuid
sys.stdout.reconfigure(encoding='utf-8')
db = sqlite3.connect('/root/品质检查项目组/data/inspection.db')
c = db.cursor()
c.execute("SELECT t.task_id, p.name FROM inspection_tasks t JOIN projects p ON t.project_id=p.id WHERE p.name IN ('金域悦府','田心康苑')")
rows = c.fetchall()
print('Found: ' + str(len(rows)))
for old_tid, name in rows:
    new_tid = 'Q-20260318-' + uuid.uuid4().hex[:8]
    c.execute('UPDATE inspection_records SET task_id=?, check_date=? WHERE task_id=?', (new_tid, '2026-03-18', old_tid))
    r1 = c.rowcount
    c.execute('UPDATE inspection_tasks SET task_id=?, check_date=? WHERE task_id=?', (new_tid, '2026-03-18', old_tid))
    r2 = c.rowcount
    print(name + ': ' + old_tid + ' -> ' + new_tid + ' records=' + str(r1) + ' task=' + str(r2))
db.commit()
c.execute("SELECT t.task_id, p.name, t.check_date FROM inspection_tasks t JOIN projects p ON t.project_id=p.id WHERE t.task_id LIKE 'Q-20260318%'")
for r in c.fetchall():
    print('OK: ' + r[0] + ' | ' + r[1] + ' | ' + r[2])
db.close()
