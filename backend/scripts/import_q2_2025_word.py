"""
导入 2025年第二季度 Word 问题汇总到知识库

将 Word 文档中的问题点导入到 Issue 表，供问答机器人检索

执行方式:
  cd backend
  python scripts/import_q2_2025_word.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from docx import Document
import uuid

from database import SessionLocal
from models.models import Project, Issue, InspectionRecord, InspectionTask
from core.logger import get_logger

logger = get_logger("import_word")

# Word文件路径
WORD_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "..", "F55第二季度品质检查汇总.docx"
)

# 标准项目列表
VALID_PROJECTS = [
    "金域蓝湾", "田心康苑", "金域悦府", "荷花紫薇", "蓝山桐林",
    "云山花园", "峰境花园", "玉兰苑", "天河御品", "御金沙",
    "中新里", "幸福悦", "四季花城", "幸福荟", "幸福誉",
    "岚林花园", "丹桂园", "金兰花园"
]

# 模块名称映射
MODULE_PATTERNS = {
    "安防": "安全管理",
    "秩序": "安全管理",
    "消防": "安全管理",
    "防盗": "安全管理",
    "停车": "安全管理",
    "客户": "客户服务",
    "管家": "客户服务",
    "诉求": "客户服务",
    "机电": "机电运维",
    "电梯": "机电运维",
    "设备": "机电运维",
    "配电": "机电运维",
    "设施": "设施维护",
    "维护": "设施维护",
    "环境": "环境管理",
    "绿化": "环境管理",
    "保洁": "环境管理",
    "垃圾": "环境管理",
    "综合": "综合管理",
    "财务": "财务管理",
}


def is_module_header(text: str) -> bool:
    """判断是否是模块标题"""
    patterns = ['（一）', '（二）', '（三）', '（四）', '（五）', '（六）', '（七）', '（八）']
    for p in patterns:
        if p in text and len(text) < 25:
            return True
    return False


def infer_module(text: str) -> str:
    """根据内容推断模块"""
    for pattern, module in MODULE_PATTERNS.items():
        if pattern in text:
            return module
    return "综合管理"  # 默认模块


def parse_word_document():
    """解析Word文档，返回问题列表（按项目和模块组织）"""
    logger.info(f"解析Word文档: {WORD_FILE}")

    doc = Document(WORD_FILE)
    paragraphs = [p.text.strip() for p in doc.paragraphs]

    # 按项目分割
    project_issues = {}  # {project_name: {module_name: [issues]}}
    current_project = None
    current_module = None

    for i, text in enumerate(paragraphs):
        if not text:
            continue

        # 检查是否是项目名
        if text in VALID_PROJECTS:
            current_project = text
            current_module = None
            if current_project not in project_issues:
                project_issues[current_project] = {}
            logger.info(f"发现项目: {current_project}")
            continue

        # 检查是否是模块标题
        if is_module_header(text):
            current_module = infer_module(text)
            if current_project and current_module:
                if current_module not in project_issues[current_project]:
                    project_issues[current_project][current_module] = []
            continue

        # 如果是问题描述
        if current_project and current_module and len(text) > 5:
            # 跳过数字开头的列表项（可能会和标题重复）
            if len(text) > 2 and text[0].isdigit() and text[1] in '、.':
                continue
            # 跳过重复的问题
            if text not in project_issues[current_project].get(current_module, []):
                project_issues[current_project][current_module].append(text)

    return project_issues


def infer_severity_from_text(text: str) -> str:
    """根据问题描述推断严重程度"""
    # 严重关键词
    severe_keywords = ["故障", "隐患", "严重", "违规", "缺失", "过期", "未按", "危险", "事故"]
    # 中等关键词
    medium_keywords = ["不足", "不完善", "不规范", "未及时", "不到位", "欠缺"]

    for kw in severe_keywords:
        if kw in text:
            return "严重"
    for kw in medium_keywords:
        if kw in text:
            return "中等"
    return "一般"


def main():
    logger.info("=" * 60)
    logger.info("开始导入 Word 问题汇总到知识库")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        # 解析Word文档
        project_issues = parse_word_document()

        total_issues = 0
        skip_count = 0
        project_stats = {}

        for project_name, modules in project_issues.items():
            # 查找项目
            project = db.query(Project).filter(Project.name == project_name).first()
            if not project:
                logger.warning(f"项目未找到: {project_name}，跳过{sum(len(v) for v in modules.values())}个问题")
                skip_count += sum(len(v) for v in modules.values())
                continue

            # 查找或创建 2025Q2 的任务
            task = db.query(InspectionTask).filter(
                InspectionTask.project_id == project.id,
                InspectionTask.check_date == "2025-04-01"
            ).first()

            if not task:
                logger.warning(f"任务未找到: 项目={project_name}，跳过{sum(len(v) for v in modules.values())}个问题")
                skip_count += sum(len(v) for v in modules.values())
                continue

            # 查找该任务的记录
            records = db.query(InspectionRecord).filter(
                InspectionRecord.task_id == task.task_id
            ).all()

            if not records:
                logger.warning(f"记录未找到: 任务={task.task_id}，跳过{sum(len(v) for v in modules.values())}个问题")
                skip_count += sum(len(v) for v in modules.values())
                continue

            # 建立模块到记录的映射
            module_to_record = {}
            for r in records:
                if r.module_name not in module_to_record:
                    module_to_record[r.module_name] = r

            project_issue_count = 0

            # 导入每个问题
            for module_name, issues in modules.items():
                # 获取对应模块的记录
                record = module_to_record.get(module_name)
                if not record:
                    record = records[0]  # 默认用第一个

                for issue_text in issues:
                    # 检查是否已存在
                    existing = db.query(Issue).filter(
                        Issue.record_id == record.record_id,
                        Issue.description == issue_text
                    ).first()

                    if existing:
                        continue

                    # 推断严重程度
                    severity = infer_severity_from_text(issue_text)

                    # 创建Issue
                    issue_id = f"ISS-W-{uuid.uuid4().hex[:12]}"
                    # Word中的问题使用模块前缀+序号
                    item_id = f"WORD-{module_name[:2]}-{total_issues:04d}"

                    issue = Issue(
                        issue_id=issue_id,
                        record_id=record.record_id,
                        module_name=module_name,
                        item_id=item_id,
                        description=issue_text,
                        severity=severity,
                        location=None
                    )
                    db.add(issue)
                    total_issues += 1
                    project_issue_count += 1

            project_stats[project_name] = project_issue_count
            logger.info(f"项目 {project_name}: 导入 {project_issue_count} 个问题")

        db.commit()

        logger.info("\n" + "=" * 60)
        logger.info(f"导入完成! 共导入 {total_issues} 个问题")
        logger.info(f"跳过 {skip_count} 个问题（未匹配项目）")
        logger.info("=" * 60)

        # 打印各项目统计
        logger.info("\n各项目导入统计:")
        for proj, count in sorted(project_stats.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {proj}: {count}个")

        # 验证
        logger.info("\n验证数据...")
        issue_count = db.query(Issue).count()
        word_issues = db.query(Issue).filter(Issue.item_id.like('WORD-%')).count()
        logger.info(f"数据库现有 {issue_count} 条Issue，其中Word导入 {word_issues} 条")

    finally:
        db.close()


if __name__ == "__main__":
    main()
