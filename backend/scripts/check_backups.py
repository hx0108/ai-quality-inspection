"""Check multiple backup files to find original production data"""
import tarfile, sqlite3, sys, os
sys.stdout.reconfigure(encoding='utf-8')
backup_dir = '/app/data/backups'

# Check key backups across the timeline
targets = [
    'backup_hourly_20260531_094116.tar.gz',
    'backup_hourly_20260530_092116.tar.gz',
    'backup_hourly_20260529_092116.tar.gz',
    'backup_daily_20260527_030117.tar.gz',
    'backup_daily_20260526_030117.tar.gz',
]

for name in targets:
    path = os.path.join(backup_dir, name)
    if not os.path.exists(path):
        print(f'{name}: NOT FOUND')
        continue
    try:
        with tarfile.open(path, 'r:gz') as tar:
            for member in tar.getmembers():
                if member.name.endswith('inspection.db') and '-wal' not in member.name and '-shm' not in member.name:
                    f = tar.extractfile(member)
                    if f:
                        db_data = f.read()
                        tmp = '/tmp/check_' + name.replace('.tar.gz', '.db')
                        with open(tmp, 'wb') as out:
                            out.write(db_data)
                        db = sqlite3.connect(tmp)
                        c = db.cursor()
                        c.execute('SELECT COUNT(*) FROM inspection_tasks')
                        tasks = c.fetchone()[0]
                        c.execute('SELECT COUNT(*) FROM users')
                        users = c.fetchone()[0]
                        c.execute('SELECT COUNT(*) FROM scoring_results')
                        scores = c.fetchone()[0]
                        c.execute('SELECT p.name, t.status, t.total_score FROM inspection_tasks t JOIN projects p ON t.project_id=p.id ORDER BY t.id DESC')
                        task_lines = []
                        for r in c.fetchall():
                            score_str = str(r[2]) if r[2] else '-'
                            task_lines.append('{}({}/{})'.format(r[0], r[1], score_str))
                        db.close()
                        os.unlink(tmp)
                        print('{}: {} tasks, {} users, {} scores'.format(name, tasks, users, scores))
                        print('  Tasks: {}'.format(', '.join(task_lines)))
                        break
    except Exception as e:
        print('{}: ERROR {}'.format(name, e))
