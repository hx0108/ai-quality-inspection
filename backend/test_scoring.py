"""诊断评分问题"""
import sys
sys.path.insert(0, '.')

from database import SessionLocal
from models.models import (
    InspectionTask, InspectionRecord, ScoringResult, Issue
)
from api.tasks import load_template_items
from config import settings
from sqlalchemy import func

print("=== 评分诊断 ===")
print(f"DASHSCOPE_API_KEY: {settings.DASHSCOPE_API_KEY[:10]}...")

db = SessionLocal()

# 1. 查看所有任务
tasks = db.query(InspectionTask).all()
print(f"\n--- 共 {len(tasks)} 个任务 ---")

for task in tasks:
    print(f"\n任务: {task.task_id} | 项目ID: {task.project_id} | 状态: {task.status}")

    # 查看检查记录
    records = db.query(InspectionRecord).filter(
        InspectionRecord.task_id == task.task_id
    ).all()
    print(f"  检查记录: {len(records)} 条")
    for rec in records:
        print(f"    模块: {rec.module_name} | 状态: {rec.status} | record_id: {rec.record_id}")

        # 查看该记录的问题
        issue_count = db.query(Issue).filter(Issue.record_id == rec.record_id).count()
        print(f"    问题数: {issue_count}")

        # 查看该记录的评分结果
        scoring_results = db.query(ScoringResult).filter(
            ScoringResult.record_id == rec.record_id
        ).all()
        print(f"    评分结果: {len(scoring_results)} 条")
        if scoring_results:
            avg_score = sum(s.score for s in scoring_results) / len(scoring_results)
            print(f"    平均分: {avg_score:.2f}")
        else:
            # 检查模板数据
            standard_type = task.standard_type if task else "diecheng"
            template_items = load_template_items(rec.module_name, standard_type)
            print(f"    **无评分** | 模板项数: {len(template_items)} | standard_type: {standard_type}")
            if not template_items:
                print(f"    >>> 模板数据为空! 这可能是评分失败的原因")

# 2. 查看总分
print(f"\n--- 任务总分 ---")
for task in tasks:
    print(f"  {task.task_id}: total_score={task.total_score}")

db.close()
print("\n=== 诊断完成 ===")
