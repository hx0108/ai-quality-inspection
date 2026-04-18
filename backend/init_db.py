"""
数据库初始化脚本
- 创建所有表
- 插入示例项目
- 插入默认管理员
- 验证模板数据
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
import bcrypt  # 直接使用 bcrypt
from database import engine, SessionLocal, Base
from models.models import User, Project


def hash_password(password: str) -> str:
    """生成密码哈希"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_tables():
    """创建所有数据库表"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created")


def create_sample_projects(db: Session):
    """创建示例项目"""
    projects = [
        "幸福悦花园", "翠湖玫瑰园", "碧桂园天麓", "锦绣城市花园",
        "保利天悦湾", "恒大御景湾", "龙湖世纪城", "融创壹号院",
        "中海锦城", "招商花园城", "金茂府", "华润橡树湾",
        "世茂滨江花园", "金地天府花园", "远洋太古里", "新城吾悦广场",
        "旭辉铂悦府", "正荣府", "建发央著", "首开龙湖天街",
        "阳光城檀悦"
    ]

    print("Creating sample projects...")
    for name in projects:
        existing = db.query(Project).filter(Project.name == name).first()
        if not existing:
            project = Project(
                name=name,
                code=f"PRJ-{projects.index(name)+1:03d}",
                address=f"Address {projects.index(name)+1}"
            )
            db.add(project)

    db.commit()
    print(f"Created {len(projects)} sample projects")


def create_admin_user(db: Session):
    """创建默认管理员和检查员"""
    print("Creating admin account...")

    existing = db.query(User).filter(User.username == "admin").first()
    if existing:
        print("Admin account already exists, skipping creation")
        return

    admin = User(
        username="admin",
        password_hash=hash_password("admin123"),
        real_name="系统管理员",
        role="admin",
        is_active=True
    )
    db.add(admin)

    # 创建检查员列表（按用户指定的8人）
    inspectors = [
        ("zhaobin", "赵泽兵", "inspector"),
        ("xumengyao", "徐梦瑶", "inspector"),
        ("limengsheng", "李孟生", "inspector"),
        ("yuxinpeng", "余鑫鹏", "inspector"),
        ("liyingqun", "李英群", "inspector"),
        ("hexing", "贺星", "inspector"),
        ("chenguo", "陈果", "inspector"),
        ("caiwu", "财务", "inspector"),
    ]

    for username, real_name, role in inspectors:
        existing = db.query(User).filter(User.username == username).first()
        if not existing:
            user = User(
                username=username,
                password_hash=hash_password("123456"),
                real_name=real_name,
                role=role,
                is_active=True
            )
            db.add(user)

    db.commit()
    print("Admin account created: admin / admin123")
    print("Inspectors created with password: 123456")


def verify_template_data():
    """验证模板数据"""
    print("Verifying template data...")

    template_path = Path(__file__).parent / "data" / "templates" / "内审检查表V3.0.xlsx"
    if not template_path.exists():
        print(f"Template file not found: {template_path}")
        return

    print("Template file found")


def main():
    """主函数"""
    print("=" * 50)
    print("Database Initialization Started")
    print("=" * 50)

    # 1. 创建表
    create_tables()

    # 2. 插入数据
    db = SessionLocal()
    try:
        create_sample_projects(db)
        create_admin_user(db)
    finally:
        db.close()

    # 3. 验证模板
    verify_template_data()

    print("=" * 50)
    print("Database Initialization Complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
