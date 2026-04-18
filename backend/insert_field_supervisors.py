import sys
import os
os.chdir(r'C:\Users\ASUS\Desktop\AI Agent\品质检查项目组\backend')
sys.path.insert(0, '.')

import bcrypt
from database import SessionLocal, init_db
from models.models import User, Project

init_db()

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

password_hash = bcrypt.hashpw("123456".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

created = 0
skipped = 0

for real_name, project_name, phone in field_supervisors:
    # Find project
    project = db.query(Project).filter(Project.name == project_name).first()
    if not project:
        print(f"[SKIP] 项目不存在: {project_name}")
        skipped += 1
        continue

    # Check if phone already registered
    existing = db.query(User).filter(User.phone == phone).first()
    if existing:
        print(f"[SKIP] 手机号已注册: {phone} ({real_name})")
        skipped += 1
        continue

    # Generate username
    import random
    suffix = random.randint(100, 999)
    username = f"u_{phone[-4:]}_{suffix}"
    while db.query(User).filter(User.username == username).first():
        suffix = random.randint(100, 999)
        username = f"u_{phone[-4:]}_{suffix}"

    user = User(
        username=username,
        password_hash=password_hash,
        real_name=real_name,
        phone=phone,
        role="field_supervisor",
        project_id=project.id,
        must_change_pwd=True
    )
    db.add(user)
    print(f"[CREATE] {real_name} | {phone} | {project_name} (project_id={project.id})")
    created += 1

db.commit()
db.close()
print(f"\n完成：创建 {created} 人，跳过 {skipped} 人")