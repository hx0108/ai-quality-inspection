"""批量创建检查员和驻场经理账号，用户名=手机号，初始密码=123456"""
import bcrypt
from database import SessionLocal
from models.models import User

USERS = [
    # 检查员 (12人)
    ("赵泽兵", "18665642931", "inspector"),
    ("徐梦瑶", "13416347128", "inspector"),
    ("李孟生", "15917383589", "inspector"),
    ("余蠡鹏", "13543037550", "inspector"),
    ("李英群", "18578426218", "inspector"),
    ("陈果", "13726798705", "inspector"),
    ("赵惠君", "15920471962", "inspector"),
    ("马科平", "15521025814", "inspector"),
    ("周卢慧", "18377827734", "inspector"),
    ("周奕华", "13501414979", "inspector"),
    ("郑钰仪", "19898074908", "inspector"),
    ("宋惠芳", "13533522949", "inspector"),
    # 驻场经理 (7人)
    ("程诚", "13416284813", "field_supervisor"),
    ("辛艳莉", "18928716637", "field_supervisor"),
    ("程居兰", "18988859444", "field_supervisor"),
    ("樊叶辉", "13711203764", "field_supervisor"),
    ("田振荣", "13926065489", "field_supervisor"),
    ("岳明山", "17665236130", "field_supervisor"),
    ("张晶", "13826094648", "field_supervisor"),
]

PASSWORD = "123456"


def main():
    db = SessionLocal()
    created = 0
    skipped = 0
    try:
        for real_name, phone, role in USERS:
            existing = db.query(User).filter(User.phone == phone).first()
            if existing:
                print(f"  跳过 {real_name} ({phone}) - 已存在")
                skipped += 1
                continue

            password_hash = bcrypt.hashpw(
                PASSWORD.encode('utf-8'), bcrypt.gensalt()
            ).decode('utf-8')

            user = User(
                username=phone,
                phone=phone,
                password_hash=password_hash,
                real_name=real_name,
                role=role,
                must_change_pwd=True
            )
            db.add(user)
            created += 1
            role_label = "检查员" if role == "inspector" else "驻场经理"
            print(f"  创建 {real_name} ({phone}) - {role_label}")

        db.commit()
        print(f"\n完成: 创建 {created} 人, 跳过 {skipped} 人")
    except Exception as e:
        db.rollback()
        print(f"错误: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
