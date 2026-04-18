"""
评分一致性测试
使用Golden Dataset验证AI评分准确性
"""
import json
import pytest
from pathlib import Path
from typing import Dict, List
from backend.core.llm_client import QwenClient
from backend.core.golden_dataset import GoldenDatasetGenerator


# 加载Golden Dataset的fixture
@pytest.fixture(scope="module")
def golden_dataset():
    """加载Golden Dataset"""
    data_dir = Path(__file__).parent.parent / "data"
    generator = GoldenDatasetGenerator(data_dir)

    # 尝试加载已有数据集
    dataset = generator.load_from_file()
    if not dataset.get("samples"):
        # 如果没有，生成新的
        samples = generator.generate_from_history(min_samples_per_module=3)
        dataset = {"metadata": {"generated_at": "", "total_samples": len(samples)}, "samples": samples}

    return dataset


@pytest.fixture(scope="module")
def qwen_client():
    """创建LLM客户端"""
    return QwenClient()


class TestScoringConsistency:
    """评分一致性测试套件"""

    @pytest.mark.asyncio
    async def test_golden_dataset_accuracy(self, qwen_client, golden_dataset):
        """
        测试Golden Dataset准确率
        准入标准：准确率 >= 85%
        """
        samples = golden_dataset.get("samples", [])
        if not samples:
            pytest.skip("Golden Dataset为空")

        total = len(samples)
        correct = 0
        results = []

        for sample in samples:
            try:
                result = await qwen_client.score_item(
                    module_name=sample["module"],
                    item_name=sample["item_name"],
                    check_standard=sample.get("check_standard", ""),
                    check_method=sample.get("check_method", ""),
                    scoring_rule=sample.get("scoring_rule", ""),
                    issues=sample.get("issues", []),
                )

                actual_score = result.get("score", 0)
                expected_score = sample["expected_score"]

                # 允许±0.5的误差
                is_correct = abs(actual_score - expected_score) <= 0.5
                if is_correct:
                    correct += 1

                results.append({
                    "id": sample["id"],
                    "module": sample["module"],
                    "item": sample["item_name"][:30],
                    "expected": expected_score,
                    "actual": actual_score,
                    "diff": actual_score - expected_score,
                    "correct": is_correct,
                    "basis": result.get("scoring_basis", "")[:100],
                })

            except Exception as e:
                results.append({
                    "id": sample["id"],
                    "error": str(e),
                    "correct": False,
                })

        accuracy = (correct / total * 100) if total > 0 else 0

        # 打印详细结果
        print("\n" + "=" * 80)
        print(f"Golden Dataset评分一致性测试结果")
        print("=" * 80)
        print(f"总样本数: {total}")
        print(f"准确样本数: {correct}")
        print(f"准确率: {accuracy:.1f}%")
        print("-" * 80)

        for r in results[:10]:  # 只打印前10条
            if "error" in r:
                print(f"[FAIL] {r['id']}: ERROR - {r['error']}")
            elif r["correct"]:
                print(f"[PASS] {r['id']} | {r['module'][:8]} | 期望:{r['expected']:.1f} 实际:{r['actual']:.1f} | {r['item']}")
            else:
                print(f"[FAIL] {r['id']} | {r['module'][:8]} | 期望:{r['expected']:.1f} 实际:{r['actual']:.1f} | diff:{r['diff']:+.1f}")

        print("=" * 80)

        # 准入标准：准确率 >= 85%
        assert accuracy >= 85, f"评分准确率 {accuracy:.1f}% < 85%，需优化AI评分"

        return {
            "accuracy": accuracy,
            "total": total,
            "correct": correct,
            "results": results,
        }

    @pytest.mark.asyncio
    async def test_scoring_basis_quality(self, qwen_client, golden_dataset):
        """
        测试评分依据质量
        - 评分依据长度应 >= 20字符
        - 应包含与检查项相关的关键词
        """
        samples = golden_dataset.get("samples", [])
        if not samples:
            pytest.skip("Golden Dataset为空")

        quality_results = []
        for sample in samples[:5]:  # 测试前5条
            try:
                result = await qwen_client.score_item(
                    module_name=sample["module"],
                    item_name=sample["item_name"],
                    check_standard=sample.get("check_standard", ""),
                    check_method=sample.get("check_method", ""),
                    scoring_rule=sample.get("scoring_rule", ""),
                    issues=sample.get("issues", []),
                )

                basis = result.get("scoring_basis", "")
                item_name = sample["item_name"]

                # 检查依据长度
                length_ok = len(basis) >= 20

                # 检查是否引用了检查项名称
                # （简化检查：至少包含评分相关词汇）
                relevant_keywords = ["符合", "标准", "分", "问题", "检查", "要求", "规则"]
                contains_keywords = any(kw in basis for kw in relevant_keywords)

                quality_results.append({
                    "id": sample["id"],
                    "basis_length": len(basis),
                    "length_ok": length_ok,
                    "contains_keywords": contains_keywords,
                    "basis_preview": basis[:80] if basis else "",
                })

            except Exception as e:
                quality_results.append({
                    "id": sample["id"],
                    "error": str(e),
                })

        # 打印结果
        print("\n评分依据质量检查:")
        for r in quality_results:
            if "error" in r:
                print(f"  {r['id']}: ERROR - {r['error']}")
            else:
                status = "OK" if (r["length_ok"] and r["contains_keywords"]) else "WARN"
                print(f"  [{status}] {r['id']} | 长度:{r['basis_length']} | {r['basis_preview']}")

        return quality_results

    @pytest.mark.asyncio
    async def test_edge_case_handling(self, qwen_client):
        """
        测试边缘案例处理
        """
        edge_cases = [
            {
                "name": "多问题混杂",
                "module": "环境管理",
                "item_name": "垃圾分类投放",
                "scoring_rule": "完全合规5分；部分不合规3-4分；严重不合规1-2分",
                "check_standard": "垃圾分类准确率",
                "check_method": "抽查",
                "issues": [
                    {"description": "可回收垃圾桶内有厨余垃圾", "severity": "一般"},
                    {"description": "有害垃圾桶未封闭", "severity": "轻微"},
                    {"description": "其他垃圾桶标识不清晰", "severity": "轻微"},
                    {"description": "垃圾桶周围有散落垃圾", "severity": "一般"},
                ],
            },
            {
                "name": "严重问题",
                "module": "安全管理",
                "item_name": "消防通道畅通",
                "scoring_rule": "无问题5分；通道堵塞4分；严重堵塞3分以下",
                "check_standard": "消防通道无堵塞",
                "check_method": "现场抽查",
                "issues": [
                    {"description": "消防通道完全堵塞，堆放大量杂物", "severity": "严重"},
                ],
            },
            {
                "name": "描述缺失",
                "module": "设施维护",
                "item_name": "电梯维护",
                "scoring_rule": "正常5分；异常按情况扣分",
                "check_standard": "电梯定期维护",
                "check_method": "查看记录",
                "issues": [
                    {"description": "", "severity": ""},  # 空描述
                ],
            },
        ]

        results = []
        for case in edge_cases:
            try:
                result = await qwen_client.score_item(
                    module_name=case["module"],
                    item_name=case["item_name"],
                    check_standard=case["check_standard"],
                    check_method=case["check_method"],
                    scoring_rule=case["scoring_rule"],
                    issues=case["issues"],
                )

                results.append({
                    "name": case["name"],
                    "score": result.get("score"),
                    "basis": result.get("scoring_basis", "")[:80],
                    "success": True,
                })

            except Exception as e:
                results.append({
                    "name": case["name"],
                    "error": str(e),
                    "success": False,
                })

        # 打印结果
        print("\n边缘案例处理测试:")
        for r in results:
            status = "PASS" if r.get("success") else "FAIL"
            if r.get("success"):
                print(f"  [{status}] {r['name']} | 得分:{r['score']} | {r['basis']}")
            else:
                print(f"  [{status}] {r['name']} | ERROR: {r.get('error')}")

        return results


