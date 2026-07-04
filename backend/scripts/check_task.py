import sys, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "/app")
from database import SessionLocal
from models.models import InspectionTask, InspectionRecord, Issue
db = SessionLocal()

task_id = "Q-20260312-d04fcec5"
records = db.query(InspectionRecord).filter(InspectionRecord.task_id == task_id).all()
print(f"Total records: {len(records)}")
for r in records:
    print(f"\nRECORD: {r.record_id} | module={r.module_name} | status={r.status}")
    if r.data_json:
        data = json.loads(r.data_json) if isinstance(r.data_json, str) else r.data_json
        items = data.get("items", {})
        checked = sum(1 for v in items.values() if v.get("status") == "checked")
        skipped = sum(1 for v in items.values() if v.get("status") == "skipped")
        pending = sum(1 for v in items.values() if v.get("status") == "pending")
        print(f"  items: total={len(items)}, checked={checked}, skipped={skipped}, pending={pending}")
        for k, v in list(items.items())[:3]:
            print(f"    {k}: {v}")
    else:
        print("  data_json: None")

    issues = db.query(Issue).filter(Issue.record_id == r.record_id).all()
    print(f"  existing issues: {len(issues)}")

db.close()
