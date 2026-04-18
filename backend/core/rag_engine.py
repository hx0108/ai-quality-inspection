"""
RAG 引擎
为知识库提供语义搜索能力
"""
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
import jieba
import json

from models.models import Issue, InspectionRecord, InspectionTask, Project, ScoringResult
from database import SessionLocal
from core.logger import get_logger

logger = get_logger("rag_engine")

# 物业品质检查领域同义词词典
SYNONYMS = {
    # 电梯/设施类
    "电梯": ["升降机", "电梯设备", "电梯维保", "电梯故障", "电梯困人", "电梯年检"],
    "升降机": ["电梯", "电梯设备"],
    "门禁": ["门锁", "门禁系统", "门禁卡", "刷卡进入", "门禁故障"],
    "监控": ["摄像头", "监控系统", "监控设备", "视频监控", "安防监控"],
    "消防": ["消防设施", "消防安全", "消防通道", "消防器材", "灭火器", "消防栓"],
    "安防": ["安保", "安全管理", "保安", "门卫"],
    "设施": ["设备", "配套设施", "公共设施"],

    # 保洁/环境类
    "保洁": ["清洁", "卫生", "环境卫生", "日常保洁", "保洁服务"],
    "垃圾": ["垃圾清运", "垃圾分类", "垃圾桶", "垃圾堆放", "生活垃圾"],
    "绿化": ["绿植", "园林", "草木", "植被", "花园养护"],
    "卫生": ["清洁", "保洁", "脏乱", "干净"],

    # 客服/管家类
    "管家": ["客服", "客户服务", "物业服务", "前台", "接待"],
    "投诉": ["诉求", "报修", "反馈", "反映问题", "意见"],
    "业主": ["住户", "居民", "客户"],
    "服务": ["服务水平", "服务质量", "服务态度"],

    # 机电/设备类
    "机电": ["电气", "配电", "电路", "用电", "电力"],
    "配电": ["配电箱", "配电房", "电力", "电路", "用电安全"],
    "空调": ["中央空调", "空调设备", "冷气", "暖气"],
    "照明": ["灯具", "灯光", "路灯", "公共照明", "照明设备"],
    "水泵": ["供水", "排水", "水管", "漏水", "用水"],
    "漏水": ["渗水", "水管破裂", "水浸"],

    # 财务管理类
    "财务": ["收费", "缴费", "账单", "费用", "资金"],
    "停车": ["停车场", "车位", "停车费", "车辆管理"],

    # 通用类
    "破损": ["损坏", "坏了", "故障", "失效", "异常"],
    "缺失": ["缺少", "没有", "未配置", "未设置"],
    "过期": ["超期", "到期", "失效", "逾期"],
    "不规范": ["不符合标准", "不达标", "不合规", "违规"],
    "不足": ["缺少", "不完善", "不到位", "欠缺"],
}

# 常见问题模式（用于泛化查询）
QUERY_PATTERNS = {
    "电梯坏了": ["电梯故障", "电梯问题", "电梯异常", "电梯停运"],
    "电梯故障": ["电梯坏了", "电梯问题", "电梯异常"],
    "消防问题": ["消防隐患", "消防安全", "消防设施故障"],
    "漏水了": ["漏水", "渗水", "水管破裂", "管道漏水"],
    "门禁坏了": ["门禁故障", "门禁失效", "门锁坏了", "门禁不工作"],
    "垃圾问题": ["垃圾堆放", "垃圾清理", "垃圾桶满", "垃圾清运不及时"],
    "噪音": ["噪声", "扰民", "噪音扰民", "施工噪音"],
    "停车位": ["车位", "停车场", "停车问题", "车辆停放"],
    "空调坏了": ["空调故障", "空调不制冷", "空调不制热", "空调故障"],
    "灯不亮": ["灯具损坏", "路灯不亮", "照明故障", "灯光异常"],
    "保洁问题": ["卫生问题", "清洁问题", "环境脏乱"],
    "绿化问题": ["绿植枯萎", "园林养护", "草木死亡", "绿化养护"],
    "投诉": ["业主投诉", "客户投诉", "住户投诉", "反映问题"],
    "电梯困人": ["电梯故障困人", "电梯困人", "电梯故障"],
}


