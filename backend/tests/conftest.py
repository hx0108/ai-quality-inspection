"""
Pytest 配置和共享 fixtures
"""
import sys
import os

# 确保 backend 目录在 path 中
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
import bcrypt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 导入应用和数据库
from main import app
from database import Base, get_db
from models.models import User, Project
from api.auth import create_access_token


# 测试数据库（SQLite 内存数据库）
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """覆盖数据库依赖"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """创建测试客户端"""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_user(db_session):
    """创建管理员用户"""
    password_hash = bcrypt.hashpw("test123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = User(
        username="test_admin",
        real_name="测试管理员",
        password_hash=password_hash,
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def inspector_user(db_session):
    """创建检查员用户"""
    password_hash = bcrypt.hashpw("test123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = User(
        username="test_inspector",
        real_name="测试检查员",
        password_hash=password_hash,
        role="inspector",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_project(db_session, admin_user):
    """创建测试项目"""
    project = Project(
        name="测试项目",
        code="TEST001",
        address="测试地址",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture(scope="function")
def admin_token(admin_user):
    """生成管理员访问令牌"""
    return create_access_token({
        "sub": admin_user.username,
        "user_id": admin_user.id,
        "role": admin_user.role,
    })


@pytest.fixture(scope="function")
def inspector_token(inspector_user):
    """生成检查员访问令牌"""
    return create_access_token({
        "sub": inspector_user.username,
        "user_id": inspector_user.id,
        "role": inspector_user.role,
    })


@pytest.fixture(scope="function")
def admin_headers(admin_token):
    """管理员请求头"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="function")
def inspector_headers(inspector_token):
    """检查员请求头"""
    return {"Authorization": f"Bearer {inspector_token}"}
