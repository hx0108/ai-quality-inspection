"""
Golden Dataset 生成器
从历史评分数据中清洗高质量样本用于评分一致性测试
"""
import json
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy import func
from database import SessionLocal
from models.models import ScoringResult, Issue, InspectionRecord
from pathlib import Path


class GoldenDatasetGenerator:
    """Golden Dataset 生成器"""

    # 筛选高质量样本的标准
    QUALITY_THRESHOLDS = {
        "min_edit_count": 1,           # 至少被人工编辑过1次（证明有参考价值）
        "max_edit_count": 10,           # 不会被过度编辑（可能是标注错误）
        "min_scoring_basis_length": 30,  # 评分依据至少30字符
        "score_diff_tolerance": 1.0,    # AI与人工分数差异容忍度（用于回归检测）
    }

    def __init__(self, output_dir: Optional[Path] = None):
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "data"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_from_history(self, min_samples_per_module: int = 5) -> List[Dict]:
        """
        从历史数据中清洗Golden Dataset

        筛选标准：
        1. 有人工修改记录（is_edited=True）
        2. 有明确的修改原因（edit_reason不为空）
        3. 评分依据长度足够
        4. 同一检查项不多次入选（保证多样性）
        """
        db = SessionLocal()
        try:
            # 查询有人工修改且有评分依据的记录
            edited_records = db.query(
                ScoringResult
            ).join(
                InspectionRecord, ScoringResult.record_id == InspectionRecord.record_id
            ).filter(
                ScoringResult.is_edited == True,
                ScoringResult.original_score != None,
                ScoringResult.edit_reason != None,
                ScoringResult.scoring_basis != None,
                func.length(ScoringResult.scoring_basis) >= self.QUALITY_THRESHOLDS["min_scoring_basis_length"],
            ).order_by(
                ScoringResult.edited_at.desc()
            ).limit(500).all()

            # 按模块分组，每模块取固定数量
            module_samples = {}
            for record in edited_records:
                module = record.module_name
                if module not in module_samples:
                    module_samples[module] = []

                # 检查是否已收录该检查项
                existing_items = [s["item_id"] for s in module_samples[module]]
                if record.item_id in existing_items:
                    continue

                # 构建样本
                sample = self._build_sample(record)
                if sample:
                    module_samples[module].append(sample)

            # 合并并保存
            all_samples = []
            for module, samples in module_samples.items():
                all_samples.extend(samples[:min_samples_per_module])

            return all_samples

        finally:
            db.close()

    def _build_sample(self, record: ScoringResult) -> Optional[Dict]:
        """从评分记录构建Golden Sample"""
        # 获取问题信息
        issues = db.query(Issue).filter(
            Issue.record_id == record.record_id,
            Issue.item_id == record.item_id,
        ).all() if record.record_id else []

        issues_data = []
        for issue in issues:
            issues_data.append({
                "description": issue.description or "",
                "severity": issue.severity or "一般",
                "location": issue.location or "",
            })

        # 计算最终分数（人工修正后的分数）
        final_score = float(record.score)
        original_score = float(record.original_score) if record.original_score else final_score

        return {
            "id": f"GD-{record.module_name[:2].upper()}-{record.item_id.replace('.', '')}",
            "module": record.module_name,
            "item_id": record.item_id,
            "item_name": record.item_name or "",
            "check_standard": record.check_standard or "",
            "check_method": record.check_method or "",
            "scoring_rule": record.scoring_rule or "",
            "issues": issues_data,
            "expected_score": final_score,
            "original_ai_score": original_score,
            "edit_reason": record.edit_reason,
            "scoring_basis": record.scoring_basis,
            "improvement_suggestion": record.improvement_suggestion,
        }

    def save_to_file(self, samples: List[Dict], filename: str = "golden_dataset.json") -> Path:
        """保存Golden Dataset到文件"""
        filepath = self.output_dir / filename

        # 添加元数据
        dataset = {
            "metadata": {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_samples": len(samples),
                "modules": list(set(s["module"] for s in samples)),
            },
            "samples": samples,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)

        return filepath

    def load_from_file(self, filename: str = "golden_dataset.json") -> Dict:
        """从文件加载Golden Dataset"""
        filepath = self.output_dir / filename
        if not filepath.exists():
            return {"metadata": {}, "samples": []}

        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def validate_sample(self, sample: Dict) -> List[str]:
        """验证样本完整性，返回错误列表"""
        errors = []
        required_fields = ["id", "module", "item_id", "item_name", "scoring_rule", "expected_score"]

        for field in required_fields:
            if field not in sample or not sample[field]:
                errors.append(f"缺少必填字段: {field}")

        if "expected_score" in sample:
            score = sample["expected_score"]
            if not isinstance(score, (int, float)) or score < 0 or score > 5:
                errors.append(f"分数必须在0-5之间: {score}")

        return errors

    def validate_dataset(self, dataset: Dict) -> Dict:
        """验证整个Dataset"""
        samples = dataset.get("samples", [])
        all_errors = []

        for i, sample in enumerate(samples):
            errors = self.validate_sample(sample)
            if errors:
                all_errors.append({
                    "index": i,
                    "sample_id": sample.get("id", "unknown"),
                    "errors": errors,
                })

        return {
            "total_samples": len(samples),
            "valid_samples": len(samples) - len(all_errors),
            "errors": all_errors,
            "is_valid": len(all_errors) == 0,
        }


def generate_golden_dataset(output_path: Optional[Path] = None) -> Dict:
    """一键生成Golden Dataset"""
    generator = GoldenDatasetGenerator(output_path)
    samples = generator.generate_from_history(min_samples_per_module=5)
    filepath = generator.save_to_file(samples)

    validation = generator.validate_dataset({"samples": samples})

    return {
        "status": "success",
        "filepath": str(filepath),
        "total_samples": len(samples),
        "validation": validation,
    }