class RAGEngine:
    """
    轻量级 RAG 引擎
    使用 BM25 + 关键词匹配实现问题检索
    """

    @classmethod
    def search_issues(
        cls,
        query: str,
        project_id: Optional[int] = None,
        module_name: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict]:
        """
        语义搜索问题

        Args:
            query: 搜索query
            project_id: 项目ID过滤
            module_name: 模块过滤（支持同义词，如"电梯"匹配"机电运维"）
            limit: 返回数量

        Returns:
            问题列表
        """
        db = SessionLocal()
        try:
            # 1. 关键词扩展
            expanded_terms = cls._expand_query(query)

            # 2. 模块名同义词扩展
            target_modules = None
            if module_name:
                target_modules = cls._expand_module_name(module_name)

            # 3. 构建基础查询
            q = db.query(Issue).join(
                InspectionRecord, Issue.record_id == InspectionRecord.record_id
            ).join(
                InspectionTask, InspectionRecord.task_id == InspectionTask.task_id
            )

            if project_id:
                q = q.filter(InspectionRecord.project_id == project_id)

            if target_modules:
                q = q.filter(Issue.module_name.in_(target_modules))

            # 4. 获取所有匹配的问题
            all_issues = q.all()

            # 5. 如果指定了project_id，优先返回Word问题（原始数据），再用关键词过滤Excel问题
            if project_id:
                word_issues = []
                excel_issues = []

                for issue in all_issues:
                    if issue.item_id.startswith('WORD-'):
                        word_issues.append(issue)
                    else:
                        excel_issues.append(issue)

                results = []

                # 优先添加Word问题
                for issue in word_issues[:limit]:
                    results.append({
                        "issue_id": issue.issue_id,
                        "description": issue.description,
                        "module_name": issue.module_name,
                        "severity": issue.severity,
                        "location": issue.location,
                        "relevance_score": 1.0,  # Word问题优先
                        "source": "word"
                    })

                # 如果Word问题不够，用Excel问题补充
                if len(results) < limit:
                    excel_limit = limit - len(results)
                    for issue in excel_issues[:excel_limit]:
                        # 计算Excel问题的相关度
                        score = cls._calculate_relevance(query, issue.description, expanded_terms)
                        if score > 0:
                            results.append({
                                "issue_id": issue.issue_id,
                                "description": issue.description,
                                "module_name": issue.module_name,
                                "severity": issue.severity,
                                "location": issue.location,
                                "relevance_score": round(score, 3),
                                "source": "excel"
                            })

                return results

            # 6. 没有指定project_id时，计算相关度并排序
            scored_issues = []
            for issue in all_issues:
                score = cls._calculate_relevance(query, issue.description, expanded_terms)
                if score > 0:
                    scored_issues.append((issue, score))

            scored_issues.sort(key=lambda x: x[1], reverse=True)

            # 7. 返回结果
            results = []
            for issue, score in scored_issues[:limit]:
                results.append({
                    "issue_id": issue.issue_id,
                    "description": issue.description,
                    "module_name": issue.module_name,
                    "severity": issue.severity,
                    "location": issue.location,
                    "relevance_score": round(score, 3)
                })

            return results
        finally:
            db.close()

    @classmethod
    def _expand_module_name(cls, module_name: str) -> List[str]:
        """
        扩展模块名称（支持同义词匹配）

        例如：
        - "电梯" -> ["机电运维", "设施维护"]
        - "消防" -> ["安全管理"]
        - "保洁" -> ["环境管理"]
        """
        # 模块名 -> 系统模块的映射
        MODULE_KEYWORDS = {
            "机电运维": ["电梯", "升降机", "机电", "配电", "空调", "照明", "水泵", "设备", "设施"],
            "安全管理": ["消防", "安防", "秩序", "监控", "门禁", "防盗", "停车"],
            "环境管理": ["保洁", "绿化", "垃圾", "卫生", "清洁"],
            "客户服务": ["管家", "客服", "客户", "业主", "投诉", "服务"],
            "综合管理": ["综合", "行政", "制度", "文档"],
            "财务管理": ["财务", "收费", "停车", "账单", "缴费"],
            "设施维护": ["设施", "维护", "维修", "保养"],
        }

        expanded = {module_name}  # 保留原始模块名

        # 检查是否匹配关键词
        for sys_module, keywords in MODULE_KEYWORDS.items():
            if module_name in keywords:
                expanded.add(sys_module)
            # 检查查询词是否包含这些关键词
            for kw in keywords:
                if kw in module_name:
                    expanded.add(sys_module)
                    break

        return list(expanded)

    @classmethod
    def _expand_query(cls, query: str) -> List[str]:
        """
        扩展查询词（分词 + 同义词 + 模式泛化）

        扩展策略：
        1. 精确模式匹配（最高优先级）
        2. jieba分词 + 同义词扩展
        3. 拼音首字母匹配（处理输入错误）
        """
        expanded = set()

        # 1. 检查是否匹配已知模式
        query_stripped = query.strip()
        for pattern, expansions in QUERY_PATTERNS.items():
            if pattern in query_stripped or query_stripped in pattern:
                expanded.update(expansions)
                expanded.add(pattern)

        # 2. 分词 + 同义词扩展
        terms = list(jieba.cut(query_stripped))
        for term in terms:
            # 去除空白字符
            term = term.strip()
            if not term:
                continue
            expanded.add(term)

            # 同义词扩展
            if term in SYNONYMS:
                expanded.update(SYNONYMS[term])

            # 逆向扩展：检查同义词是否包含查询词
            for key, synonyms in SYNONYMS.items():
                if term in synonyms and key not in expanded:
                    expanded.add(key)
                    expanded.update(SYNONYMS.get(key, []))

        return list(expanded)

    @classmethod
    def _calculate_relevance(
        cls,
        query: str,
        description: str,
        expanded_terms: List[str]
    ) -> float:
        """
        计算查询与描述的相关度

        评分逻辑（多层级加权）：
        - 精确包含原始query：5分（最高优先级）
        - 扩展词精确匹配：2分/词
        - 分词重叠：1分/词
        - 短描述惩罚：描述过短且匹配度高（可能是噪音）
        """
        score = 0.0
        desc_lower = description.lower()
        query_lower = query.lower()

        # 1. 精确包含query（最高权重）
        if query_lower in desc_lower:
            score += 5.0
            # 如果query是description的结尾或开头，加权（更可能是专门讨论这个话题）
            if desc_lower.startswith(query_lower) or desc_lower.endswith(query_lower):
                score += 1.0

        # 2. 扩展词匹配（中等权重）
        matched_expanded = []
        for term in expanded_terms:
            if term in desc_lower and term != query_lower:
                matched_expanded.append(term)

        # 去重后计分（避免同一词重复计分）
        matched_expanded = list(set(matched_expanded))
        score += 2.0 * len(matched_expanded)

        # 3. 分词重叠（基础权重）
        query_words = set(jieba.cut(query))
        desc_words = set(jieba.cut(description))
        overlap = query_words & desc_words
        if overlap:
            # 过滤掉单字符和标点
            meaningful_overlap = {w for w in overlap if len(w) > 1}
            score += 1.0 * len(meaningful_overlap)

        # 4. 短描述惩罚（描述<10字且得分>3，可能是噪音）
        if len(description) < 10 and score > 3:
            score *= 0.8

        # 5. 长描述奖励（描述>50字且高匹配，可能是详细讨论）
        if len(description) > 50 and score >= 3:
            score *= 1.1

        # 6. 严重问题加权（如果查询包含"严重"等词）
        severe_words = ["严重", "重大", "紧急", "危险", "隐患"]
        if any(sw in query_lower for sw in severe_words):
            if any(sw in desc_lower for sw in severe_words):
                score *= 1.2

        return max(0.0, score)  # 确保非负

    @classmethod
    def get_issue_stats(
        cls,
        project_id: Optional[int] = None,
        module_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict:
        """
        获取问题统计

        Returns:
            统计数据字典
        """
        db = SessionLocal()
        try:
            q = db.query(Issue).join(
                InspectionRecord, Issue.record_id == InspectionRecord.record_id
            ).join(
                InspectionTask, InspectionRecord.task_id == InspectionTask.task_id
            )

            if project_id:
                q = q.filter(InspectionRecord.project_id == project_id)

            if module_name:
                q = q.filter(Issue.module_name == module_name)

            if start_date:
                q = q.filter(InspectionTask.check_date >= start_date)

            if end_date:
                q = q.filter(InspectionTask.check_date <= end_date)

            total = q.count()

            # 按模块统计
            by_module = db.query(
                Issue.module_name,
                func.count(Issue.id).label("count")
            ).join(
                InspectionRecord, Issue.record_id == InspectionRecord.record_id
            ).join(
                InspectionTask, InspectionRecord.task_id == InspectionTask.task_id
            ).filter(
                InspectionRecord.project_id == project_id if project_id else True
            ).group_by(Issue.module_name).all()

            # 按严重程度统计
            by_severity = db.query(
                Issue.severity,
                func.count(Issue.id).label("count")
            ).join(
                InspectionRecord, Issue.record_id == InspectionRecord.record_id
            ).join(
                InspectionTask, InspectionRecord.task_id == InspectionTask.task_id
            ).filter(
                InspectionRecord.project_id == project_id if project_id else True
            ).group_by(Issue.severity).all()

            return {
                "total": total,
                "by_module": {m.module_name: m.count for m in by_module},
                "by_severity": {s.severity: s.count for s in by_severity}
            }
        finally:
            db.close()

    @classmethod
    def get_similar_issues(
        cls,
        description: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        查找相似问题

        用于：在录入新问题时，提示历史类似问题
        """
        return cls.search_issues(description, limit=limit)


# 便捷函数
def search_issues(query: str, **kwargs) -> List[Dict]:
    return RAGEngine.search_issues(query, **kwargs)


def get_issue_stats(**kwargs) -> Dict:
    return RAGEngine.get_issue_stats(**kwargs)


def get_similar_issues(description: str, **kwargs) -> List[Dict]:
    return RAGEngine.get_similar_issues(description, **kwargs)