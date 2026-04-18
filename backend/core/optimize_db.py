"""
数据库性能优化 - 添加缺失索引
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine


def add_performance_indexes():
    """添加性能优化索引"""
    indexes = [
        # 用户表索引
        ("idx_users_role", "users", "role"),

        # 任务表索引
        ("idx_tasks_status", "inspection_tasks", "status"),
        ("idx_tasks_project_id", "inspection_tasks", "project_id"),
        ("idx_tasks_created_at", "inspection_tasks", "created_at"),

        # 检查记录表索引
        ("idx_records_task_id", "inspection_records", "task_id"),
        ("idx_records_status", "inspection_records", "status"),
        ("idx_records_inspector_id", "inspection_records", "inspector_id"),

        # 任务分配表索引
        ("idx_assignments_task_module", "task_assignments", "task_id, module_name"),

        # 问题表索引
        ("idx_issues_record_id", "issues", "record_id"),
        ("idx_issues_severity", "issues", "severity"),

        # 评分结果表索引
        ("idx_scoring_record_id", "scoring_results", "record_id"),

        # 报告表索引
        ("idx_reports_task_id", "reports", "task_id"),
        ("idx_reports_project_id", "reports", "project_id"),
        ("idx_reports_generated_at", "reports", "generated_at"),

        # 整改表索引
        ("idx_rectifications_status", "rectifications", "status"),
        ("idx_rectifications_task_id", "rectifications", "task_id"),

        # 复合索引 - 常见查询模式
        ("idx_records_task_module", "inspection_records", "task_id, module_name"),
        ("idx_rectifications_status_task", "rectifications", "task_id, status"),
    ]

    with engine.connect() as conn:
        for idx_name, table, columns in indexes:
            try:
                # 检查索引是否已存在
                result = conn.execute(text(f"PRAGMA index_info({idx_name})"))
                existing = result.fetchall()

                if not existing:
                    # 构建 CREATE INDEX 语句
                    col_list = columns.replace(",", ", ")
                    sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({col_list})"
                    conn.execute(text(sql))
                    print(f"创建索引: {idx_name}")
                else:
                    print(f"索引已存在: {idx_name}")
            except Exception as e:
                print(f"索引 {idx_name} 创建失败: {e}")

        conn.commit()

    print("\n索引优化完成!")


def analyze_tables():
    """分析表，获取查询优化建议"""
    tables = [
        "users", "projects", "inspection_tasks", "task_assignments",
        "inspection_records", "issues", "photos", "scoring_results",
        "reports", "rectifications"
    ]

    with engine.connect() as conn:
        print("\n表统计信息:")
        print("-" * 50)
        for table in tables:
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"{table}: {count} 条记录")
            except:
                print(f"{table}: 无法统计")


if __name__ == "__main__":
    print("开始数据库性能优化...")
    add_performance_indexes()
    analyze_tables()
