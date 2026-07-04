import sqlite3, sys
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding="utf-8")
c = sqlite3.connect("/app/data/inspection.db").cursor()
today = datetime.now().strftime("%Y-%m-%d")
exp5 = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
over1 = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
print(f"Today={today} Expiring={exp5} Overdue={over1}")
c.execute("SELECT deadline, COUNT(*) FROM rectifications WHERE status='pending' GROUP BY deadline ORDER BY deadline")
for r in c.fetchall():
    tag = " <-- MATCH" if r[0] in (exp5, over1) else ""
    print(f"  {r[0]}: {r[1]}{tag}")
