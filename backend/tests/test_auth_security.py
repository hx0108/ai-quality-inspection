"""
认证安全 API 测试
覆盖：登录速率限制、注册校验、权限控制、Token 有效性
"""
import pytest


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    """每个测试前重置速率限制器，避免跨测试影响"""
    from api.auth import _login_attempts, _register_limiter
    _login_attempts.clear()
    _register_limiter._data.clear()
    yield
    _login_attempts.clear()
    _register_limiter._data.clear()


class TestLoginRateLimit:
    """登录速率限制测试"""

    def test_login_within_rate_limit(self, client, admin_user):
        """正常频次登录应成功"""
        for _ in range(4):
            resp = client.post("/api/v1/auth/login", json={
                "account": "test_admin", "password": "test123"
            })
        assert resp.status_code == 200

    def test_login_exceeds_rate_limit(self, client, admin_user):
        """超过速率限制应返回 429"""
        for _ in range(5):
            client.post("/api/v1/auth/login", json={
                "account": "test_admin", "password": "test123"
            })
        # 第6次应被限流
        resp = client.post("/api/v1/auth/login", json={
            "account": "test_admin", "password": "test123"
        })
        assert resp.status_code == 429


class TestRegisterValidation:
    """注册参数校验测试"""

    def test_register_invalid_phone(self, client, db_session, test_project):
        """无效手机号应被拒绝"""
        resp = client.post("/api/v1/auth/register", json={
            "phone": "12345",
            "password": "testPass123",
            "real_name": "测试用户",
            "project_name": test_project.name
        })
        assert resp.status_code == 400
        assert "手机号" in resp.json()["detail"]

    def test_register_short_password(self, client, db_session, test_project):
        """密码过短应被拒绝"""
        resp = client.post("/api/v1/auth/register", json={
            "phone": "13800001111",
            "password": "short1",
            "real_name": "测试用户",
            "project_name": test_project.name
        })
        assert resp.status_code == 400
        assert "密码" in resp.json()["detail"]

    def test_register_password_no_letter(self, client, db_session, test_project):
        """纯数字密码应被拒绝"""
        resp = client.post("/api/v1/auth/register", json={
            "phone": "13800001111",
            "password": "1234567890",
            "real_name": "测试用户",
            "project_name": test_project.name
        })
        assert resp.status_code == 400
        assert "密码" in resp.json()["detail"]

    def test_register_password_no_digit(self, client, db_session, test_project):
        """纯字母密码应被拒绝"""
        resp = client.post("/api/v1/auth/register", json={
            "phone": "13800001111",
            "password": "abcdefghij",
            "real_name": "测试用户",
            "project_name": test_project.name
        })
        assert resp.status_code == 400

    def test_register_empty_name(self, client, db_session, test_project):
        """空姓名应被拒绝"""
        resp = client.post("/api/v1/auth/register", json={
            "phone": "13800001111",
            "password": "testPass123",
            "real_name": "  ",
            "project_name": test_project.name
        })
        assert resp.status_code == 400

    def test_register_nonexistent_project(self, client, db_session):
        """不存在的项目应被拒绝"""
        resp = client.post("/api/v1/auth/register", json={
            "phone": "13800001111",
            "password": "testPass123",
            "real_name": "测试用户",
            "project_name": "不存在的项目"
        })
        assert resp.status_code == 400

    def test_register_duplicate_phone(self, client, admin_user, db_session, test_project):
        """已注册手机号应被拒绝"""
        admin_user.phone = "13800009999"
        db_session.commit()
        resp = client.post("/api/v1/auth/register", json={
            "phone": "13800009999",
            "password": "testPass123",
            "real_name": "重复手机号",
            "project_name": test_project.name
        })
        assert resp.status_code == 400
        assert "已注册" in resp.json()["detail"]

    def test_register_success(self, client, db_session, test_project):
        """正常注册应成功并返回 token"""
        resp = client.post("/api/v1/auth/register", json={
            "phone": "13800002222",
            "password": "testPass123",
            "real_name": "新用户",
            "project_name": test_project.name
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["role"] == "project_staff"

    def test_register_multiple_projects_keeps_first_as_default(self, client, db_session, test_project):
        """注册选择多个项目时应绑定全部项目，并将首选项目作为默认项目。"""
        from models.models import Project, User, UserProject

        second_project = Project(name="测试项目二", code="PRJ-TEST-002")
        db_session.add(second_project)
        db_session.commit()
        db_session.refresh(second_project)

        resp = client.post("/api/v1/auth/register", json={
            "phone": "13800003333",
            "password": "testPass123",
            "real_name": "多项目用户",
            "project_id": second_project.id,
            "project_name": second_project.name,
            "project_ids": [second_project.id, test_project.id],
            "project_names": [second_project.name, test_project.name]
        })

        assert resp.status_code == 200
        data = resp.json()["user"]
        assert data["project_id"] == second_project.id
        assert data["project_name"] == second_project.name
        assert data["projects"] == [
            {"id": second_project.id, "name": second_project.name},
            {"id": test_project.id, "name": test_project.name}
        ]

        user = db_session.query(User).filter(User.phone == "13800003333").one()
        linked_ids = [
            row.project_id
            for row in db_session.query(UserProject)
            .filter(UserProject.user_id == user.id)
            .order_by(UserProject.id)
            .all()
        ]
        assert user.project_id == second_project.id
        assert linked_ids == [second_project.id, test_project.id]


class TestTokenAndAuth:
    """Token 和权限控制测试"""

    def test_access_protected_without_token(self, client, admin_user):
        """无 token 访问受保护端点应返回 401"""
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_access_with_valid_token(self, client, admin_headers):
        """有效 token 访问受保护端点应成功"""
        resp = client.get("/api/v1/auth/me", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["username"] == "test_admin"

    def test_access_with_invalid_token(self, client, admin_user):
        """无效 token 应返回 401"""
        resp = client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer invalid.token.here"
        })
        assert resp.status_code == 401

    def test_get_me_returns_user_info(self, client, admin_headers):
        """GET /me 应返回完整用户信息"""
        resp = client.get("/api/v1/auth/me", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "username" in data
        assert "role" in data


class TestChangePassword:
    """修改密码测试"""

    def test_change_password_success(self, client, admin_headers, admin_user, db_session):
        """正常改密应成功"""
        resp = client.post("/api/v1/auth/change-password",
                           json={"new_password": "newPass123"},
                           headers=admin_headers)
        assert resp.status_code == 200

        # 用新密码登录
        login_resp = client.post("/api/v1/auth/login", json={
            "account": admin_user.username,
            "password": "newPass123"
        })
        assert login_resp.status_code == 200

    def test_change_password_weak(self, client, admin_headers):
        """弱密码应被拒绝"""
        resp = client.post("/api/v1/auth/change-password",
                           json={"new_password": "weak"},
                           headers=admin_headers)
        assert resp.status_code == 400
