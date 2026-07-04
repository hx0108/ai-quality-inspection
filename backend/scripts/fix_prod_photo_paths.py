"""Fix production photo file_path: relative -> absolute paths"""
import sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = '/app/data/inspection.db'
PHOTOS_BASE = '/app/data'

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Find all photos with relative paths (not starting with /)
c.execute("SELECT id, file_path FROM photos WHERE file_path NOT LIKE '/%'")
rows = c.fetchall()
print(f'Photos with relative paths: {len(rows)}')

fixed = 0
missing = 0
for row_id, fpath in rows:
    abs_path = os.path.join(PHOTOS_BASE, fpath)
    if os.path.exists(abs_path):
        c.execute('UPDATE photos SET file_path = ? WHERE id = ?', (abs_path, row_id))
        fixed += 1
    else:
        missing += 1
        if missing <= 5:
            print(f'  STILL MISSING: {abs_path}')

conn.commit()
conn.close()

print(f'\nFixed: {fixed}, Missing files: {missing}')
print('IMPORTANT: Restart the backend container to clear cache!')
