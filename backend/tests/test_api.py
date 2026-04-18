"""
API 自动化测试
测试核心 API 端点：认证、任务、报告、评分
"""
import pytest
from fastapi.testclient import TestClient


class TestAuthAPI:
    """认证 API 测试"""

    def test_login_success(self, client, admin_user):
        """测试正常登录"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "account": "test_admin",
                "password": "test123",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["username"] == "test_admin"

    def test_login_wrong_password(self, client, admin_user):
        """测试密码错误"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "account": "test_admin",
                "password": "wrongpassword",
            }
        )
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_login_nonexistent_user(self, client):
        """测试不存在的用户"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "account": "nonexistent",
                "password": "test123",
            }
        )
        assert response.status_code == 401

    def test_get_current_user(self, client, admin_headers, admin_user):
        """测试获取当前用户信息"""
        response = client.get("/api/v1/auth/me", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "test_admin"
        assert data["role"] == "admin"

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401


class TestProjectAPI:
    """项目管理 API 测试"""

    def test_list_projects_as_admin(self, client, admin_headers, test_project):
        """管理员列出所有项目"""
        response = client.get("/api/v1/projects/", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)

    def test_list_projects_as_inspector(self, client, inspector_headers, test_project):
        """检查员只能看到分配的项目"""
        response = client.get("/api/v1/projects/", headers=inspector_headers)
        assert response.status_code == 200

    def test_create_project(self, client, admin_headers):
        """创建新项目"""
        response = client.post(
            "/api/v1/projects/",
            headers=admin_headers,
            json={
                "name": "新测试项目",
                "code": "NEW001",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "新测试项目"
        assert "message" in data  # 创建成功返回 message

    def test_create_project_duplicate_name(self, client, admin_headers, test_project):
        """创建项目 - 重复名称应被拒绝"""
        response = client.post(
            "/api/v1/projects/",
            headers=admin_headers,
            json={
                "name": test_project.name,  # 使用已存在的项目名
                "code": "DUP001",
            }
        )
        assert response.status_code == 400
        assert "已存在" in response.json().get("detail", "")


class TestTaskAPI:
    """任务管理 API 测试"""

    def test_list_tasks_as_admin(self, client, admin_headers, test_project):
        """管理员列出所有任务"""
        response = client.get("/api/v1/tasks/", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_create_task(self, client, admin_headers, test_project):
        """创建新任务"""
        response = client.post(
            "/api/v1/tasks/",
            headers=admin_headers,
            json={
                "project_id": test_project.id,
                "check_date": "2026-04-12",
                "standard_type": "diecheng",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == test_project.id
        assert data["status"] in ["pending", "in_progress"]
        assert "task_id" in data

    def test_get_task_detail(self, client, admin_headers, test_project):
        """获取任务详情"""
        # 先创建任务
        create_resp = client.post(
            "/api/v1/tasks/",
            headers=admin_headers,
            json={
                "project_id": test_project.id,
                "check_date": "2026-04-12",
                "standard_type": "diecheng",
            }
        )
        task_id = create_resp.json()["task_id"]

        # 获取详情
        response = client.get(f"/api/v1/tasks/{task_id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id

    def test_task_not_found(self, client, admin_headers):
        """任务不存在"""
        response = client.get("/api/v1/tasks/nonexistent-task-id", headers=admin_headers)
        assert response.status_code == 404


class TestReportAPI:
    """报告 API 测试"""

    def test_list_reports_as_admin(self, client, admin_headers):
        """管理员列出所有报告"""
        response = client.get("/api/v1/reports/list/all", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_list_reports_as_inspector(self, client, inspector_headers):
        """检查员列出自己的报告"""
        response = client.get("/api/v1/reports/list/all", headers=inspector_headers)
        assert response.status_code == 200

    def test_report_pagination(self, client, admin_headers):
        """报告分页测试"""
        response = client.get(
            "/api/v1/reports/list/all",
            headers=admin_headers,
            params={"page": 1, "page_size": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_report_filter_by_project(self, client, admin_headers):
        """按项目筛选报告"""
        response = client.get(
            "/api/v1/reports/list/all",
            headers=admin_headers,
            params={"project_id": 9999}
        )
        assert response.status_code == 200


class TestUserAPI:
    """用户管理 API 测试"""

    def test_list_users_as_admin(self, client, admin_headers):
        """管理员列出所有用户"""
        response = client.get("/api/v1/users/", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_list_users_forbidden_for_inspector(self, client, inspector_headers):
        """检查员无权列出所有用户"""
        response = client.get("/api/v1/users/", headers=inspector_headers)
        assert response.status_code in [403, 401]

    def test_admin_can_create_user(self, client, admin_headers):
        """管理员可以创建用户"""
        response = client.post(
            "/api/v1/users/",
            headers=admin_headers,
            json={
                "username": "newuser",
                "password": "test123",
                "real_name": "新用户",
                "role": "inspector",
                "phone": "13800138000",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "id" in data


class TestHealthCheck:
    """健康检查测试"""

    def test_root_endpoint(self, client):
        """根路径返回欢迎信息"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_health_endpoint(self, client):
        """健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestAccessControl:
    """访问控制测试"""

    def test_cors_headers(self, client):
        """测试 CORS 头"""
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            }
        )
        # CORS preflight 应该返回 200 或 405

    def test_role_based_access(self, client, inspector_headers):
        """测试基于角色的访问控制"""
        # 检查员尝试访问管理端点应该被拒绝
        response = client.get("/api/v1/users/", headers=inspector_headers)
        assert response.status_code in [401, 403]
