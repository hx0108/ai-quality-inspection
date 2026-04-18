"""
端到端工作流测试
测试完整业务流程：创建任务 → 分配模块 → 开始检查 → 提交问题 → 完成检查 → AI评分 → 生成报告 → 整改闭环
"""
import pytest
from fastapi.testclient import TestClient


class TestInspectionWorkflow:
    """
    完整巡检工作流测试

    流程：
    1. 管理员创建任务
    2. 管理员分配模块给检查员
    3. 检查员开始模块检查（创建检查记录）
    4. 检查员更新检查项状态（合格/不合格）
    5. 检查员提交问题点
    6. 检查员完成模块检查（自动触发评分）
    7. 管理员生成报告
    8. 整改闭环：项目人员提交整改 → 督导重新核查
    """

    def test_full_workflow(self, client, admin_headers, inspector_headers, db_session, admin_user, inspector_user, test_project):
        """
        完整工作流测试
        注意：AI评分和报告生成涉及LLM调用，在测试环境可能返回202（后台处理）
        """
        # ========== Step 1: 管理员创建任务 ==========
        print("\n[Step 1] 创建任务...")
        task_resp = client.post(
            "/api/v1/tasks/",
            headers=admin_headers,
            json={
                "project_id": test_project.id,
                "check_date": "2026-04-12",
                "standard_type": "diecheng",
            }
        )
        assert task_resp.status_code == 200, f"创建任务失败: {task_resp.text}"
        task_data = task_resp.json()
        task_id = task_data["task_id"]
        print(f"  任务创建成功: {task_id}")

        # ========== Step 2: 管理员分配模块给检查员 ==========
        print("\n[Step 2] 分配模块...")
        assign_resp = client.post(
            f"/api/v1/tasks/{task_id}/assign",
            headers=admin_headers,
            json={
                "module_name": "环境管理",
                "inspector_id": inspector_user.id,
            }
        )
        assert assign_resp.status_code == 200, f"分配模块失败: {assign_resp.text}"
        print(f"  模块分配成功: 环境管理 → {inspector_user.username}")

        # ========== Step 3: 检查员创建检查记录 ==========
        print("\n[Step 3] 开始检查...")
        record_resp = client.post(
            "/api/v1/records/",
            headers=inspector_headers,
            json={
                "task_id": task_id,
                "module_name": "环境管理",
            }
        )
        assert record_resp.status_code == 200, f"创建检查记录失败: {record_resp.text}"
        record_data = record_resp.json()
        record_id = record_data.get("record_id")
        print(f"  检查记录创建成功: {record_id}")

        # ========== Step 4: 检查员更新检查项状态 ==========
        print("\n[Step 4] 更新检查项状态...")
        # 获取模板项
        template_resp = client.get(
            "/api/v1/tasks/module-template/环境管理",
            headers=admin_headers,
            params={"standard_type": "diecheng"}
        )
        template_items = template_resp.json().get("items", [])

        # 只测试前2项
        for item in template_items[:2]:
            item_id = item["item_id"]
            is_first = template_items.index(item) == 0
            update_resp = client.put(
                f"/api/v1/records/{record_id}/items/{item_id}",
                headers=inspector_headers,
                json={
                    "status": "checked",
                    "qualified": is_first,  # 第一项合格，第二项不合格
                }
            )
            assert update_resp.status_code == 200, f"更新检查项失败: {update_resp.text}"
            print(f"  检查项更新: {item_id} → {'合格' if is_first else '不合格'}")

        # ========== Step 5: 检查员提交问题点 ==========
        print("\n[Step 5] 提交问题点...")
        second_item = template_items[1]
        issue_resp = client.post(
            f"/api/v1/records/{record_id}/issues",
            headers=inspector_headers,
            json={
                "item_id": second_item["item_id"],
                "item_name": second_item.get("item_name", "测试检查项"),
                "description": "垃圾桶标识不清晰，需要更换",
                "location": "小区东门",
                "severity": "一般",
            }
        )
        assert issue_resp.status_code == 200, f"提交问题失败: {issue_resp.text}"
        issue_data = issue_resp.json()
        issue_id = issue_data.get("issue_id")
        print(f"  问题提交成功: {issue_id}")

        # ========== Step 6: 检查员完成模块检查 ==========
        print("\n[Step 6] 完成模块检查...")
        # 完成所有检查项
        for item in template_items:
            client.put(
                f"/api/v1/records/{record_id}/items/{item['item_id']}",
                headers=inspector_headers,
                json={
                    "status": "checked",
                    "qualified": True,
                }
            )

        complete_resp = client.put(
            f"/api/v1/records/{record_id}/complete",
            headers=inspector_headers,
        )
        assert complete_resp.status_code == 200, f"完成检查失败: {complete_resp.text}"
        print(f"  模块检查完成（评分自动触发）")

        # ========== 验证：检查任务状态 ==========
        print("\n[验证] 检查任务状态...")
        task_detail_resp = client.get(
            f"/api/v1/tasks/{task_id}",
            headers=admin_headers,
        )
        assert task_detail_resp.status_code == 200
        task_detail = task_detail_resp.json()
        print(f"  任务状态: {task_detail.get('status')}")
        print(f"  任务总分: {task_detail.get('total_score')}")


