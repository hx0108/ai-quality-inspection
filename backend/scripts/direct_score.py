"""直接调用评分逻辑，绕过API认证"""
import sys, threading, asyncio
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "/app")

from database import SessionLocal
from models.models import InspectionTask, InspectionRecord, ScoringResult

db = SessionLocal()
task_id = "Q-20260312-d04fcec5"

# Check status
records = db.query(InspectionRecord).filter(
    InspectionRecord.task_id == task_id,
    InspectionRecord.status == "completed"
).all()

print(f"Completed records: {len(records)}")

modules_to_score = []
skipped = []
for r in records:
    count = db.query(ScoringResult).filter(ScoringResult.record_id == r.record_id).count()
    if count > 0:
        skipped.append(f"{r.module_name} ({count} results)")
    else:
        modules_to_score.append(r.module_name)
        print(f"  To score: {r.module_name}")

if skipped:
    print(f"Already scored: {skipped}")

if not modules_to_score:
    print("No modules to score!")
    db.close()
    sys.exit(0)

print(f"\nTriggering LangGraph scoring for {len(modules_to_score)} modules...")

def _run_scoring():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        from agents.scoring import build_scoring_graph
        graph = build_scoring_graph()
        result = loop.run_until_complete(graph.ainvoke({
            "task_id": task_id,
            "records": [],
            "standard_type": "diecheng",
            "scoring_results": [],
            "completed_modules": [],
            "errors": [],
        }))
        print("Scoring complete!")
        print(f"  Completed modules: {result.get('completed_modules', [])}")
        print(f"  Errors: {result.get('errors', [])}")

        # Check total score
        db2 = SessionLocal()
        task = db2.query(InspectionTask).filter(InspectionTask.task_id == task_id).first()
        print(f"  Task total_score: {task.total_score}")
        db2.close()
    except Exception as e:
        print(f"Scoring error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        loop.close()

t = threading.Thread(target=_run_scoring, daemon=False)
t.start()
t.join(timeout=600)  # Wait up to 10 minutes

if t.is_alive():
    print("Scoring still running after 10 min timeout")
else:
    print("Scoring thread finished")

db.close()
