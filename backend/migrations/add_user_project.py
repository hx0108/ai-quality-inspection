"""
迁移：为 users 表增加 project_id 列
"""
import sys
sys.path.insert(0, r'c:\Users\ASUS\Desktop\AI Agent\品质检查项目组\backend')

import os
os.chdir(r'c:\Users\ASUS\Desktop\AI Agent\品质检查项目组\backend')

from database import SessionLocal, engine
import sqlite3

def run():
    # SQLite 直接 ALTER TABLE
    conn = sqlite3.connect('inspection.db')
    cursor = conn.cursor()

    # 检查列是否存在
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'project_id' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN project_id INTEGER REFERENCES projects(id)")
        conn.commit()
        print("users.project_id 列已添加")
    else:
        print("users.project_id 列已存在，跳过")

    conn.close()
    print("迁移完成")

if __name__ == '__main__':
    run()
