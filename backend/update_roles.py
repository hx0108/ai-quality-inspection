import sys
import os
os.chdir(r'C:\Users\ASUS\Desktop\AI Agent\品质检查项目组\backend')
sys.path.insert(0, '.')

from database import SessionLocal
from models.models import User

db = SessionLocal()

# 7人改为 阵地督导(site_supervisor)
site_supervisors = [
    ("程诚", "13416284813"),
    ("辛艳莉", "18928716637"),
    ("程居兰", "18988859444"),
    ("樊叶辉", "13711203764"),
    ("田振荣", "13926065489"),
    ("岳明山", "17665236130"),
    ("张晶", "13826094648"),
]

for name, phone in site_supervisors:
    user = db.query(User).filter(User.phone == phone).first()
    if user:
        user.role = "site_supervisor"
        print(f"[UPDATE] {name} ({phone}) -> site_supervisor")
    else:
        print(f"[NOT FOUND] {name} ({phone})")

db.commit()
db.close()
print("Done")
