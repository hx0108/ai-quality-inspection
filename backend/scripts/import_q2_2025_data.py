"""
导入 2025年第二季度 Excel 数据到数据库

数据来源:
  - 15个Excel文件 → ScoringResult 表 (评分结果)
  - 1个Word文件 → Issue 表 (问题点)  [暂不实现，先处理Excel]

执行方式:
  cd backend
  python scripts/import_q2_2025_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from pathlib import Path
from datetime import datetime
import uuid

from database import SessionLocal, engine
from models.models import (
    Project, InspectionTask, InspectionRecord,
    ScoringResult, Issue
)
from core.logger import get_logger

logger = get_logger("import_q2_2025")

# Excel文件根目录
EXCEL_DIR = Path(__file__).parent.parent.parent.parent / "F55第二季度品质检查报告"
CHECK_DATE = "2025-04-01"  # 2025年第二季度

# Sheet名称映射 (Excel Sheet名 → 系统模块名)
SHEET_MODULE_MAP = {
    "安防秩序": "安全管理",
    "客户服务": "客户服务",
    "机电运维": "机电运维",
    "设施维护": "设施维护",
    "环境管理": "环境管理",
    "综合管理": "综合管理",
    "财务管理": "财务管理",
}

# 严重程度判断
def infer_severity(score):
    """根据得分推断严重程度"""
    if pd.isna(score):
        return None
    try:
        score = float(score)
        if score <= 2:
            return "严重"
        elif score == 3:
            return "中等"
        else:
            return "一般"
    except:
        return "一般"


def get_or_create_task(db, project_id: int, check_date: str) -> InspectionTask:
    """获取或创建检查任务"""
    # 查找是否已存在
    task = db.query(InspectionTask).filter(
        InspectionTask.project_id == project_id,
        InspectionTask.check_date == check_date
    ).first()

    if task:
        return task

    # 创建新任务
    task_id = f"Q-{check_date[:10].replace('-', '')}-{uuid.uuid4().hex[:8]}"
    task = InspectionTask(
        task_id=task_id,
        project_id=project_id,
        check_date=check_date,
        status="completed",
        total_score=0,
        standard_type="diecheng"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    logger.info(f"创建任务: {task_id}, 项目ID={project_id}")
    return task


def get_or_create_record(db, task_id: str, module_name: str, project_id: int) -> InspectionRecord:
    """获取或创建检查记录"""
    record_id = f"REC-{CHECK_DATE[:10].replace('-', '')}-{uuid.uuid4().hex[:8]}"

    record = InspectionRecord(
        record_id=record_id,
        task_id=task_id,
        project_id=project_id,
        module_name=module_name,
        inspector_id=1,  # 假设系统管理员
        check_date=CHECK_DATE
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def import_excel_file(db, file_path: Path):
    """导入单个Excel文件"""
    logger.info(f"开始导入: {file_path.name}")

    # 从文件名提取项目名
    project_name = file_path.stem.replace('F55', '').replace('第二季度品质检查报告', '').strip()
    logger.info(f"  项目名: {project_name}")

    # 查找项目
    project = db.query(Project).filter(Project.name == project_name).first()
    if not project:
        logger.warning(f"  项目未找到: {project_name}，跳过")
        return 0, 0

    # 获取或创建任务
    task = get_or_create_task(db, project.id, CHECK_DATE)

    # 获取或创建记录（按模块）
    records = {}
    for sheet_name in SHEET_MODULE_MAP.keys():
        if sheet_name in pd.ExcelFile(file_path, engine='openpyxl').sheet_names:
            records[sheet_name] = get_or_create_record(db, task.task_id, SHEET_MODULE_MAP[sheet_name], project.id)

    # 读取Excel所有sheet
    df_all = pd.read_excel(file_path, sheet_name=None, engine='openpyxl')

    scoring_count = 0
    issue_count = 0

    for sheet_name, df in df_all.items():
        if sheet_name == '汇总分':
            continue
        if sheet_name not in SHEET_MODULE_MAP:
            logger.warning(f"  未知Sheet: {sheet_name}")
            continue

        module_name = SHEET_MODULE_MAP[sheet_name]
        record = records.get(sheet_name)
        if record is None:
            continue

        for idx, row in df.iterrows():
            score_value = row.get('评价得分')
            weight_value = row.get('权重')
            total_score_value = row.get('总得分')
            issue_desc = row.get('检查问题描述')
            check_method = row.get('抽样标准与检查方法') or ''
            scoring_rule = row.get('评价方法1') or ''

            # 跳过没有得分的行
            if pd.isna(score_value):
                continue

            # 处理特殊得分值
            try:
                score = float(score_value)
            except (ValueError, TypeError):
                # 跳过非数值得分（如"/"表示不涉及）
                logger.debug(f"  跳过非数值得分: {score_value}")
                continue

            # 构建item_id
            item_id = f"{module_name[:2]}-{idx:03d}"

            # 构建item_name (检查标准的前100字符)
            check_standard = str(row.get('检查标准', ''))[:100]

            # scoring_basis: 合格项填"检查合格"，有问题项填问题描述
            if pd.notna(issue_desc) and str(issue_desc).strip():
                scoring_basis = str(issue_desc).strip()
            else:
                scoring_basis = "检查合格，无问题发现"

            # 保存评分结果
            scoring_id = f"SCR-{uuid.uuid4().hex[:12]}"
            scoring = ScoringResult(
                scoring_id=scoring_id,
                record_id=record.record_id,
                module_name=module_name,
                item_id=item_id,
                item_name=check_standard,
                score=score,
                weight=float(weight_value) if pd.notna(weight_value) else 0.01,
                weighted_score=float(total_score_value) if pd.notna(total_score_value) else 0,
                scoring_basis=scoring_basis,
                improvement_suggestion="",
                check_standard=check_standard,
                check_method=str(check_method)[:200] if check_method else "",
                scoring_rule=str(scoring_rule)[:200] if scoring_rule else "",
            )
            db.add(scoring)
            scoring_count += 1

            # 如果有问题描述，创建Issue
            if pd.notna(issue_desc) and str(issue_desc).strip():
                issue_id = f"ISS-{uuid.uuid4().hex[:12]}"
                severity = infer_severity(score)

                # 推断位置（暂无）
                location = None

                issue = Issue(
                    issue_id=issue_id,
                    record_id=record.record_id,
                    module_name=module_name,
                    item_id=item_id,
                    description=str(issue_desc).strip(),
                    severity=severity,
                    location=location
                )
                db.add(issue)
                issue_count += 1

        logger.info(f"  Sheet '{sheet_name}': 导入完成")

    db.commit()
    logger.info(f"  共导入 {scoring_count} 条评分, {issue_count} 条问题")
    return scoring_count, issue_count


def main():
    logger.info("=" * 60)
    logger.info("开始导入 2025Q2 品质检查数据")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        # 获取所有Excel文件（排除临时文件）
        excel_files = [f for f in EXCEL_DIR.glob("*.xlsx") if not f.name.startswith('~$')]
        logger.info(f"找到 {len(excel_files)} 个Excel文件\n")

        total_scoring = 0
        total_issues = 0

        for file in sorted(excel_files):
            try:
                # 每个文件开始前清理session状态
                db.rollback()
                scoring_cnt, issue_cnt = import_excel_file(db, file)
                total_scoring += scoring_cnt
                total_issues += issue_cnt
            except Exception as e:
                logger.error(f"导入文件失败 {file.name}: {e}")
                db.rollback()
                import traceback
                traceback.print_exc()

        logger.info("\n" + "=" * 60)
        logger.info(f"导入完成! 共导入 {total_scoring} 条评分, {total_issues} 条问题")
        logger.info("=" * 60)

        # 验证
        logger.info("\n验证数据...")
        scoring_total = db.query(ScoringResult).count()
        issue_total = db.query(Issue).count()
        logger.info(f"数据库现有 {scoring_total} 条评分, {issue_total} 条问题")

    finally:
        db.close()


if __name__ == "__main__":
    main()