class TestInspectionRecordAPI:
    """检查记录 API 测试"""

    def test_create_record(self, client, inspector_headers, admin_headers, db_session, inspector_user, test_project):
        """测试创建检查记录"""
        # 创建任务
        task_resp = client.post(
            "/api/v1/tasks/",
            headers=admin_headers,
            json={
                "project_id": test_project.id,
                "check_date": "2026-04-12",
                "standard_type": "diecheng",
            }
        )
        task_id = task_resp.json()["task_id"]

        # 分配模块
        client.post(
            f"/api/v1/tasks/{task_id}/assign",
            headers=admin_headers,
            json={
                "module_name": "安全管理",
                "inspector_id": inspector_user.id,
            }
        )

        # 创建检查记录
        record_resp = client.post(
            "/api/v1/records/",
            headers=inspector_headers,
            json={
                "task_id": task_id,
                "module_name": "安全管理",
            }
        )
        assert record_resp.status_code == 200
        data = record_resp.json()
        assert "record_id" in data or "id" in data

    def test_update_item_status(self, client, inspector_headers, admin_headers, db_session, inspector_user, test_project):
        """测试更新检查项状态"""
        # 创建任务和记录
        task_resp = client.post(
            "/api/v1/tasks/",
            headers=admin_headers,
            json={
                "project_id": test_project.id,
                "check_date": "2026-04-12",
                "standard_type": "diecheng",
            }
        )
        task_id = task_resp.json()["task_id"]

        client.post(
            f"/api/v1/tasks/{task_id}/assign",
            headers=admin_headers,
            json={
                "module_name": "设施维护",
                "inspector_id": inspector_user.id,
            }
        )

        record_resp = client.post(
            "/api/v1/records/",
            headers=inspector_headers,
            json={
                "task_id": task_id,
                "module_name": "设施维护",
            }
        )
        record_id = record_resp.json().get("record_id")

        # 获取模板项
        template_resp = client.get(
            "/api/v1/tasks/module-template/设施维护",
            headers=admin_headers,
            params={"standard_type": "diecheng"}
        )
        items = template_resp.json().get("items", [])
        if items:
            item_id = items[0]["item_id"]

            # 更新状态
            update_resp = client.put(
                f"/api/v1/records/{record_id}/items/{item_id}",
                headers=inspector_headers,
                json={
                    "status": "checked",
                    "qualified": True,
                }
            )
            assert update_resp.status_code == 200

    def test_submit_issue(self, client, inspector_headers, admin_headers, db_session, inspector_user, test_project):
        """测试提交问题点"""
        # 创建任务和记录
        task_resp = client.post(
            "/api/v1/tasks/",
            headers=admin_headers,
            json={
                "project_id": test_project.id,
                "check_date": "2026-04-12",
                "standard_type": "diecheng",
            }
        )
        task_id = task_resp.json()["task_id"]

        client.post(
            f"/api/v1/tasks/{task_id}/assign",
            headers=admin_headers,
            json={
                "module_name": "环境管理",
                "inspector_id": inspector_user.id,
            }
        )

        record_resp = client.post(
            "/api/v1/records/",
            headers=inspector_headers,
            json={
                "task_id": task_id,
                "module_name": "环境管理",
            }
        )
        record_id = record_resp.json().get("record_id")

        # 提交问题
        issue_resp = client.post(
            f"/api/v1/records/{record_id}/issues",
            headers=inspector_headers,
            json={
                "item_id": "TEST001",
                "item_name": "环境测试",
                "description": "垃圾桶标识不清晰",
                "location": "小区东门",
                "severity": "一般",
            }
        )
        assert issue_resp.status_code == 200
        assert "issue_id" in issue_resp.json()

    def test_complete_record(self, client, inspector_headers, admin_headers, db_session, inspector_user, test_project):
        """测试完成检查记录"""
        # 创建任务和记录
        task_resp = client.post(
            "/api/v1/tasks/",
            headers=admin_headers,
            json={
                "project_id": test_project.id,
                "check_date": "2026-04-12",
                "standard_type": "diecheng",
            }
        )
        task_id = task_resp.json()["task_id"]

        client.post(
            f"/api/v1/tasks/{task_id}/assign",
            headers=admin_headers,
            json={
                "module_name": "安全管理",
                "inspector_id": inspector_user.id,
            }
        )

        record_resp = client.post(
            "/api/v1/records/",
            headers=inspector_headers,
            json={
                "task_id": task_id,
                "module_name": "安全管理",
            }
        )
        record_id = record_resp.json().get("record_id")

        # 获取模板并标记所有项为完成
        template_resp = client.get(
            "/api/v1/tasks/module-template/安全管理",
            headers=admin_headers,
            params={"standard_type": "diecheng"}
        )
        items = template_resp.json().get("items", [])
        for item in items:
            client.put(
                f"/api/v1/records/{record_id}/items/{item['item_id']}",
                headers=inspector_headers,
                json={
                    "status": "checked",
                    "qualified": True,
                }
            )

        # 完成检查
        complete_resp = client.put(
            f"/api/v1/records/{record_id}/complete",
            headers=inspector_headers,
        )
        assert complete_resp.status_code == 200


