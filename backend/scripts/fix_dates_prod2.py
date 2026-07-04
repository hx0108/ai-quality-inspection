import sqlite3, sys, uuid
sys.stdout.reconfigure(encoding='utf-8')
db = sqlite3.connect('/app/data/inspection.db')
c = db.cursor()

old_ids = [
    ('Q-20260531-2e2d3f90', 'Q-20260318-' + uuid.uuid4().hex[:8]),
    ('Q-20260531-df8d2e00', 'Q-20260318-' + uuid.uuid4().hex[:8]),
]

for old_id, new_id in old_ids:
    sql1 = "UPDATE inspection_records SET task_id='" + new_id + "', check_date='2026-03-18' WHERE task_id='" + old_id + "'"
    c.execute(sql1)
    r1 = c.rowcount
    sql2 = "UPDATE inspection_tasks SET task_id='" + new_id + "', check_date='2026-03-18' WHERE task_id='" + old_id + "'"
    c.execute(sql2)
    r2 = c.rowcount
    print(old_id + ' -> ' + new_id + ' records=' + str(r1) + ' task=' + str(r2))

db.commit()

c.execute("SELECT task_id, check_date FROM inspection_tasks WHERE task_id LIKE 'Q-20260318%'")
for r in c.fetchall():
    print('OK: ' + r[0] + ' date=' + r[1])
db.close()
