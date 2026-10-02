"""直接在宿主机上触发整改提醒，写入共享数据库"""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "/root/品质检查项目组/backend")

from datetime import datetime, timedelta
from collections import defaultdict, Counter
import sqlite3

DB_PATH = "/root/品质检查项目组/data/inspection.db"
today = datetime.now()
today_str = today.strftime("%Y-%m-%d")
exp5 = (today + timedelta(days=5)).strftime("%Y-%m-%d")
over1 = (today - timedelta(days=1)).strftime("%Y-%m-%d")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()
wecom_lines = []  # 企业微信群推送汇总

# Clear old notifications
c.execute("DELETE FROM notifications")
conn.commit()
print("Cleared old notifications")

for deadline, reminder_type, label in [
    (exp5, "expiring", "即将到期"),
    (over1, "expired", "已逾期"),
]:
    # Find matching pending rectifications
    c.execute("""
        SELECT r.rectification_id, r.task_id, r.reminder_sent,
               i.module_name
        FROM rectifications r
        LEFT JOIN issues i ON r.issue_id = i.issue_id
        WHERE r.status = 'pending' AND r.deadline = ?
    """, (deadline,))
    rects = c.fetchall()
    # Filter reminder_sent
    rects = [r for r in rects if r["reminder_sent"] != reminder_type]
    if not rects:
        continue

    # Group by task_id (project)
    by_task = defaultdict(list)
    for r in rects:
        by_task[r["task_id"]].append(r)

    for task_id, task_rects in by_task.items():
        # Get project name
        c.execute("""
            SELECT p.name, t.project_id
            FROM inspection_tasks t
            JOIN projects p ON t.project_id = p.id
            WHERE t.task_id = ?
        """, (task_id,))
        task_info = c.fetchone()
        if not task_info:
            continue
        project_name = task_info["name"]
        project_id = task_info["project_id"]

        # Count by module
        module_counts = Counter()
        for r in task_rects:
            module_counts[r["module_name"] or "未知"] += 1
        total_count = sum(module_counts.values())
        module_detail = "、".join(f"{m}{cnt}项" for m, cnt in module_counts.items())

        if reminder_type == "expiring":
            title = f"整改即将到期 - {project_name}"
            content = f"项目「{project_name}」有{total_count}条整改将于5天后到期（截止：{deadline}），涉及：{module_detail}。请尽快督促整改。"
            wecom_lines.append(f"🟡 **{project_name}**：{total_count}条即将到期（{module_detail}）")
        else:
            title = f"整改已逾期 - {project_name}"
            content = f"项目「{project_name}」有{total_count}条整改已逾期（截止：{deadline}），涉及：{module_detail}。请立即处理。"
            wecom_lines.append(f"🔴 **{project_name}**：{total_count}条已逾期（{module_detail}）")

        # Find recipients
        recipients = set()
        # Field supervisors
        c.execute("""
            SELECT u.id, u.username FROM users u
            JOIN user_projects up ON u.id = up.user_id
            WHERE up.project_id = ? AND u.role = 'field_supervisor' AND u.is_active = 1
        """, (project_id,))
        for r in c.fetchall():
            recipients.add((r["id"], r["username"]))
        # Admins
        c.execute("SELECT id, username FROM users WHERE role = 'admin' AND is_active = 1")
        for r in c.fetchall():
            recipients.add((r["id"], r["username"]))

        # Write notifications
        import random
        for user_id, username in recipients:
            nid = f"NTF-{today.strftime('%Y%m%d')}-{random.randint(100000, 999999)}"
            now = datetime.now().isoformat()
            c.execute(
                "INSERT INTO notifications (notification_id, user_id, username, title, content, notify_type, ref_type, ref_id, is_read, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)",
                (nid, user_id, username, title, content, "rectification_reminder", "task", task_id, now)
            )
            print(f"  -> {username}: [{title}]")

    # Mark reminder_sent
    for r in rects:
        c.execute("UPDATE rectifications SET reminder_sent = ? WHERE rectification_id = ?", (reminder_type, r["rectification_id"]))

    conn.commit()
    print(f"{label}: {len(by_task)}个项目, {len(rects)}条记录")

conn.close()

# 汇总推送企业微信群（自包含实现：宿主机脚本不依赖 backend 配置模块）
WEBHOOK_URL = os.getenv("WECOM_WEBHOOK_URL", "")
if wecom_lines and WEBHOOK_URL:
    try:
        import json, urllib.request
        payload = json.dumps({
            "msgtype": "markdown",
            "markdown": {"content": "**📋 整改提醒（每日自动检查）**\n" + "\n".join(wecom_lines)},
        }).encode("utf-8")
        req = urllib.request.Request(WEBHOOK_URL, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        print("企业微信推送完成")
    except Exception as e:
        print(f"企业微信推送失败: {e}")
print("Done!")
