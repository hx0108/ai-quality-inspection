"""
数据迁移脚本：将 users.project_id 迁移到 user_projects 多对多表
"""
from database import engine
from sqlalchemy import text, inspect

def migrate():
    with engine.connect() as conn:
        # 1. 创建 user_projects 表（如果不存在）
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """))
        conn.commit()
        print("[OK] user_projects 表已确保存在")

        # 2. 迁移现有数据
        rows = conn.execute(text(
            "SELECT id, project_id FROM users WHERE project_id IS NOT NULL"
        )).fetchall()

        migrated = 0
        for user_id, project_id in rows:
            # 检查是否已存在
            existing = conn.execute(text(
                "SELECT id FROM user_projects WHERE user_id = :uid AND project_id = :pid"
            ), {"uid": user_id, "pid": project_id}).fetchone()

            if not existing:
                conn.execute(text(
                    "INSERT INTO user_projects (user_id, project_id) VALUES (:uid, :pid)"
                ), {"uid": user_id, "pid": project_id})
                migrated += 1

        conn.commit()
        print(f"[OK] 迁移完成：{len(rows)} 个用户有项目绑定，新插入 {migrated} 条记录")

        # 3. 验证
        total = conn.execute(text("SELECT COUNT(*) FROM user_projects")).scalar()
        print(f"[OK] user_projects 表现有 {total} 条记录")


if __name__ == "__main__":
    migrate()
