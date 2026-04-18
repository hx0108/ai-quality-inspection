"""
评分规则编译器（Skill Compilation）
从人工修正案例中抽象提取评分规则，替代简单案例罗列
"""
import json
import uuid
import hashlib
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict

from sqlalchemy import func, desc
from database import SessionLocal
from models.models import ScoringResult, ScoringRule
from core.llm_client import QwenClient
from core.logger import get_logger

logger = get_logger("rule_compiler")

# 编译配置
COMPILE_CONFIG = {
    "min_cases_per_group": 3,        # 同组最少修正案例数
    "lookback_days": 90,             # 回溯天数
    "max_rules_per_module": 5,       # 每模块最多规则数
    "similarity_threshold": 0.6,     # 规则合并相似度阈值
}


class RuleCompiler:
    """
    技能编译器：将散乱的人工修正案例 → 抽象评分规则

    工作流程：
    1. 从 ScoringResult 提取 is_edited=True 且有 edit_reason 的记录
    2. 按 module_name + edit_reason 分组
    3. 对每组用 LLM (Qwen) 提炼抽象规则
    4. 合并相似规则，计算支持率和 AI 偏差
    5. 写入 scoring_rules 表
    """

    async def compile_rules(self, module_name: str = None) -> List[ScoringRule]:
        """
        编译评分规则

        Args:
            module_name: 指定模块，None 表示全部模块

        Returns:
            新增/更新的规则列表
        """
        db = SessionLocal()
        try:
            # 1. 查询人工修正记录
            cases = self._load_edit_cases(db, module_name)
            if not cases:
                logger.info("无人工修正记录，跳过编译")
                return []

            # 2. 按模块 + edit_reason 分组
            groups = self._group_cases(cases)
            logger.info(f"分组完成: {len(groups)} 组，来自 {len(cases)} 条修正记录")

            # 3. 对每组提炼规则
            compiled_rules = []
            for key, group_cases in groups.items():
                if len(group_cases) < COMPILE_CONFIG["min_cases_per_group"]:
                    continue

                rule = await self._compile_group(key, group_cases)
                if rule:
                    compiled_rules.append(rule)

            # 4. 合并相似规则并写入DB
            saved = self._save_rules(db, compiled_rules)
            logger.info(f"规则编译完成: {len(saved)} 条新规则")
            return saved

        finally:
            db.close()

    def _load_edit_cases(self, db, module_name: str = None) -> List[Dict]:
        """加载人工修正记录"""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=COMPILE_CONFIG["lookback_days"])

        query = db.query(
            ScoringResult.module_name,
            ScoringResult.item_id,
            ScoringResult.item_name,
            ScoringResult.original_score,
            ScoringResult.score,
            ScoringResult.scoring_basis,
            ScoringResult.edit_reason,
            ScoringResult.check_standard,
            ScoringResult.scoring_rule,
        ).filter(
            ScoringResult.is_edited == True,
            ScoringResult.original_score != None,
            ScoringResult.edit_reason != None,
            ScoringResult.edit_reason != "",
            ScoringResult.edited_at >= cutoff,
        )

        if module_name:
            query = query.filter(ScoringResult.module_name == module_name)

        rows = query.order_by(desc(ScoringResult.edited_at)).limit(200).all()

        cases = []
        for r in rows:
            delta = float(r.original_score) - float(r.score)
            cases.append({
                "module_name": r.module_name,
                "item_id": r.item_id,
                "item_name": r.item_name or "",
                "original_score": float(r.original_score),
                "human_score": float(r.score),
                "delta": delta,
                "direction": "偏高" if delta > 0 else "偏低",
                "scoring_basis": r.scoring_basis or "",
                "edit_reason": r.edit_reason or "",
                "check_standard": (r.check_standard or "")[:80],
                "scoring_rule": (r.scoring_rule or "")[:100],
            })

        return cases

    def _group_cases(self, cases: List[Dict]) -> Dict[str, List[Dict]]:
        """按模块+edit_reason分组"""
        groups = defaultdict(list)
        for c in cases:
            key = f"{c['module_name']}|{c['edit_reason']}"
            groups[key].append(c)
        return dict(groups)

    async def _compile_group(self, key: str, cases: List[Dict]) -> Optional[Dict]:
        """对一组相似修正案例提炼规则"""
        parts = key.split("|")
        module_name = parts[0]
        edit_reason = parts[1] if len(parts) > 1 else ""

        # 构建提炼 Prompt
        cases_text = ""
        for i, c in enumerate(cases[:10], 1):  # 最多取10条
            cases_text += (
                f"\n{i}. [{c['item_name'][:30]}] "
                f"AI给{c['original_score']}分→人工修正{c['human_score']}分"
                f"(AI{c['direction']}{abs(c['delta']):.1f}分, "
                f"原因:{c['edit_reason']})"
            )

        # 计算统计信息
        avg_delta = sum(c["delta"] for c in cases) / len(cases)
        direction = "偏高" if avg_delta > 0 else "偏低"

        prompt = f"""根据以下 {len(cases)} 条评分修正记录，提炼一条简洁的评分规则。

【模块】{module_name}
【修正原因】{edit_reason}
【修正记录】{cases_text}
【统计】AI平均{direction}{abs(avg_delta):.1f}分

请输出JSON格式：
{{
    "rule_text": "<一句话规则，描述什么情况下应该怎么评分>",
    "score_directive": "<评分指令，如'扣2-3分'或'直接判0分'或'多扣0.5分'>",
    "issue_keyword": "<触发此规则的问题关键词，用|分隔>",
    "severity_pattern": "<适用严重程度: 严重/一般/轻微/any>"
}}

只输出JSON，不要其他文字。"""

        try:
            llm = QwenClient()
            result = await llm.chat(
                messages=[
                    {"role": "system", "content": "你是评分规则提炼专家。从修正案例中提取通用评分规则，输出合法JSON。"},
                    {"role": "user", "content": prompt},
                ],
                max_retries=1,
            )

            content = result.get("content", "")
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            parsed = json.loads(content.strip())

            return {
                "module_name": module_name,
                "rule_text": parsed.get("rule_text", ""),
                "score_directive": parsed.get("score_directive", ""),
                "issue_keyword": parsed.get("issue_keyword", ""),
                "severity_pattern": parsed.get("severity_pattern", "any"),
                "source_case_count": len(cases),
                "avg_ai_deviation": round(avg_delta, 2),
                "support_rate": round(len(cases) / max(len(cases), 1), 4),
            }

        except Exception as e:
            logger.warning(f"规则提炼失败 ({key}): {e}")
            return None

    def _save_rules(self, db, rules: List[Dict]) -> List[ScoringRule]:
        """合并相似规则并写入DB"""
        saved = []

        # 按模块分组
        by_module = defaultdict(list)
        for r in rules:
            by_module[r["module_name"]].append(r)

        for module_name, module_rules in by_module.items():
            # 查询该模块已有的规则
            existing = db.query(ScoringRule).filter(
                ScoringRule.module_name == module_name,
                ScoringRule.is_active == True,
            ).all()

            for new_rule in module_rules:
                # 检查是否与已有规则相似（按 issue_keyword 匹配）
                keyword_set = set(new_rule["issue_keyword"].split("|"))
                merged = False

                for ex in existing:
                    ex_keywords = set((ex.issue_keyword or "").split("|"))
                    overlap = keyword_set & ex_keywords
                    similarity = len(overlap) / max(len(keyword_set), len(ex_keywords), 1)

                    if similarity >= COMPILE_CONFIG["similarity_threshold"]:
                        # 合并：更新统计，保留 support_rate 更高的规则文本
                        ex.source_case_count += new_rule["source_case_count"]
                        if new_rule["support_rate"] > float(ex.support_rate or 0):
                            ex.rule_text = new_rule["rule_text"]
                            ex.score_directive = new_rule["score_directive"]
                            ex.issue_keyword = "|".join(keyword_set | ex_keywords)
                        ex.avg_ai_deviation = round(
                            (float(ex.avg_ai_deviation or 0) + new_rule["avg_ai_deviation"]) / 2, 2
                        )
                        ex.updated_at = datetime.utcnow()
                        saved.append(ex)
                        merged = True
                        break

                if not merged:
                    # 新建规则
                    today = datetime.now().strftime("%Y%m%d")
                    rule_id = f"RULE-{today}-{uuid.uuid4().hex[:6].upper()}"

                    rule = ScoringRule(
                        rule_id=rule_id,
                        module_name=module_name,
                        severity_pattern=new_rule["severity_pattern"],
                        issue_keyword=new_rule["issue_keyword"],
                        rule_text=new_rule["rule_text"],
                        score_directive=new_rule["score_directive"],
                        source_case_count=new_rule["source_case_count"],
                        support_rate=new_rule["support_rate"],
                        avg_ai_deviation=new_rule["avg_ai_deviation"],
                    )
                    db.add(rule)
                    saved.append(rule)
                    existing.append(rule)  # 防止同一批内重复创建

            # 每模块最多保留 N 条活跃规则
            active_rules = db.query(ScoringRule).filter(
                ScoringRule.module_name == module_name,
                ScoringRule.is_active == True,
            ).order_by(desc(ScoringRule.source_case_count)).all()

            if len(active_rules) > COMPILE_CONFIG["max_rules_per_module"]:
                for r in active_rules[COMPILE_CONFIG["max_rules_per_module"]:]:
                    r.is_active = False

        db.commit()
        return saved

    def get_rules_for_prompt(self, module_name: str, limit: int = 5) -> str:
        """
        获取注入 Prompt 的规则文本（替代旧的案例罗列）

        Args:
            module_name: 模块名称
            limit: 最多返回条数

        Returns:
            格式化的规则文本，无规则时返回空字符串
        """
        db = SessionLocal()
        try:
            rules = db.query(ScoringRule).filter(
                ScoringRule.module_name == module_name,
                ScoringRule.is_active == True,
            ).order_by(
                desc(ScoringRule.source_case_count),
                desc(ScoringRule.support_rate),
            ).limit(limit).all()

            if not rules:
                return ""

            lines = ["\n## 已验证的评分规则（源自人工修正经验，请严格遵守）"]
            for r in rules:
                deviation_text = ""
                if r.avg_ai_deviation and float(r.avg_ai_deviation) != 0:
                    direction = "偏高" if float(r.avg_ai_deviation) > 0 else "偏低"
                    deviation_text = f"（历史AI{direction}{abs(float(r.avg_ai_deviation)):.1f}分，{r.source_case_count}条修正验证）"
                lines.append(
                    f"- [{r.module_name}] {r.rule_text} → {r.score_directive} {deviation_text}"
                )

            return "\n".join(lines)

        finally:
            db.close()


# 模块级便捷函数
_compiler = RuleCompiler()


def get_compiled_rules_text(module_name: str, limit: int = 5) -> str:
    """便捷函数：获取编译规则文本"""
    return _compiler.get_rules_for_prompt(module_name, limit)


async def run_compilation(module_name: str = None) -> List[ScoringRule]:
    """便捷函数：执行规则编译"""
    return await _compiler.compile_rules(module_name)
