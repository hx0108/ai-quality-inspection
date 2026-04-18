import sys
import os
os.chdir(r'C:\Users\ASUS\Desktop\AI Agent\品质检查项目组\backend')
sys.path.insert(0, '.')

from database import SessionLocal
from models.models import User, Project

db = SessionLocal()

field_supervisors = [
    ("侯淦耀", "云山花园", "13928916520"),
    ("卢大伟", "幸福誉", "17346614118"),
    ("谭津津", "幸福荟", "13265376643"),
    ("吴琼玉", "幸福悦", "18899730830"),
    ("曾婉纯", "岚林花园", "13570204203"),
    ("盛海东", "金域悦府", "18935201559"),
    ("谭凌云", "天河御品", "15818182132"),
    ("郑前程", "四季花城", "13470822799"),
    ("谭凌云", "蓝山桐林", "15818182132"),
    ("黄蓉", "御金沙", "15817176310"),
    ("马婉婷", "中新里", "15817053001"),
    ("岳明山", "玉兰苑", "17665236130"),
    ("刘志鹏", "金域蓝湾", "13249147245"),
    ("曾婉纯", "田心康苑", "13570204203"),
    ("吴锡俊", "荷花紫薇", "13922321570"),
    ("岑威辰", "峰境花园", "13432805122"),
    ("郑前程", "四季公寓", "13470822799"),
    ("岑威辰", "金兰花园", "13432805122"),
    ("岑威辰", "丹桂园", "13432805122"),
]

updated = 0
skipped = 0

for real_name, project_name, phone in field_supervisors:
    project = db.query(Project).filter(Project.name == project_name).first()
    if not project:
        print(f"[SKIP] 项目不存在: {project_name}")
        skipped += 1
        continue

    user = db.query(User).filter(User.phone == phone, User.role == "field_supervisor").first()
    if not user:
        print(f"[SKIP] 用户不存在或非驻场经理: {real_name} ({phone})")
        skipped += 1
        continue

    user.project_id = project.id
    print(f"[UPDATE] {real_name} ({phone}) -> {project_name} (project_id={project.id})")
    updated += 1

db.commit()
db.close()
print(f"\n完成：更新 {updated} 人，跳过 {skipped} 人")
