import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "/app")
from database import SessionLocal
from models.models import InspectionTask, InspectionRecord, ScoringResult
db = SessionLocal()
for tid in ["Q-20260318-e198ba12", "Q-20260318-bf020a84"]:
    t = db.query(InspectionTask).filter(InspectionTask.task_id == tid).first()
    if not t:
        print("TASK:", tid, "NOT FOUND")
        continue
    recs = db.query(InspectionRecord).filter(InspectionRecord.task_id == tid).all()
    total_scores = 0
    for r in recs:
        cnt = db.query(ScoringResult).filter(ScoringResult.record_id == r.record_id).count()
        total_scores += cnt
    print("TASK:", tid, "score=", t.total_score, "status=", t.status, "scored_items=", total_scores)
    for r in recs:
        cnt = db.query(ScoringResult).filter(ScoringResult.record_id == r.record_id).count()
        print("    ", r.module_name, "scores=", cnt)
db.close()
