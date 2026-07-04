import sqlite3, sys, os
sys.stdout.reconfigure(encoding='utf-8')
db_path = '/root/品质检查项目组/data/inspection.db'
for ext in ['-wal', '-shm']:
    p = db_path + ext
    if os.path.exists(p):
        os.remove(p)
        print('Removed ' + p)
old_db = sqlite3.connect(db_path)
with open('/tmp/dump.sql', 'w', encoding='utf-8') as f:
    for line in old_db.iterdump():
        f.write(line + '\n')
old_db.close()
os.remove(db_path)
new_db = sqlite3.connect(db_path)
with open('/tmp/dump.sql', 'r', encoding='utf-8') as f:
    sql = f.read()
new_db.executescript(sql)
new_db.commit()
c = new_db.cursor()
c.execute('SELECT COUNT(*) FROM inspection_tasks')
print('Tasks: ' + str(c.fetchone()[0]))
c.execute('SELECT COUNT(*) FROM inspection_records')
print('Records: ' + str(c.fetchone()[0]))
c.execute('SELECT COUNT(*) FROM scoring_results')
print('ScoringResults: ' + str(c.fetchone()[0]))
c.execute('SELECT COUNT(*) FROM users')
print('Users: ' + str(c.fetchone()[0]))
new_db.close()
os.remove('/tmp/dump.sql')
print('DB fixed')