class ScoringConsistencyChecker:
    """
    评分一致性检查器（非测试用途，供CI/CD和生产监控调用）
    """

    def __init__(self, golden_dataset_path: Path = None):
        if golden_dataset_path is None:
            golden_dataset_path = Path(__file__).parent.parent / "data" / "golden_dataset.json"
        self.golden_dataset_path = golden_dataset_path
        self.generator = GoldenDatasetGenerator(self.golden_dataset_path.parent)

    def check_consistency(self, qwen_client: QwenClient = None) -> Dict:
        """执行评分一致性检查"""
        if qwen_client is None:
            qwen_client = QwenClient()

        dataset = self.generator.load_from_file()
        samples = dataset.get("samples", [])

        if not samples:
            return {
                "status": "no_dataset",
                "message": "Golden Dataset为空，请先生成",
                "accuracy": 0,
            }

        total = len(samples)
        correct = 0
        results = []

        import asyncio

        async def run_check():
            nonlocal correct, results
            for sample in samples:
                try:
                    result = await qwen_client.score_item(
                        module_name=sample["module"],
                        item_name=sample["item_name"],
                        check_standard=sample.get("check_standard", ""),
                        check_method=sample.get("check_method", ""),
                        scoring_rule=sample.get("scoring_rule", ""),
                        issues=sample.get("issues", []),
                    )

                    actual_score = result.get("score", 0)
                    expected_score = sample["expected_score"]
                    is_correct = abs(actual_score - expected_score) <= 0.5

                    if is_correct:
                        correct += 1

                    results.append({
                        "id": sample["id"],
                        "expected": expected_score,
                        "actual": actual_score,
                        "correct": is_correct,
                    })

                except Exception as e:
                    results.append({
                        "id": sample["id"],
                        "error": str(e),
                        "correct": False,
                    })

        # 运行异步检查
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_check())
        finally:
            loop.close()

        accuracy = (correct / total * 100) if total > 0 else 0

        return {
            "status": "completed",
            "accuracy": accuracy,
            "total": total,
            "correct": correct,
            "passed": accuracy >= 85,
            "results": results,
        }