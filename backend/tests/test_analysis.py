"""
统计与分析 API 测试
覆盖：仪表盘统计、项目分析、评分汇总
"""


class TestDashboardStats:
    """仪表盘统计 API 测试"""

    def test_get_stats_without_auth(self, client):
        """无 token 访问统计应返回 401"""
        resp = client.get("/api/v1/analysis/dashboard/stats")
        assert resp.status_code == 401

    def test_get_stats_with_auth(self, client, admin_headers):
        """有 token 应能获取仪表盘统计"""
        resp = client.get("/api/v1/analysis/dashboard/stats", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data

    def test_stats_summary_structure(self, client, admin_headers):
        """统计摘要应包含核心指标"""
        resp = client.get("/api/v1/analysis/dashboard/stats", headers=admin_headers)
        assert resp.status_code == 200
        summary = resp.json().get("summary", {})
        expected_keys = ["total_projects", "total_tasks", "total_issues", "total_rectifications"]
        for key in expected_keys:
            assert key in summary, f"缺少统计字段: {key}"

    def test_stats_includes_project_scores(self, client, admin_headers):
        """统计应包含项目得分"""
        resp = client.get("/api/v1/analysis/dashboard/stats", headers=admin_headers)
        data = resp.json()
        assert "project_latest_scores" in data

    def test_stats_includes_issue_distribution(self, client, admin_headers):
        """统计应包含问题分布"""
        resp = client.get("/api/v1/analysis/dashboard/stats", headers=admin_headers)
        data = resp.json()
        assert "issue_by_module" in data


class TestAnalysisAPI:
    """综合分析 API 测试"""

    def test_get_project_reports_without_auth(self, client):
        """无 token 应返回 401"""
        resp = client.get("/api/v1/analysis/projects-with-reports")
        assert resp.status_code == 401

    def test_get_project_reports_with_auth(self, client, admin_headers):
        """有 token 应能获取项目报告列表"""
        resp = client.get("/api/v1/analysis/projects-with-reports",
                          headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "projects" in data

    def test_get_project_reports_with_date_filter(self, client, admin_headers):
        """日期筛选应生效"""
        resp = client.get(
            "/api/v1/analysis/projects-with-reports?start=2025-01-01&end=2026-12-31",
            headers=admin_headers
        )
        assert resp.status_code == 200

    def test_get_history_without_auth(self, client):
        """无 token 应返回 401"""
        resp = client.get("/api/v1/analysis/history")
        assert resp.status_code == 401


class TestScoringAPI:
    """评分 API 测试"""

    def test_get_scoring_summary_without_auth(self, client):
        """无 token 访问评分应返回 401"""
        resp = client.get("/api/v1/scoring/results-summary/nonexistent-task")
        assert resp.status_code == 401

    def test_get_scoring_summary_nonexistent_task(self, client, admin_headers):
        """不存在的任务应返回 404 或空数据"""
        resp = client.get("/api/v1/scoring/results-summary/nonexistent-task-id",
                          headers=admin_headers)
        assert resp.status_code in (200, 404)


class TestTasksAPI:
    """任务 API 测试"""

    def test_get_tasks_without_auth(self, client):
        """无 token 应返回 401"""
        resp = client.get("/api/v1/tasks/")
        assert resp.status_code == 401

    def test_get_tasks_with_auth(self, client, admin_headers):
        """有 token 应能获取任务列表"""
        resp = client.get("/api/v1/tasks/", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_get_tasks_pagination(self, client, admin_headers):
        """分页参数应生效"""
        resp = client.get("/api/v1/tasks/?page=1&page_size=5",
                          headers=admin_headers)
        assert resp.status_code == 200

    def test_get_tasks_status_filter(self, client, admin_headers):
        """状态筛选应生效"""
        for status in ["pending", "in_progress", "completed"]:
            resp = client.get(f"/api/v1/tasks/?status={status}",
                              headers=admin_headers)
            assert resp.status_code == 200
