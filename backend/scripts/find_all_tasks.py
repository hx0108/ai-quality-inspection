import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "/app")
from database import SessionLocal
from models.models import InspectionTask, InspectionRecord, Issue, Photo, Project
db = SessionLocal()
projects = {p.id: p.name for p in db.query(Project).all()}
for t in db.query(InspectionTask).order_by(InspectionTask.id.desc()).limit(10).all():
    pname = projects.get(t.project_id, "?")
    rec_count = db.query(InspectionRecord).filter(InspectionRecord.task_id == t.task_id).count()
    issue_count = db.query(Issue).join(InspectionRecord).filter(InspectionRecord.task_id == t.task_id).count()
    print("TASK:", t.task_id, "| project:", pname, "| date:", t.check_date, "| status:", t.status, "| score:", t.total_score, "| records:", rec_count, "| issues:", issue_count)
db.close()