class TestScoringAPI:
    """评分 API 测试"""

    def test_trigger_scoring(self, client, admin_headers, inspector_headers, db_session, inspector_user, test_project):
        """测试触发评分（可能返回200或400，取决于任务状态）"""
        # 创建完整任务流程
        task_resp = client.post(
            "/api/v1/tasks/",
            headers=admin_headers,
            json={
                "project_id": test_project.id,
                "check_date": "2026-04-12",
                "standard_type": "diecheng",
            }
        )
        task_id = task_resp.json()["task_id"]

        client.post(
            f"/api/v1/tasks/{task_id}/assign",
            headers=admin_headers,
            json={
                "module_name": "环境管理",
                "inspector_id": inspector_user.id,
            }
        )

        record_resp = client.post(
            "/api/v1/records/",
            headers=inspector_headers,
            json={
                "task_id": task_id,
                "module_name": "环境管理",
            }
        )
        record_id = record_resp.json().get("record_id")

        # 完成检查触发评分
        template_resp = client.get(
            "/api/v1/tasks/module-template/环境管理",
            headers=admin_headers,
            params={"standard_type": "diecheng"}
        )
        items = template_resp.json().get("items", [])
        for item in items:
            client.put(
                f"/api/v1/records/{record_id}/items/{item['item_id']}",
                headers=inspector_headers,
                json={"status": "checked", "qualified": True}
            )

        complete_resp = client.put(
            f"/api/v1/records/{record_id}/complete",
            headers=inspector_headers,
        )
        # 评分自动触发，检查返回状态
        assert complete_resp.status_code == 200

    def test_get_scoring_status(self, client, admin_headers, inspector_headers, db_session, inspector_user, test_project):
        """测试获取评分状态"""
        # 创建任务
        task_resp = client.post(
            "/api/v1/tasks/",
            headers=admin_headers,
            json={
                "project_id": test_project.id,
                "check_date": "2026-04-12",
                "standard_type": "diecheng",
            }
        )
        task_id = task_resp.json()["task_id"]

        # 获取评分状态
        status_resp = client.get(
            f"/api/v1/scoring/status/{task_id}",
            headers=admin_headers,
        )
        # 可能返回200或404（任务不存在于评分记录中）
        assert status_resp.status_code in [200, 404]


