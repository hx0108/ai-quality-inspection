"""
模拟数据初始化脚本
用于开发和演示，所有数据均为虚构，不包含任何真实个人信息
运行方式：cd backend && python init_sample_data.py
"""
import bcrypt
from database import SessionLocal
from models.models import User, Project, InspectionTask
from sqlalchemy import text


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_sample_users(db):
    """创建模拟用户（虚构数据）"""
    users = [
        # 检查员
        ("张三", "13800000001", "inspector"),
        ("李四", "13800000002", "inspector"),
        ("王五", "13800000003", "inspector"),
        ("赵六", "13800000004", "inspector"),
        ("钱七", "13800000005", "inspector"),
        # 驻场经理
        ("孙八", "13800000006", "field_supervisor"),
        ("周九", "13800000007", "field_supervisor"),
        ("吴十", "13800000008", "field_supervisor"),
        # 系统管理员
        ("系统管理员", "admin", "admin"),
        # 项目人员
        ("项目人员A", "project001", "project_staff"),
    ]

    for real_name, username, role in users:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            continue
        user = User(
            username=username,
            phone=username if username != "admin" and username != "project001" else "",
            password_hash=hash_password("123456"),
            real_name=real_name,
            role=role,
            is_active=True,
            must_change_pwd=True if username != "admin" else False
        )
        db.add(user)
        role_label = {"inspector": "检查员", "field_supervisor": "驻场经理", "admin": "管理员", "project_staff": "项目人员"}.get(role, role)
        print(f"  创建用户: {real_name} ({username}) - {role_label}")

    db.commit()


def create_sample_projects(db):
    """创建模拟项目"""
    projects = [
        "阳光花园一期",
        "翠湖名苑二期",
        "龙腾广场",
    ]
    for name in projects:
        existing = db.query(Project).filter(Project.name == name).first()
        if existing:
            continue
        p = Project(name=name, description=f"{name}项目", status="active")
        db.add(p)
        print(f"  创建项目: {name}")

    db.commit()


def main():
    db = SessionLocal()
    print("=" * 50)
    print("模拟数据初始化（所有数据均为虚构）")
    print("=" * 50)

    print("\n[1] 创建用户...")
    create_sample_users(db)

    print("\n[2] 创建项目...")
    create_sample_projects(db)

    print("\n初始化完成!")
    print("管理员账号: admin / admin123")
    print("其他账号密码: 123456（首次登录需修改）")
    db.close()


if __name__ == "__main__":
    main()
