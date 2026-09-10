"""
API 自动化测试
测试核心 API 端点：认证、任务、报告、评分
"""
import pytest
from fastapi.testclient import TestClient

from models.models import Project, TaskAssignment


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

    def _make_project(self, db_session, name, code):
        """批量测试用：直插一个项目并返回"""
        project = Project(name=name, code=code, address="批量测试地址")
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)
        return project

    def test_batch_create_tasks(self, client, admin_headers, db_session, test_project):
        """批量创建：一次为多个项目建任务"""
        p2 = self._make_project(db_session, "批量项目B", "BATCH02")
        response = client.post(
            "/api/v1/tasks/batch",
            headers=admin_headers,
            json={
                "project_ids": [test_project.id, p2.id],
                "check_date": "2026-04-12",
                "standard_type": "diecheng",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["created_count"] == 2
        assert data["skipped_count"] == 0
        assert data["failed_count"] == 0
        assert all(t["task_id"].startswith("Q-20260412-") for t in data["created"])
        assert {t["project_id"] for t in data["created"]} == {test_project.id, p2.id}

    def test_batch_create_skips_existing(self, client, admin_headers, db_session, test_project):
        """重复批量创建：已有同项目同日期同标准任务时跳过而非重复建"""
        p2 = self._make_project(db_session, "批量项目C", "BATCH03")
        payload = {
            "project_ids": [test_project.id, p2.id],
            "check_date": "2026-04-12",
            "standard_type": "diecheng",
        }
        first = client.post("/api/v1/tasks/batch", headers=admin_headers, json=payload)
        assert first.json()["created_count"] == 2

        second = client.post("/api/v1/tasks/batch", headers=admin_headers, json=payload)
        data = second.json()
        assert data["created_count"] == 0
        assert data["skipped_count"] == 2
        assert all(s["existing_task_id"] for s in data["skipped"])

        # 换标准后不算重复，可再建
        third = client.post(
            "/api/v1/tasks/batch", headers=admin_headers,
            json={**payload, "standard_type": "lizhi"},
        )
        assert third.json()["created_count"] == 2

    def test_batch_create_partial_failure(self, client, admin_headers, test_project):
        """部分失败：不存在的项目记为 failed，其余照常创建"""
        response = client.post(
            "/api/v1/tasks/batch",
            headers=admin_headers,
            json={
                "project_ids": [test_project.id, 999999],
                "check_date": "2026-04-12",
                "standard_type": "diecheng",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created_count"] == 1
        assert data["failed_count"] == 1
        assert data["failed"][0]["reason"] == "项目不存在"

    def test_batch_create_dedup_within_request(self, client, admin_headers, test_project):
        """同一请求内重复项目id只建一次"""
        response = client.post(
            "/api/v1/tasks/batch",
            headers=admin_headers,
            json={
                "project_ids": [test_project.id, test_project.id],
                "check_date": "2026-04-12",
                "standard_type": "diecheng",
            },
        )
        data = response.json()
        assert data["created_count"] == 1
        assert data["skipped_count"] == 1
        assert data["skipped"][0]["reason"] == "本次请求内重复"

    def test_batch_create_requires_admin(self, client, inspector_headers, test_project):
        """批量创建仅管理员可用"""
        response = client.post(
            "/api/v1/tasks/batch",
            headers=inspector_headers,
            json={
                "project_ids": [test_project.id],
                "check_date": "2026-04-12",
                "standard_type": "diecheng",
            },
        )
        assert response.status_code == 403

    def _create_task(self, client, admin_headers, project_id, standard_type="diecheng"):
        """批量分配测试用：建一个任务返回 task_id"""
        resp = client.post(
            "/api/v1/tasks/",
            headers=admin_headers,
            json={"project_id": project_id, "check_date": "2026-04-12", "standard_type": standard_type},
        )
        return resp.json()["task_id"]

    def test_batch_assign(self, client, admin_headers, db_session, test_project, inspector_user):
        """批量分配：一套方案应用到多个任务，状态迁移 pending→in_progress"""
        t1 = self._create_task(client, admin_headers, test_project.id)
        t2 = self._create_task(client, admin_headers, test_project.id)
        response = client.post(
            "/api/v1/tasks/assign/batch",
            headers=admin_headers,
            json={
                "task_ids": [t1, t2],
                "assignments": [
                    {"module_name": "客户服务", "inspector_id": inspector_user.id},
                    {"module_name": "安全管理", "inspector_id": inspector_user.id},
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["assigned_count"] == 2
        assert data["skipped_count"] == 0 and data["failed_count"] == 0
        rows = db_session.query(TaskAssignment).filter(
            TaskAssignment.task_id.in_([t1, t2])
        ).all()
        assert len(rows) == 4
        # 任务状态：分配后应转 in_progress（经 API 侧查询验证）
        detail = client.get(f"/api/v1/tasks/{t1}", headers=admin_headers).json()
        assert detail["status"] == "in_progress"

    def test_batch_assign_skips_existing(self, client, admin_headers, db_session, test_project, inspector_user):
        """已有任何分配记录的任务整任务跳过"""
        t1 = self._create_task(client, admin_headers, test_project.id)
        db_session.add(TaskAssignment(task_id=t1, module_name="客户服务", inspector_id=inspector_user.id))
        db_session.commit()
        t2 = self._create_task(client, admin_headers, test_project.id)

        response = client.post(
            "/api/v1/tasks/assign/batch",
            headers=admin_headers,
            json={
                "task_ids": [t1, t2],
                "assignments": [{"module_name": "客户服务", "inspector_id": inspector_user.id}],
            },
        )
        data = response.json()
        assert data["assigned_count"] == 1
        assert data["skipped_count"] == 1
        assert data["skipped"][0]["task_id"] == t1
        # t1 仍只有 1 条分配（未被追加）
        assert db_session.query(TaskAssignment).filter(TaskAssignment.task_id == t1).count() == 1

    def test_batch_assign_partial_failure(self, client, admin_headers, test_project, inspector_user):
        """不存在的任务记为 failed，其余照常分配"""
        t1 = self._create_task(client, admin_headers, test_project.id)
        response = client.post(
            "/api/v1/tasks/assign/batch",
            headers=admin_headers,
            json={
                "task_ids": [t1, "Q-00000000-notexist"],
                "assignments": [{"module_name": "客户服务", "inspector_id": inspector_user.id}],
            },
        )
        data = response.json()
        assert data["assigned_count"] == 1
        assert data["failed_count"] == 1
        assert data["failed"][0]["reason"] == "任务不存在"

    def test_batch_assign_invalid_module(self, client, admin_headers, test_project, inspector_user):
        """模块名不属于任务标准：整任务失败且不落任何分配"""
        t1 = self._create_task(client, admin_headers, test_project.id, standard_type="lizhi")
        response = client.post(
            "/api/v1/tasks/assign/batch",
            headers=admin_headers,
            json={
                "task_ids": [t1],
                "assignments": [{"module_name": "客户服务", "inspector_id": inspector_user.id}],
            },
        )
        data = response.json()
        assert data["assigned_count"] == 0
        assert data["failed_count"] == 1
        assert "检查标准" in data["failed"][0]["reason"]

    def test_batch_assign_rejects_over_two_modules(self, client, admin_headers, test_project, inspector_user):
        """方案内同一检查员超过2个模块直接 400"""
        t1 = self._create_task(client, admin_headers, test_project.id)
        response = client.post(
            "/api/v1/tasks/assign/batch",
            headers=admin_headers,
            json={
                "task_ids": [t1],
                "assignments": [
                    {"module_name": m, "inspector_id": inspector_user.id}
                    for m in ("客户服务", "安全管理", "环境管理")
                ],
            },
        )
        assert response.status_code == 400
        assert "2个模块" in response.json()["detail"]

    def test_batch_assign_requires_admin(self, client, inspector_headers, test_project, inspector_user):
        """批量分配仅管理员可用"""
        response = client.post(
            "/api/v1/tasks/assign/batch",
            headers=inspector_headers,
            json={
                "task_ids": ["whatever"],
                "assignments": [{"module_name": "客户服务", "inspector_id": inspector_user.id}],
            },
        )
        assert response.status_code == 403


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