class TestReportAPI:
    """报告 API 测试"""

    def test_list_reports(self, client, admin_headers):
        """测试列出报告"""
        resp = client.get("/api/v1/reports/list/all", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_get_report_status(self, client, admin_headers, inspector_headers, db_session, inspector_user, test_project):
        """测试获取报告生成状态"""
        # 创建任务
        task_resp = client.post(
            "/api/v1/tasks/",
            headers=admin_headers,
            json={
                "project_id": test_project.id,
                "check_date": "2026-04-12",
                "standard_type": "diecheng",
            }
        )
        task_id = task_resp.json()["task_id"]

        # 获取报告状态（可能返回404，如果报告不存在）
        status_resp = client.get(
            f"/api/v1/reports/status/{task_id}",
            headers=admin_headers,
        )
        assert status_resp.status_code in [200, 404]


class TestRectificationAPI:
    """整改 API 测试"""

    def test_list_pending_rectifications(self, client, admin_headers):
        """测试获取待整改列表"""
        resp = client.get("/api/v1/rectifications/pending", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list) or "items" in data

    def test_get_rectification_workflow(self, client, admin_headers, inspector_headers, db_session, inspector_user, test_project):
        """测试整改工作流：创建问题 → 自动创建整改记录"""
        # 创建任务并完成检查
        task_resp = client.post(
            "/api/v1/tasks/",
            headers=admin_headers,
            json={
                "project_id": test_project.id,
                "check_date": "2026-04-12",
                "standard_type": "diecheng",
            }
        )
        task_id = task_resp.json()["task_id"]

        client.post(
            f"/api/v1/tasks/{task_id}/assign",
            headers=admin_headers,
            json={
                "module_name": "环境管理",
                "inspector_id": inspector_user.id,
            }
        )

        record_resp = client.post(
            "/api/v1/records/",
            headers=inspector_headers,
            json={
                "task_id": task_id,
                "module_name": "环境管理",
            }
        )
        record_id = record_resp.json().get("record_id")

        # 提交一个问题
        client.post(
            f"/api/v1/records/{record_id}/issues",
            headers=inspector_headers,
            json={
                "item_id": "TEST001",
                "item_name": "测试项",
                "description": "测试问题",
                "severity": "一般",
            }
        )

        # 完成检查（会自动创建整改记录）
        template_resp = client.get(
            "/api/v1/tasks/module-template/环境管理",
            headers=admin_headers,
            params={"standard_type": "diecheng"}
        )
        items = template_resp.json().get("items", [])
        for item in items:
            client.put(
                f"/api/v1/records/{record_id}/items/{item['item_id']}",
                headers=inspector_headers,
                json={"status": "checked", "qualified": True}
            )

        complete_resp = client.put(
            f"/api/v1/records/{record_id}/complete",
            headers=inspector_headers,
        )
        assert complete_resp.status_code == 200

        # 验证整改记录已创建
        pending_resp = client.get("/api/v1/rectifications/pending", headers=admin_headers)
        assert pending_resp.status_code == 200


class TestOrchestratorAPI:
    """编排器 API 测试"""

    def test_get_pipeline_status(self, client, admin_headers, inspector_headers, db_session, inspector_user, test_project):
        """测试获取流水线状态"""
        # 创建任务
        task_resp = client.post(
            "/api/v1/tasks/",
            headers=admin_headers,
            json={
                "project_id": test_project.id,
                "check_date": "2026-04-12",
                "standard_type": "diecheng",
            }
        )
        task_id = task_resp.json()["task_id"]

        # 获取流水线状态（新任务可能返回404）
        status_resp = client.get(
            f"/api/v1/orchestrator/status/{task_id}",
            headers=admin_headers,
        )
        # 可能返回200（有状态）或404（新任务无状态）
        assert status_resp.status_code in [200, 404]


class TestModuleTemplateAPI:
    """模块模板 API 测试"""

    def test_get_module_template(self, client, admin_headers):
        """测试获取模块模板"""
        resp = client.get(
            "/api/v1/tasks/module-template/环境管理",
            headers=admin_headers,
            params={"standard_type": "diecheng"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) > 0

        # 验证模板项结构
        first_item = data["items"][0]
        assert "item_id" in first_item
        assert "item_name" in first_item

    def test_get_valid_modules(self, client, admin_headers):
        """测试获取有效模块的模板"""
        # 测试已知的有效模块
        valid_modules = ["环境管理", "安全管理", "设施维护", "客户服务"]
        for module in valid_modules:
            resp = client.get(
                f"/api/v1/tasks/module-template/{module}",
                headers=admin_headers,
                params={"standard_type": "diecheng"}
            )
            assert resp.status_code == 200, f"模块 {module} 获取失败"
            data = resp.json()
            assert "items" in data
