"""Check: what file_path does DB have, and do files exist on disk?"""
import sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('/app/data/inspection.db')
c = conn.cursor()

# 金域悦府 安全管理
c.execute("""
SELECT p.photo_id, p.file_path
FROM photos p
JOIN issues i ON p.issue_id = i.issue_id
WHERE i.record_id = 'REC-20260531-1ceaba6a'
LIMIT 5
""")
print('金域悦府 安全管理 photos:')
for pid, fpath in c.fetchall():
    exists = os.path.exists(fpath)
    parent_exists = os.path.exists(os.path.dirname(fpath))
    print(f'  {pid} | exists={exists} | parent_exists={parent_exists}')
    print(f'    path: {fpath}')

# List what's actually in the REC directory
rec_dir = '/app/data/photos/REC-20260531-1ceaba6a'
if os.path.exists(rec_dir):
    files = os.listdir(rec_dir)
    print(f'\n  Files in {rec_dir}: {len(files)}')
    for f in files[:5]:
        print(f'    {f}')
else:
    print(f'\n  Directory {rec_dir} does NOT exist')

conn.close()
