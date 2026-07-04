import sqlite3, sys, uuid
sys.stdout.reconfigure(encoding='utf-8')
db = sqlite3.connect('/root/品质检查项目组/data/inspection.db')
c = db.cursor()

# Find by project_id instead of task_id
for project_id, name in [(3, '金域悦府'), (2, '田心康苑')]:
    new_tid = 'Q-20260318-' + uuid.uuid4().hex[:8]

    # Get current task rowid and task_id
    c.execute('SELECT rowid, task_id FROM inspection_tasks WHERE project_id=? ORDER BY id DESC LIMIT 1', (project_id,))
    row = c.fetchone()
    if not row:
        print(name + ': NOT FOUND')
        continue
    rowid, old_tid = row
    print(name + ': rowid=' + str(rowid) + ' old_tid=' + repr(old_tid) + ' len=' + str(len(old_tid)))

    # Show hex of task_id
    print('  hex: ' + old_tid.encode('utf-8').hex())

    # Update by rowid instead
    c.execute('UPDATE inspection_records SET task_id=?, check_date=? WHERE task_id=?', (new_tid, '2026-03-18', old_tid))
    r1 = c.rowcount

    # If param match fails, try by joining records to task rowid
    if r1 == 0:
        c.execute('UPDATE inspection_records SET task_id=?, check_date=? WHERE rowid IN (SELECT r.rowid FROM inspection_records r WHERE r.project_id=? AND r.task_id IN (SELECT t.task_id FROM inspection_tasks t WHERE t.project_id=?))', (new_tid, '2026-03-18', project_id, project_id))
        r1 = c.rowcount

    c.execute('UPDATE inspection_tasks SET task_id=?, check_date=? WHERE rowid=?', (new_tid, '2026-03-18', rowid))
    r2 = c.rowcount

    print('  -> ' + new_tid + ' records=' + str(r1) + ' task=' + str(r2))

db.commit()

# Verify
c.execute("SELECT t.task_id, p.name, t.check_date FROM inspection_tasks t JOIN projects p ON t.project_id=p.id WHERE p.id IN (2,3)")
for r in c.fetchall():
    print('OK: ' + r[0] + ' | ' + r[1] + ' | ' + r[2])
db.close()
