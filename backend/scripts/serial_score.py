import sys, threading, asyncio, json, time
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "/app")
from database import SessionLocal
from models.models import InspectionTask, InspectionRecord, ScoringResult

task_id = "Q-20260312-d04fcec5"
modules = ["安全管理", "EHS及风险管理", "环境管理", "机电运维", "设施维护", "综合管理", "财务管理"]

for mod in modules:
    db = SessionLocal()
    record = db.query(InspectionRecord).filter(
        InspectionRecord.task_id == task_id,
        InspectionRecord.module_name == mod
    ).first()
    if not record:
        print("SKIP", mod, ": no record")
        db.close()
        continue

    count = db.query(ScoringResult).filter(ScoringResult.record_id == record.record_id).count()
    if count > 0:
        print("SKIP", mod, ": already has", count, "results")
        db.close()
        continue

    db.close()
    print("Scoring", mod, "...")

    def _run(mod_name=mod):
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
            errs = result.get("errors", [])
            if errs:
                print("  ", mod_name, "error:", str(errs[0])[:100])
            else:
                completed = result.get("completed_modules", [])
                print("  ", mod_name, "OK, completed:", len(completed), "modules total")
        except Exception as e:
            print("  ", mod_name, "failed:", e)
        finally:
            loop.close()

    t = threading.Thread(target=_run, daemon=False)
    t.start()
    t.join(timeout=300)
    time.sleep(3)

# Final check
db = SessionLocal()
task = db.query(InspectionTask).filter(InspectionTask.task_id == task_id).first()
print("")
print("Final total_score:", task.total_score)
for r in db.query(InspectionRecord).filter(InspectionRecord.task_id == task_id).all():
    cnt = db.query(ScoringResult).filter(ScoringResult.record_id == r.record_id).count()
    print("  ", r.module_name, ":", cnt, "scoring results")
db.close()
