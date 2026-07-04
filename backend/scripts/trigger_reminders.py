"""清除旧通知 + 重置reminder_sent + 重新触发"""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "/app")
os.chdir("/app")

from database import SessionLocal
from models.models import Rectification, Notification

db = SessionLocal()
# Clear old notifications
db.query(Notification).delete()
# Reset reminder_sent
for r in db.query(Rectification).filter(Rectification.reminder_sent.isnot(None)).all():
    r.reminder_sent = None
db.commit()
db.close()
print("Cleared old data")

# Trigger
from main import _scheduled_rectification_reminders
_scheduled_rectification_reminders()

import sqlite3
c = sqlite3.connect("/app/data/inspection.db").cursor()
c.execute("SELECT COUNT(*) FROM notifications")
total = c.fetchone()[0]
print(f"\nNotifications: {total}")
c.execute("SELECT title, content FROM notifications")
for r in c.fetchall():
    print(f"  [{r[0]}] {r[1][:80]}")
c.execute("SELECT DISTINCT username FROM notifications")
print(f"Users: {[r[0] for r in c.fetchall()]}")
