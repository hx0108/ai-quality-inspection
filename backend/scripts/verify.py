import sys, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "/app")
from database import SessionLocal
from models.models import InspectionRecord, Issue, Photo, InspectionTask
db = SessionLocal()

task_id = "Q-20260312-d04fcec5"
task = db.query(InspectionTask).filter(InspectionTask.task_id == task_id).first()
print("Task:", task.task_id, "status=", task.status, "total_score=", task.total_score)

records = db.query(InspectionRecord).filter(InspectionRecord.task_id == task_id).all()
print("\nRecords:", len(records))
total_issues = 0
total_photos = 0
for r in records:
    issues = db.query(Issue).filter(Issue.record_id == r.record_id).all()
    photos = db.query(Photo).join(Issue).filter(Issue.record_id == r.record_id).count()
    total_issues += len(issues)
    total_photos += photos
    print("  ", r.module_name, ": status=", r.status, "issues=", len(issues), "photos=", photos)

print("\nTotal:", len(records), "records,", total_issues, "issues,", total_photos, "photos")
db.close()
