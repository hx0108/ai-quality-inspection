"""
LLM 客户端
通义千问 Qwen-plus（用于AI评分和分析）
"""
import asyncio
import json
import re
import time as _time
import threading
import httpx
from collections import defaultdict
from functools import wraps
from typing import List, Dict, Any, Optional
from config import settings
from core.logger import get_logger

logger = get_logger("llm")


# ============== 健壮的 JSON 提取 ==============

def _extract_json_array(content: str):
    """
    从 LLM 响应中健壮地提取 JSON 数组。

    处理的常见格式:
    1. 纯 JSON 数组: [...]
    2. markdown 代码块: ```json [...] ```
    3. 前后有文字: "以下是评分结果:\n[...]\n以上是评分"
    4. 带尾逗号: [{...},]
    5. 多行带注释的 JSON
    """
    if not content or not content.strip():
        return None

    text = content.strip()

    # 预处理：修复AI在中文文本中误用英文双引号导致的JSON损坏
    # 模式: 中文/数字/括号 + " + 中文/数字/空格 → 转义为 \"
    text = re.sub(r'([\u4e00-\u9fff\uff08\uff09\u3001\uff0c0-9])"([\u4e00-\u9fff\uff08\uff09\u3001\uff0c0-9\s])',
                  r'\1\\"\2', text)
    text = re.sub(r'([\u4e00-\u9fff\uff0c\uff1b])"(\s*[0-9\u4e00-\u9fff])',
                  r'\1\\"\2', text)

    # 策略1: 尝试直接解析（最常见的理想情况）
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # 策略2: 去掉 markdown 代码块包裹后再解析
    for pattern in [r'```json\s*', r'```\s*']:
        if pattern.startswith('```'):
            match = re.search(r'```(?:json)?\s*\n?(.*?)```', text, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group(1).strip())
                    if isinstance(result, list):
                        return result
                except (json.JSONDecodeError, ValueError):
                    # 继续尝试修复
                    fixed = _try_fix_json(match.group(1).strip())
                    if fixed is not None:
                        return fixed

    # 策略3: 用正则找第一个完整的 JSON 数组 [ ... ]
    # 从外向内匹配，找最长的合法数组
    bracket_depth = 0
    start_idx = None
    for i, ch in enumerate(text):
        if ch == '[':
            if bracket_depth == 0:
                start_idx = i
            bracket_depth += 1
        elif ch == ']':
            bracket_depth -= 1
            if bracket_depth == 0 and start_idx is not None:
                candidate = text[start_idx:i + 1]
                try:
                    result = json.loads(candidate)
                    if isinstance(result, list):
                        return result
                except (json.JSONDecodeError, ValueError):
                    # 尝试修复常见问题
                    fixed = _try_fix_json(candidate)
                    if fixed is not None:
                        return fixed

    # 策略4: 最后的尝试 - 找所有 [ 到 ] 的子串
    matches = re.findall(r'\[[\s\S]*?\]', text)
    for m in reversed(matches):  # 从后往前，通常最后的更完整
        if len(m) > 10:  # 过滤掉太短的匹配
            try:
                result = json.loads(m)
                if isinstance(result, list):
                    return result
            except (json.JSONDecodeError, ValueError):
                fixed = _try_fix_json(m)
                if fixed is not None:
                    return fixed

    return None


def _try_fix_json(text: str):
    """尝试修复常见的 JSON 格式问题"""
    if not text:
        return None

    # 修复1: 去掉尾逗号 (trailing comma)
    fixed = re.sub(r',\s*([}\]])', r'\1', text)
    try:
        result = json.loads(fixed)
        if isinstance(result, list):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # 修复2: 去掉单行注释 // ...
    fixed = re.sub(r'//[^\n]*', '', text)
    try:
        result = json.loads(fixed)
        if isinstance(result, list):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # 修复3: 去掉多余转义（LLM 有时输出 \_ 等无效转义）
    fixed = re.sub(r'\\([^"\\/bfnrtu])', r'\1', text)
    try:
        result = json.loads(fixed)
        if isinstance(result, list):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # 修复4: 组合修复
    fixed = re.sub(r',\s*([}\]])', r'\1', text)
    fixed = re.sub(r'//[^\n]*', '', fixed)
    fixed = re.sub(r'\\([^"\\/bfnrtu])', r'\1', fixed)
    try:
        result = json.loads(fixed)
        if isinstance(result, list):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # 修复5: 尝试补全被截断的JSON（AI响应被max_tokens截断）
    # 找到最后一个完整的 } 然后关闭数组
    last_brace = fixed.rfind('}')
    if last_brace > 0:
        candidate = fixed[:last_brace + 1] + ']'
        # 去掉可能的尾逗号
        candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
        try:
            result = json.loads(candidate)
            if isinstance(result, list):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

    return None


# ============== 熔断器 + 统一重试 ==============

class CircuitBreaker:
    """简单熔断器：连续失败 N 次后断开，一段时间后半开"""
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self._failure_count = defaultdict(int)
        self._last_failure = defaultdict(float)
        self._state = defaultdict(lambda: "closed")
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout

    def is_open(self, key: str) -> bool:
        if self._state[key] == "open":
            if _time.time() - self._last_failure[key] > self._recovery_timeout:
                self._state[key] = "half_open"
                return False
            return True
        return False

    def record_success(self, key: str):
        self._failure_count[key] = 0
        self._state[key] = "closed"

    def record_failure(self, key: str):
        self._failure_count[key] += 1
        self._last_failure[key] = _time.time()
        if self._failure_count[key] >= self._failure_threshold:
            self._state[key] = "open"


_qwen_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=120)
_deepseek_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=180)


def with_retry(max_retries=2, base_delay=2, breaker=None, breaker_key=None):
    """LLM 调用统一重试装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = breaker_key or func.__name__
            if breaker and breaker.is_open(key):
                raise Exception(f"熔断器已断开: {key}，请稍后重试")
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    result = await func(*args, **kwargs)
                    if breaker:
                        breaker.record_success(key)
                    return result
                except Exception as e:
                    last_error = e
                    if breaker:
                        breaker.record_failure(key)
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"{func.__name__} 第{attempt+1}次失败，{delay}秒后重试: {e}")
                        await asyncio.sleep(delay)
            raise last_error
        return wrapper
    return decorator


# ============== LLM 用量日志记录（Phase 5） ==============

def _log_llm_usage(model_name: str, call_type: str, result_json: dict, duration_ms: int,
                   task_id: str = None, success: bool = True):
    """后台线程写入LLM用量日志（非阻塞）"""
    usage = result_json.get("usage", {})
    # DeepSeek 细分解析：input_tokens_detail = {cache_read_tokens, cache_miss_tokens}
    input_detail = usage.get("input_tokens_detail") or {}
    cache_hit = input_detail.get("cache_read_tokens", 0) if isinstance(input_detail, dict) else 0
    cache_miss = input_detail.get("cache_miss_tokens", 0) if isinstance(input_detail, dict) else 0
    threading.Thread(
        target=_write_usage_log,
        args=(model_name, call_type, usage, duration_ms, task_id, success, cache_hit, cache_miss),
        daemon=True
    ).start()


def _write_usage_log(model_name, call_type, usage, duration_ms, task_id, success, cache_hit=0, cache_miss=0):
    from database import SessionLocal
    from models.models import LlmUsageLog
    import time as _t
    for _attempt in range(3):
        db = SessionLocal()
        try:
            log = LlmUsageLog(
                model_name=model_name,
                call_type=call_type,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                input_cache_hit_tokens=cache_hit,
                input_cache_miss_tokens=cache_miss,
                duration_ms=duration_ms,
                task_id=task_id,
                success=success
            )
            db.add(log)
            db.commit()
            return
        except Exception as e:
            if _attempt < 2:
                _t.sleep(0.5 * (_attempt + 1))
            else:
                logger.error(f"写入用量日志失败(重试3次): {e}")
        finally:
            db.close()


# ============== 评分纠偏案例缓存（Phase 6 数据飞轮） ==============

_correction_cache = {"data": None, "updated_at": 0}
_CORRECTION_CACHE_TTL = 3600  # 1小时缓存


def _get_correction_examples(module_name: str = None, limit: int = 5) -> str:
    """
    获取评分纠偏参考（优先使用编译规则，退化使用案例）

    技能编译（Skill Compilation）:
    1. 优先从 scoring_rules 查询编译后的抽象规则
    2. 无规则时退化使用旧案例罗列
    """
    # 优先使用编译后的规则
    try:
        from core.rule_compiler import get_compiled_rules_text
        rules_text = get_compiled_rules_text(module_name or "", limit)
        if rules_text:
            return rules_text
    except Exception as e:
        logger.debug(f"编译规则查询失败，退化使用案例: {e}")

    # 退化：使用旧案例罗列逻辑
    now = _time.time()
    if _correction_cache["data"] is None or (now - _correction_cache["updated_at"]) > _CORRECTION_CACHE_TTL:
        from database import SessionLocal
        from models.models import ScoringResult
        db = SessionLocal()
        try:
            edited = db.query(ScoringResult).filter(
                ScoringResult.is_edited == True,
                ScoringResult.original_score != None,
                ScoringResult.edit_reason != None,
            ).order_by(ScoringResult.edited_at.desc()).limit(50).all()

            examples = []
            for r in edited:
                delta = float(r.original_score) - float(r.score)
                direction = "偏高" if delta > 0 else "偏低"
                examples.append({
                    "module": r.module_name,
                    "item": r.item_name or "",
                    "ai_score": float(r.original_score),
                    "human_score": float(r.score),
                    "reason": r.edit_reason,
                    "direction": direction,
                })
            _correction_cache["data"] = examples
            _correction_cache["updated_at"] = now
        except Exception as e:
            logger.error(f"加载纠偏案例失败: {e}")
        finally:
            db.close()

    all_examples = _correction_cache["data"] or []
    if not all_examples:
        return ""

    if module_name:
        matched = [e for e in all_examples if e["module"] == module_name]
        if not matched:
            matched = all_examples[:limit]
    else:
        matched = all_examples[:limit]

    if not matched:
        return ""

    lines = ["\n## 参考案例（人工修正记录，请参考调整评分策略）"]
    for e in matched[:limit]:
        lines.append(
            f"- {e['module']}|{e['item'][:20]}: AI给{e['ai_score']}分→人工修正{e['human_score']}分"
            f"(原{e['direction']},原因:{e['reason']})"
        )
    return "\n".join(lines)


class QwenClient:
    """通义千问客户端（用于AI评分和分析）"""

    # 全局共享连接池，避免每次请求都新建TCP连接+TLS握手
    _shared_client: httpx.AsyncClient = None
    _lock = asyncio.Lock()  # 线程安全锁

    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.base_url = settings.DASHSCOPE_BASE_URL
        self.model = "qwen-plus"

    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        """获取或创建全局共享的 httpx 客户端（连接池复用，双重检查锁定）"""
        if cls._shared_client is not None and not cls._shared_client.is_closed:
            return cls._shared_client
        async with cls._lock:
            if cls._shared_client is not None and not cls._shared_client.is_closed:
                return cls._shared_client
            cls._shared_client = httpx.AsyncClient(
                timeout=httpx.Timeout(180.0, connect=10.0),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=4)
            )
            return cls._shared_client

    @classmethod
    def reset_client(cls):
        """关闭并重置共享客户端（在后台线程新 event loop 中使用前调用）"""
        if cls._shared_client is not None and not cls._shared_client.is_closed:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(cls._shared_client.aclose())
                else:
                    loop.run_until_complete(cls._shared_client.aclose())
            except Exception:
                pass
        cls._shared_client = None

    async def score_item(
        self,
        module_name: str,
        item_name: str,
        check_standard: str,
        check_method: str,
        scoring_rule: str,
        issues: List[Dict[str, Any]],
        is_skipped: bool = False
    ) -> Dict[str, Any]:
        """
        对单个检查项进行AI评分

        Args:
            module_name: 模块名称
            item_name: 检查项名称
            check_standard: 检查标准
            check_method: 检查方法
            scoring_rule: 评价方法/评分规则
            issues: 问题列表，每个问题包含 description, severity, location
            is_skipped: 是否跳过

        Returns:
            评分结果：score (0-5), scoring_basis, improvement_suggestion
        """
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY 未配置")

        # 如果跳过，直接返回满分
        if is_skipped:
            return {
                "score": 5,
                "scoring_basis": "该检查项被跳过，自动给予满分",
                "improvement_suggestion": ""
            }

        # 构建问题描述
        issues_text = ""
        if issues:
            issues_text = "\n【发现的问题】\n"
            for i, issue in enumerate(issues, 1):
                issues_text += f"{i}. 问题描述：{issue.get('description', '无')}\n"
                issues_text += f"   严重程度：{issue.get('severity', '一般')}\n"
                if issue.get('location'):
                    issues_text += f"   问题位置：{issue.get('location')}\n"
        else:
            issues_text = "\n【发现的问题】\n无问题发现，检查符合要求。"

        # 构建评分 Prompt
        prompt = f"""你是一名专业的物业品质检查评分专家。请根据以下信息对检查项进行AI评分。

【模块名称】{module_name}

【检查项信息】
- 检查点：{item_name}
- 检查标准：{check_standard}
- 检查方法：{check_method}
- 评价方法/评分规则：{scoring_rule}
{issues_text}

【评分要求】
1. 严格按照"评价方法/评分规则"进行评分
2. 评分范围：0-5分（可以是小数，如3.5分）
3. 无问题项应给予满分5分
4. 有问题的项应根据问题严重程度和评分规则扣分
5. 严重问题扣分较多，轻微问题扣分较少

【输出格式】（必须是合法的JSON）
```json
{{
    "score": <0-5的分数>,
    "scoring_basis": "<评分依据，说明为什么给这个分数>",
    "improvement_suggestion": "<改进建议，针对问题提出具体整改建议，无问题时填'符合要求'>"
}}
```

请直接输出JSON，不要有其他说明文字。"""

        try:
            client = await self.get_client()
            start = _time.time()
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一名专业的物业品质检查评分专家。你必须严格按照评分规则进行评分，输出必须是合法的JSON格式。"
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1
                }
            )

            if response.status_code != 200:
                raise Exception(f"API调用失败: {response.status_code} - {response.text}")

            result = response.json()
            duration = int((_time.time() - start) * 1000)
            _log_llm_usage(self.model, "scoring", result, duration)
            content = result["choices"][0]["message"]["content"]

            # 解析 JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            score_result = json.loads(content.strip())

            # 验证分数范围
            score = float(score_result.get("score", 5))
            score = max(0, min(5, score))
            score_result["score"] = score

            return score_result

        except json.JSONDecodeError as e:
            # JSON解析失败，根据是否有问题返回默认分数
            if issues:
                return {
                    "score": 3.0,
                    "scoring_basis": "AI评分解析失败，根据存在问题给予中等偏下分数",
                    "improvement_suggestion": "建议整改发现的问题"
                }
            else:
                return {
                    "score": 5.0,
                    "scoring_basis": "AI评分解析失败，无问题发现，给予满分",
                    "improvement_suggestion": "符合要求"
                }
        except Exception as e:
            raise Exception(f"AI评分失败: {str(e)}")

    async def score_module(
        self,
        module_name: str,
        items: List[Dict[str, Any]],
        max_retries: int = 2,
        memory_context: str = "",
        standard_type: str = "diecheng",
    ) -> List[Dict[str, Any]]:
        """
        批量评分一个模块的所有检查项（一次API调用）
        只发送有问题的检查项给AI，合格项不进入prompt

        Args:
            module_name: 模块名称
            items: 检查项列表（仅包含有问题/跳过的项）
            max_retries: 最大重试次数
            memory_context: 记忆上下文（短记忆+长记忆），用于注入到Prompt
            standard_type: 检查标准（diecheng/feidiecheng 走0-5分制；lizhi 走各项max_score分制）

        Returns:
            评分结果列表
        """
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY 未配置")

        # 过滤掉无需AI评分的项（合格项不应该到这里，但做防御性处理）
        problem_items = [item for item in items if item.get("issues") or item.get("is_skipped")]

        if not problem_items:
            logger.debug(f"{module_name}: 无需AI评分的项")
            return []

        total_items = len(problem_items)
        logger.info(f"批量评分开始: {module_name} 模块（{standard_type}），共 {total_items} 项需AI评分")

        # 分批处理：超过 8 个检查项时自动分批，避免单次 API 调用超时
        BATCH_SIZE = 8
        if total_items > BATCH_SIZE:
            logger.info(f"{module_name}: {total_items}项超过单批上限{BATCH_SIZE}，将分 {(total_items + BATCH_SIZE - 1) // BATCH_SIZE} 批评分")
            all_results = []
            for batch_start in range(0, total_items, BATCH_SIZE):
                batch = problem_items[batch_start:batch_start + BATCH_SIZE]
                batch_num = batch_start // BATCH_SIZE + 1
                logger.info(f"{module_name}: 评分第 {batch_num} 批 ({len(batch)}项)")
                batch_results = await self._score_batch(module_name, batch, max_retries, memory_context, standard_type)
                all_results.extend(batch_results)
            return all_results

        return await self._score_batch(module_name, problem_items, max_retries, memory_context, standard_type)

    @staticmethod
    def _match_ai_results(score_results: list, problem_items: List[Dict[str, Any]],
                          module_name: str) -> List[Dict[str, Any]]:
        """
        将AI返回的评分结果匹配回原始检查项。
        多策略匹配：精确item_id → 去空格匹配 → 序号映射 → item_name匹配。
        匹配成功后注入原始项的 weight/check_standard 等数据。
        """
        import re as _re
        item_id_to_original = {item.get("item_id"): item for item in problem_items}
        # 去空格版映射：AI可能返回 "设施 -001" 而非 "设施-001"
        stripped_to_id = {_re.sub(r'\s+', '', k): k for k in item_id_to_original}
        number_to_item_id = {i: item.get("item_id") for i, item in enumerate(problem_items, 1)}
        matched_ids = set()
        results = []

        for score_item in score_results:
            score = float(score_item.get("score", 5))

            ai_item_id = score_item.get("item_id")
            original = None

            # 策略1: 精确 item_id 匹配
            if ai_item_id and ai_item_id in item_id_to_original and ai_item_id not in matched_ids:
                original = item_id_to_original[ai_item_id]

            # 策略2: 去空格匹配（AI返回 "设施 -001" 而非 "设施-001"）
            if not original and ai_item_id:
                ai_stripped = _re.sub(r'\s+', '', str(ai_item_id))
                real_id = stripped_to_id.get(ai_stripped)
                if real_id and real_id not in matched_ids:
                    original = item_id_to_original[real_id]
                    logger.debug(f"去空格匹配: '{ai_item_id}' → '{real_id}'")

            # 策略3: AI返回了序号而非item_id (如 "1" 而非 "设施-001")
            if not original and ai_item_id:
                try:
                    num = int(str(ai_item_id).strip())
                    mapped_id = number_to_item_id.get(num)
                    if mapped_id and mapped_id not in matched_ids:
                        original = item_id_to_original[mapped_id]
                        logger.debug(f"序号映射: '{ai_item_id}' → '{mapped_id}'")
                except (ValueError, TypeError):
                    pass

            # 策略4: 通过 item_name 匹配
            if not original:
                ai_name = score_item.get("item_name", "")
                if ai_name:
                    for oid, oitem in item_id_to_original.items():
                        if oid not in matched_ids and oitem.get("item_name") == ai_name:
                            original = oitem
                            break

            # 蝶城/非蝶城未提供 max_score，默认仍按 0-5 分校验；
            # 砺质检查项会携带各自的 max_score，不能再被统一截断到 5 分。
            max_score = float(original.get("max_score", 5)) if original else 5.0
            score = max(0.0, min(max_score, score))

            entry = {
                "score": score,
                "scoring_basis": score_item.get("scoring_basis", ""),
                "improvement_suggestion": score_item.get("improvement_suggestion", "")
            }

            if original:
                entry["item_id"] = original["item_id"]
                entry["item_name"] = original["item_name"]
                entry["_weight"] = original.get("weight", 0.01)
                entry["_check_standard"] = original.get("check_standard", "")
                entry["_check_method"] = original.get("check_method", "")
                entry["_scoring_rule"] = original.get("scoring_rule", "")
                matched_ids.add(original["item_id"])
            else:
                logger.warning(f"AI返回的item_id '{ai_item_id}' 无法匹配原始检查项, module={module_name}")
                entry["item_id"] = ai_item_id
                entry["item_name"] = score_item.get("item_name", "")

            results.append(entry)

        unmatched = len(score_results) - len(matched_ids)
        if unmatched:
            logger.warning(f"{module_name}: {unmatched}/{len(score_results)}项匹配失败")
        return results

    async def _score_batch(self, module_name: str, problem_items: List[Dict[str, Any]],
                           max_retries: int = 2, memory_context: str = "",
                           standard_type: str = "diecheng") -> List[Dict[str, Any]]:
        """单批评分（内部方法）"""

        # 封顶制（内置砺质 + point_cap 类自定义标准）走独立评分函数，与蝶城完全隔离
        from core import standards as _stds
        if _stds.get_scoring_model(standard_type) == "point_cap":
            return await self._score_batch_lizhi(module_name, problem_items, max_retries, memory_context)

        is_lizhi = (standard_type == "lizhi")

        # 构建检查项列表文本（精简版，只含关键信息）
        items_text = ""
        for i, item in enumerate(problem_items, 1):
            item_id = item.get("item_id", f"item-{i}")
            item_name = item.get("item_name", "")
            check_standard = item.get("check_standard", "")
            scoring_rule = item.get("scoring_rule", "完全符合5分")
            issues = item.get("issues", [])
            is_skipped = item.get("is_skipped", False)
            max_score = item.get("max_score", 5)

            # 构建问题描述
            if is_skipped:
                issues_text = "跳过"
            elif issues:
                parts = []
                for j, issue in enumerate(issues, 1):
                    part = f"{j}. {issue.get('description', '无描述')}"
                    if issue.get('severity'):
                        part += f"（{issue.get('severity')}）"
                    parts.append(part)
                issues_text = "；".join(parts)
            else:
                issues_text = "无"

            if is_lizhi:
                items_text += f"\n{i}. [{item_id}] {item_name} | 满分:{max_score} | 评分规则:{scoring_rule[:300]} | 问题:{issues_text}"
            else:
                items_text += f"\n{i}. [{item_id}] {item_name} | 标准:{check_standard[:80]} | 评分规则:{scoring_rule[:200]} | 问题:{issues_text}"

        # 完整 Prompt（含纠偏案例+记忆上下文）
        correction_text = _get_correction_examples(module_name)

        SYSTEM_PROMPT = """你是物业品质检查评分专家，负责对物业内审检查项进行 AI 评分。

【专业背景】
你精通物业管理行业规范，涵盖：客户服务、安全管理、EHS管理、环境管理、机电运维、设施维护、综合管理、财务管理八大模块。
你了解物业现场检查的标准方法，能够根据问题描述准确判断扣分幅度。

【评分体系】
- 5分：完全符合标准，无任何瑕疵
- 4分：基本符合标准，有细微不足（扣0.5-1分）
- 3分：部分符合标准，存在明显问题需改进（扣1.5-2分）
- 2分：较严重不符合标准，存在系统性缺陷（扣2.5-3分）
- 1分：严重不符合标准，违反标准强制条款或存在安全隐患（扣3-4分）
- 0分：完全不符合，或触犯禁止项（扣4-5分）

【扣分原则】
1. 评分以"评分规则"字段描述的评分办法为主要依据
2. 问题严重程度：严重 > 一般 > 轻微
3. 问题数量：同一检查项问题越多，扣分越多（最多叠加2分）
4. 问题覆盖面：问题涉及范围越广、影响人数越多，扣分越多
5. 整改难度：短期内难以整改的系统性问题可酌情多扣0.5-1分

【输出要求】
- 每项必须输出 item_id、score、scoring_basis、improvement_suggestion、confidence 五个字段
- scoring_basis 必须详细说明扣分理由：先引用评分规则原文，再引用具体问题描述，然后推导扣分和最终得分
- improvement_suggestion 必须具体可执行，不能仅重复"符合要求"
- confidence 为你对本次评分的置信度(0-1)，评估依据：
  · 0.9-1.0：问题描述充分，场景典型，评分标准明确
  · 0.7-0.9：描述基本充分，有轻微模糊因素
  · 0.5-0.7：描述不完整或场景较罕见，评分有一定困难
  · <0.5：信息严重不足或场景从未见过，评分仅作参考

【异常输入识别】
如果问题描述明显与检查内容无关（如"你好"、"测试"、"我试试"、无意义文字等随意填写的内容），必须：
1. score 设为 3（问题描述无效，无法判断实际情况，给中等分数待人工复核）
2. confidence 设为 0.3 以下
3. scoring_basis 中明确标注「问题描述与检查项无相关性，疑似随意填写，无法进行有效评分，建议人工复核」
4. improvement_suggestion 设为「建议检查人员重新填写有效的问题描述」
- scoring_basis 和 improvement_suggestion 中引用中文文字时，必须使用中文引号「」（绝对不能使用英文双引号 " ，否则会破坏JSON格式）
- JSON 必须合法，不要输出 ```json 包装"""

        # 8条 Few-Shot 示例（覆盖8大模块常见问题类型）
        FEW_SHOT_EXAMPLES = """
【评分示例参考】（以下示例仅供参考格式和思路，实际评分必须根据具体检查项的评分规则独立判断）

示例1【客户服务】
检查标准：管家每人每周至少与10位客户进行面对面访谈，并将访谈中获取的有用客户信息在客服工作台系统内进行记录、更新与维护
评分规则：达到要求评5分，每少一户扣1分，每少一个有用信息未在客服工作台记录扣1分
问题：催缴工单录入内容缺失；网格F催缴记录都是系统新增，没有手动更新
评分参考：3分
参考理由：问题涉及两个网格催缴记录缺失（每项各扣约1分），扣分约2分，得3分

示例2【安全管理】
检查标准：设备房、消防主机报警，应通知巡逻岗前往现场查看，白天设备房报警需通知设备责任人到场。处理完毕后将设备复位，并将处理情况记录在《指挥中心工作记录表》上
评分规则：有处理记录，评5分；无处理记录，评0分；记录不完善的，扣2分；其他问题，每项扣1分
问题：按下B19栋指压报警器指挥中心未通知人员到场核实（严重）
评分参考：0分
参考理由：消防报警是强制要求，未到场核实属严重违规，直接判定0分

示例3【EHS及风险管理】
检查标准：每年组织全员签订安全生产责任书并存档，提升全员安全生产意识
评分规则：全部合格评5分；员工未签署安全生产责任书每人扣2分；安全生产评价结果未与员工考核挂钩每人扣1分
问题：两人未签署安全生产责任书
评分参考：1分
参考理由：未签署2人，每人扣2分，共扣4分，但最高只扣到0分，故得1分

示例4【环境管理】
检查标准：草坪目视平整，无坑洼积水，杂草率不超过3%，地被植物及花丛边幅修剪整齐，无残花、无杂草
评分规则：完全符合要求，评5分；抽查6处中每2处存在不符降2分（不足2处按2个计）
问题：草坪、地被内杂草较多
评分参考：3分
参考理由：杂草问题属于部分不符，参照"部分符合3分"原则，扣2分，得3分

示例5【机电运维】
检查标准：设备房内应干净整洁、无积尘、设备表面无油污、物品摆放整齐、无杂物，严禁堆放易燃、易爆物品
评分规则：全部符合，评5分；有不符合，每处扣1分
问题：C4负一57号车位后方排水泵控制电箱下面业主堆放纸箱杂物，存在风险
评分参考：4分
参考理由：仅有1处杂物堆放，扣1分，得4分。属于轻微瑕疵但不属于严重违规

示例6【设施维护】
检查标准：外墙面、建筑小品外观完好、整洁。外墙贴面建材无脱落；外玻璃幕墙清洁明亮、无破损
评分规则：全部符合，评5分；有不符合，每处扣1分
问题：A4-A6-43号车位天花漏水墙面脱漆需刷漆翻新；B4幸福驿站门口上方雨棚和东门水景护栏玻璃破损
评分参考：2分
参考理由：两处问题（漏水脱漆+玻璃破损），每处扣1分，叠加后扣约3分，得2分

示例7【综合管理】
检查标准：仓库管理员每月25日前须对仓库库存物资进行一次全面盘点，并填写《库存物资盘点汇总表》
评分规则：完全符合要求，评5分；有盘点记录但无相关人员签字，评3分；无盘点，评0分
问题：1、社文预存物资未建立台账管理；2、安防应急物资仓库防毒面具过期，物资清单未更新
评分参考：0分
参考理由：台账未建立等同于无盘点记录，直接判定0分，属于严重管理缺失

示例8【财务管理】
检查标准：核对系统临停现金收费及移动支付到账是否一致；核对系统计费是否正确
评分规则：完全符合要求，评5分；任一项不符合，得0分
问题：白名单过夜记录38条
评分参考：0分
参考理由：白名单过夜属于计费异常，规则明确"任一项不符合得0分"，直接判定0分"""

        # ===== 砺质标准：覆盖为按各项 max_score 计分的评分体系（不影响蝶城/非蝶城） =====
        if is_lizhi:
            SYSTEM_PROMPT = """你是「砺质行动」物业品质检查评分专家，负责对砺质行动检查项进行 AI 评分。

【检查体系】
砺质行动检查（8月标准）按 5 个模块开展：管家礼韵塑新颜、安防礼韵塑新颜、环境礼韵塑新颜、技术礼韵塑新颜、其他场所5S。
前 4 个模块每个满分 25 分，其他场所5S 只负责扣分。每个检查项有各自的满分（max_score），评分必须严格依据该检查项的「评分规则」字段。

【评分原则】
1. 评分范围为 0 到该检查项的「满分」（max_score），可为小数
2. 严格按「评分规则」字段的计分办法评分：涉及"合格率/千户均投诉率"等按规则线性取值；涉及"无/轻微/严重"档位的按对应档位给分；涉及"每处/每人扣N分"的按数量累加扣分
3. 无问题的检查项应给满分（= max_score）
4. 先引用评分规则原文，再结合问题描述推导扣分与最终得分，写入 scoring_basis

【异常输入识别】
问题描述明显与检查内容无关（随意填写），score 取满分的一半，confidence 低于0.3，并在 scoring_basis 标注「问题描述疑似无效，建议人工复核」。
- scoring_basis 和 improvement_suggestion 中引用中文文字时，必须使用中文引号「」（不能使用英文双引号 "）
- JSON 必须合法，不要输出 ```json 包装"""

            FEW_SHOT_EXAMPLES = """
【评分示例参考】（砺质行动计分，仅供参考思路，实际按各项评分规则独立判断）

示例A【消防通道杂物率，满分20】
评分规则：无杂物堆放得20分；杂物堆放轻微（不影响通行）得10分；严重（影响通行/火灾隐患）得0分；所有楼栋取平均分
问题：抽5栋中3栋楼道有少量纸箱鞋柜（轻微，不影响通行），2栋无杂物
评分参考：14分
参考理由：3栋轻微（各10分）+2栋无杂物（各20分）取平均 = (10×3+20×2)/5 = 14分

示例B【管家响应不及时投诉量，满分5】
评分规则：月千户均投诉率为0得5分；为0.5得0分；其余线性取值
问题：本月千户均投诉率0.1
评分参考：4分
参考理由：0→5分，0.5→0分线性，0.1对应 5×(1-0.1/0.5)=5×0.8=4分

示例C【管家企微回复平均时长，满分10】
评分规则：项目平均值低于20分钟得10分，每多1分钟扣1分
问题：项目平均回复时长24分钟
评分参考：6分
参考理由：超出20分钟4分钟，扣4分，10-4=6分

示例D【电梯轿厢+机房综合，满分15】
评分规则：无问题15分；乘梯体验问题酌情扣；机房未上锁/风扇空调故障/年检过期/五方通话异常每项至少扣5分；所有电梯取平均分
问题：抽3台电梯，1台轿厢空调故障（扣5），其余2台无问题
评分参考：11.7分
参考理由：(15-5 + 15 + 15)/3 = 40/3 ≈ 11.7分"""

        # 自我改进：注入偏差修正指令
        directive_text = ""
        try:
            from core.self_improver import get_scoring_directives_text
            directive_text = get_scoring_directives_text(module_name)
        except Exception as e:
            logger.debug(f"修正指令查询失败: {e}")

        scale_note = (
            "\n【计分说明】本检查采用砺质行动计分：每项评分范围为 0 ~ 该项「满分」（max_score），"
            "严格按各项「评分规则」计分，无问题项给满分。\n"
            if is_lizhi else ""
        )

        user_prompt = f"""对【{module_name}】模块的 {len(problem_items)} 个有问题检查项进行评分。
{scale_note}
{items_text}

{FEW_SHOT_EXAMPLES}

{correction_text}
{memory_context}
{directive_text}

请为以上每个检查项输出评分结果，JSON数组格式：
[
  {{
    "item_id": "检查项ID",
    "score": <分数>,
    "scoring_basis": "<评分依据，说明扣分原因，需引用具体问题描述>",
    "improvement_suggestion": "<针对问题的具体改进建议>",
    "confidence": <置信度0-1>
  }}
]"""

        # 带重试的API调用
        last_error = None
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    import asyncio as _asyncio
                    delay = 2 ** attempt  # 指数退避：2s, 4s
                    logger.warning(f"第 {attempt + 1} 次重试 {module_name}，等待 {delay}s...")
                    await _asyncio.sleep(delay)

                logger.info(f"调用通义千问 API (尝试 {attempt + 1}/{max_retries})...")

                # Prompt管理器：优先从DB读取，无记录则使用默认
                # 砺质标准不读DB（DB中scoring_system为蝶城0-5分制定制），直接用内置砺质Prompt
                _system_prompt = SYSTEM_PROMPT
                if not is_lizhi:
                    try:
                        from core.prompt_manager import prompt_manager
                        _system_prompt = prompt_manager.get_prompt("scoring_system", SYSTEM_PROMPT)
                    except Exception:
                        pass

                client = httpx.AsyncClient(
                    timeout=httpx.Timeout(120.0, connect=10.0),
                    limits=httpx.Limits(max_connections=5, max_keepalive_connections=2)
                )
                start = _time.time()
                try:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": _system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            "temperature": 0.1
                        }
                    )
                finally:
                    await client.aclose()

                if response.status_code == 429:
                    logger.warning(f"API限流，准备重试...")
                    last_error = Exception(f"API限流: {response.status_code}")
                    continue

                if response.status_code != 200:
                    raise Exception(f"API调用失败: {response.status_code} - {response.text}")

                result = response.json()
                duration = int((_time.time() - start) * 1000)
                _log_llm_usage(self.model, "scoring", result, duration, task_id=module_name)
                content = result["choices"][0]["message"]["content"]

                # 健壮的 JSON 提取：处理 LLM 各种输出格式
                score_results = _extract_json_array(content)

                if score_results is None:
                    logger.warning(f"JSON提取失败 (尝试 {attempt + 1}/{max_retries}), 原始响应前500字符: {content[:500]}")
                    raise json.JSONDecodeError("无法从LLM响应中提取有效JSON数组", content, 0)

                # 验证并处理结果 — 多策略匹配AI返回的item_id到原始检查项
                results = self._match_ai_results(score_results, problem_items, module_name)

                logger.info(f"批量评分完成: {module_name}，成功 {len(results)} 项")
                return results

            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(f"JSON解析失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.error(f"★★★ {module_name} 评分最终失败（JSON解析），最近一次LLM原始响应:\n{content[:1000] if 'content' in dir() else '无'}")
                    return self._get_default_scores(problem_items, "AI返回格式解析失败")

            except Exception as e:
                last_error = e
                err_str = str(e)
                exc_type_name = type(e).__name__
                # httpcore/httpx 超时异常的 str() 和 args 都可能为空，必须用类型名
                if not err_str or not err_str.strip():
                    e_args = getattr(e, 'args', None)
                    if e_args and len(e_args) > 0 and e_args[0]:
                        err_str = str(e_args[0]).strip()
                    if not err_str:
                        err_str = f"{exc_type_name}"
                logger.error(f"评分失败 (尝试 {attempt + 1}/{max_retries}): {exc_type_name}: {err_str} | repr={repr(e)}")
                if "429" in err_str or "限流" in err_str or "rate" in err_str.lower():
                    continue  # 限流则重试
                if attempt == max_retries - 1:
                    logger.error(f"★★★ {module_name} 评分最终失败: type={exc_type_name} err={err_str}")
                    return self._get_default_scores(problem_items, err_str)

        # 所有重试失败 → 尝试降级模型（使用独立连接池，避免被主模型阻塞）
        fallback_model = getattr(settings, 'QWEN_FALLBACK_MODEL', 'qwen-turbo')
        if fallback_model and fallback_model != self.model:
            logger.warning(f"{module_name} 主模型 {self.model} 失败，尝试降级模型 {fallback_model}")
            try:
                # 独立的轻量级 client，连接池与主模型隔离，避免被占满的连接阻塞
                fb_client = httpx.AsyncClient(
                    timeout=httpx.Timeout(120.0, connect=10.0),
                    limits=httpx.Limits(max_connections=3, max_keepalive_connections=1)
                )
                try:
                    response = await fb_client.post(
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": fallback_model,
                            "messages": [
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": user_prompt}
                            ],
                            "temperature": 0.1
                        }
                    )
                finally:
                    await fb_client.aclose()
                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"]
                    fallback_results = _extract_json_array(content)
                    if fallback_results is None:
                        logger.warning(f"降级模型JSON提取失败, 原始响应前300字符: {content[:300]}")
                        raise json.JSONDecodeError("降级模型响应无法提取JSON", content, 0)
                    results = self._match_ai_results(fallback_results, problem_items, module_name)
                    for r in results:
                        r["_fallback"] = True
                        r["_fallback_model"] = fallback_model
                    logger.info(f"{module_name} 降级模型 {fallback_model} 成功")
                    return results
                else:
                    logger.warning(f"降级模型返回 {response.status_code}")
            except Exception as fb_err:
                fb_err_str = str(fb_err)
                if not fb_err_str or not fb_err_str.strip():
                    fb_e_args = getattr(fb_err, 'args', None)
                    if fb_e_args and len(fb_e_args) > 0 and fb_e_args[0]:
                        fb_err_str = str(fb_e_args[0]).strip()
                    else:
                        fb_err_str = f"{type(fb_err).__name__}"
                logger.warning(f"降级模型 {fallback_model} 也失败: {fb_err_str}")

        err_str = str(last_error)
        if not err_str or not err_str.strip():
            e_args = getattr(last_error, 'args', None)
            if e_args and len(e_args) > 0 and e_args[0]:
                err_str = str(e_args[0]).strip()
            else:
                err_str = f"{type(last_error).__name__}"
        logger.error(f"{module_name} 所有模型均失败: {err_str}")
        return self._get_default_scores(problem_items, err_str)

    async def _score_batch_lizhi(self, module_name: str, problem_items: List[Dict[str, Any]],
                                  max_retries: int = 2, memory_context: str = "") -> List[Dict[str, Any]]:
        """砺质专用评分：完全独立的 Prompt 体系，不与蝶城共享任何逻辑"""
        import httpx as _httpx, json as _json, time as _time

        # 构建检查项文本（每项标注其满分）
        items_text = ""
        for i, item in enumerate(problem_items, 1):
            item_id = item.get("item_id", f"item-{i}")
            item_name = item.get("item_name", "")
            scoring_rule = item.get("scoring_rule", "")
            max_score = item.get("max_score", 5)
            issues = item.get("issues", [])
            if item.get("is_skipped"):
                issues_text = "跳过"
            elif issues:
                parts = []
                for j, issue in enumerate(issues, 1):
                    part = f"{j}. {issue.get('description', '无描述')}"
                    if issue.get('severity'):
                        part += f"（{issue.get('severity')}）"
                    parts.append(part)
                issues_text = "；".join(parts)
            else:
                issues_text = "无"
            items_text += f"\n{i}. [{item_id}] {item_name}\n   满分：{max_score}\n   评分规则：{scoring_rule[:300]}\n   发现问题：{issues_text}"

        SYSTEM_PROMPT = """你是「砺质行动」物业品质检查 AI 评分专家。你只使用砺质检查标准（8月版），不使用任何其他标准。

【砺质检查体系】
5个模块：管家礼韵塑新颜（25分）、安防礼韵塑新颜（25分）、环境礼韵塑新颜（25分）、技术礼韵塑新颜（25分）、其他场所5S（只扣分）。
每个检查项有各自的满分（max_score）。前4个模块满分各25分，其他场所5S负责扣分。项目总分=4个计分模块之和−其他场所5S扣分（最高100）。

【评分方法】
- 你必须严格按每个检查项的「评分规则」评分，不得套用任何其他评分体系
- 每个检查项的评分范围是 0 到它的「满分」（max_score）
- 无问题项给满分（=max_score）
- 涉及"合格率""千户均投诉率"等百分比/比率：按评分规则中的线性/档位公式计算具体分数
- 涉及"无/轻微/严重"档位：按对应档位分值给分，多个样本取平均
- 涉及"每处/每人扣N分"：按问题数量累加扣分
- 评分可以是小数（如7.5分、11.7分），保留合理精度
- 如果评分规则是"酌情扣分"，根据问题严重程度在0到max_score之间判断

【输出要求】
- 输出严格JSON数组，不含```json```包装
- 每项输出 item_id、score（数值）、scoring_basis（先引用评分规则原文，再根据问题推导具体分数）、improvement_suggestion、confidence（0-1）
- scoring_basis 中必须展示计分推导过程（如"满分20×3栋无杂物+10×2栋轻微=80/5=16分"）
- 中文引号使用「」"""

        FEW_SHOT = """
【砺质评分示例】

示例1：消防通道杂物率，满分20
评分规则：无杂物堆放得20分；轻微存在（不影响通行）得10分；严重存在（影响通行、火灾隐患）得0分；所有楼栋取平均
问题：抽查5栋，1栋无杂物，3栋轻微杂物，1栋严重杂物
评分：{score: 8.0, scoring_basis: "按评分规则：1栋无杂物=20分，3栋轻微=10×3=30分，1栋严重=0分，(20+30+0)/5=10分", improvement_suggestion: "针对严重杂物楼栋，建议限期清理并张贴消防风险提示函", confidence: 0.9}

示例2：垃圾桶整洁，满分10
评分规则：合格率100%得10分；合格率0%得0分；其余线性取值
问题：抽查5个点位，3个合格，2个桶身有污迹
评分：{score: 6.0, scoring_basis: "按评分规则：合格率3/5=60%，线性计算 10×60%=6.0分", improvement_suggestion: "建议加强垃圾桶日常清洗频次", confidence: 0.95}

示例3：管家企微回复平均时长，满分10
评分规则：项目平均值低于20分钟得10分，每多1分钟扣1分
问题：项目平均回复时长24分钟
评分：{score: 6.0, scoring_basis: "按评分规则：24分钟超出20分钟门槛4分钟，每多1分钟扣1分，10-4=6分", improvement_suggestion: "建议优化回复流程，目标控制在20分钟以内", confidence: 0.95}

示例4：电梯困人次数，满分5
评分规则：未发生电梯困人得5分；发生电梯困人不得分
问题：本月发生1次电梯困人
评分：{score: 0.0, scoring_basis: "按评分规则：本月发生1次电梯困人，不得分", improvement_suggestion: "建议立即排查电梯故障原因并安排维保", confidence: 1.0}
"""

        user_prompt = f"""对【{module_name}】模块的 {len(problem_items)} 个检查项进行砺质评分。

{items_text}

{FEW_SHOT}
{memory_context}

请为以上每个检查项输出评分结果，JSON数组格式：
[
  {{
    "item_id": "检查项ID",
    "score": <分数，0到该项max_score>,
    "scoring_basis": "<评分依据，引用评分规则原文并推导具体分数>",
    "improvement_suggestion": "<具体可执行的改进建议>",
    "confidence": <置信度0-1>
  }}
]"""

        last_error = None
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    import asyncio as _asyncio
                    await _asyncio.sleep(2 ** attempt)

                logger.info(f"砺质API评分 (attempt {attempt + 1}/{max_retries})...")
                client = _httpx.AsyncClient(timeout=_httpx.Timeout(120.0, connect=10.0))
                try:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                        json={"model": self.model, "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt}
                        ], "temperature": 0.1}
                    )
                finally:
                    await client.aclose()

                if response.status_code == 429:
                    last_error = Exception("API rate limit")
                    continue
                if response.status_code != 200:
                    raise Exception(f"API error: {response.status_code}")

                result = response.json()
                duration = int((_time.time() - _time.time()) * 1000)
                _log_llm_usage(self.model, "scoring_lizhi", result, 0)
                content = result["choices"][0]["message"]["content"]
                score_results = _extract_json_array(content)
                if score_results is None:
                    raise _json.JSONDecodeError("Invalid JSON array", content, 0)

                results = self._match_ai_results(score_results, problem_items, module_name)
                logger.info(f"砺质评分完成: {module_name} ({len(results)}项)")
                return results

            except _json.JSONDecodeError as e:
                last_error = e
                if attempt == max_retries - 1:
                    return self._get_default_scores(problem_items, "砺质AI返回格式解析失败")
            except Exception as e:
                last_error = e
                if "429" in str(e) or "rate" in str(e).lower():
                    continue
                if attempt == max_retries - 1:
                    return self._get_default_scores(problem_items, str(e))

        return self._get_default_scores(problem_items, str(last_error))

    def _get_default_scores(self, items: List[Dict[str, Any]], error_msg: str = "") -> List[Dict[str, Any]]:
        """生成默认分数（当AI评分失败时）"""
        # 防御：对 error_msg 做全面净化，确保永远不会有空内容
        if error_msg is None:
            error_msg_clean = "API调用失败"
        else:
            error_msg_clean = repr(error_msg)[1:-1]  # 去除引号，获取原始字符串表示
            error_msg_clean = error_msg_clean.strip()
            # 如果净化后为空或只有空白，使用兜底
            if not error_msg_clean:
                error_msg_clean = "API调用失败"
            # 如果太短（可能被截断），补全
            elif len(error_msg_clean) < 3:
                error_msg_clean = f"API异常({error_msg_clean})"
        error_msg = error_msg_clean
        results = []
        for item in items:
            full = item.get("max_score", 5)  # 砺质各项有独立满分；蝶城默认5
            if item.get("is_skipped"):
                score = full
                basis = "跳过项，自动满分"
            elif item.get("issues"):
                score = round(full * 0.6, 1) if full != 5 else 3.0
                basis = f"评分异常({error_msg})，根据存在问题给予中等分数"
            else:
                score = full
                basis = f"评分异常({error_msg})，无问题给予满分"

            results.append({
                "item_id": item.get("item_id"),
                "item_name": item.get("item_name", ""),
                "score": score,
                "scoring_basis": basis,
                "improvement_suggestion": "",
                "_weight": item.get("weight", 0.01),
                "_check_standard": item.get("check_standard", ""),
                "_check_method": item.get("check_method", ""),
                "_scoring_rule": item.get("scoring_rule", "")
            })
        return results

    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        """
        通用对话接口（用于智能问答机器人）

        Args:
            messages: 对话历史 [{"role": "user"/"assistant", "content": "..."}]
            max_retries: 最大重试次数

        Returns:
            {"content": "回答内容"}
        """
        if not self.api_key:
            return {"content": "LLM API未配置，无法回答问题。"}

        last_error = None
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    import asyncio as _asyncio
                    delay = 2 ** attempt
                    await _asyncio.sleep(delay)

                client = await self.get_client()
                start = _time.time()
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.7
                    }
                )

                if response.status_code == 429:
                    last_error = Exception("API限流")
                    continue

                if response.status_code != 200:
                    raise Exception(f"API调用失败: {response.status_code}")

                result = response.json()
                duration = int((_time.time() - start) * 1000)
                _log_llm_usage(self.model, "chat", result, duration)

                content = result["choices"][0]["message"]["content"]
                return {"content": content}

            except Exception as e:
                last_error = e
                logger.error(f"对话失败 (尝试 {attempt + 1}/{max_retries}): {e}")

        return {"content": f"抱歉，无法回答您的问题。错误: {last_error}"}

    async def analyze_module(
        self,
        module_name: str,
        scoring_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析单个模块的检查情况

        Args:
            module_name: 模块名称
            scoring_items: 评分项列表（包含分数和问题）

        Returns:
            分析结果字典
        """
        if not self.api_key:
            return {"error": "DASHSCOPE_API_KEY 未配置"}

        prompt = self._build_analysis_prompt(module_name, scoring_items)

        try:
            client = await self.get_client()
            start = _time.time()
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一名专业的物业品质检查分析专家。请对检查情况进行分析，输出必须是合法的JSON格式。"
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3
                }
            )

            if response.status_code != 200:
                return {"error": f"API调用失败: {response.status_code}"}

            result = response.json()
            duration = int((_time.time() - start) * 1000)
            _log_llm_usage(self.model, "analysis", result, duration)
            content = result["choices"][0]["message"]["content"]

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())

        except json.JSONDecodeError:
            return {
                "overall_evaluation": "分析结果解析失败",
                "main_issues": [],
                "improvement_suggestions": []
            }
        except Exception as e:
            return {"error": str(e)}

    def _build_analysis_prompt(self, module_name: str, items: List[Dict]) -> str:
        """构建分析 Prompt"""
        items_json = json.dumps(items, ensure_ascii=False, indent=2)

        prompt = f"""你是一名专业的物业品质检查分析专家。请对以下模块的检查情况进行分析。

【模块信息】
模块名称：{module_name}
检查项数量：{len(items)}

【检查项评分情况】
{items_json}

【分析要求】
请从以下几个方面进行分析：
1. 模块整体表现评价
2. 主要问题分析
3. 改进建议

【输出格式】
```json
{{
    "overall_evaluation": "<整体表现评价>",
    "main_issues": ["<主要问题1>", "<主要问题2>"],
    "improvement_suggestions": ["<建议1>", "<建议2>"]
}}
```

请直接输出JSON，不要有其他说明文字。"""

        return prompt

    async def analyze_overall(
        self,
        project_name: str,
        module_analyses: List[Dict[str, Any]],
        total_score: float
    ) -> str:
        """
        生成项目综合分析

        Args:
            project_name: 项目名称
            module_analyses: 各模块分析结果
            total_score: 项目总分

        Returns:
            综合分析文本
        """
        if not self.api_key:
            return "综合分析需要配置 DASHSCOPE_API_KEY"

        prompt = f"""你是一名专业的物业品质检查分析专家。请根据各模块的分析结果，生成项目综合检查报告。

【项目信息】
项目名称：{project_name}
总分：{total_score:.2f}分

【各模块分析结果】
{json.dumps(module_analyses, ensure_ascii=False, indent=2)}

【输出要求】
请生成完整的检查报告文本，包含以下内容：

一、检查概况
   - 检查基本信息
   - 总体得分情况

二、各模块检查情况
   - 模块得分排名
   - 各模块详细分析

三、重点问题清单
   - 严重问题（需立即整改）
   - 一般问题（限期整改）

四、改进建议
   - 短期整改措施
   - 长期提升建议

请直接输出报告文本。"""

        try:
            client = await self.get_client()
            start = _time.time()
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3
                }
            )

            if response.status_code != 200:
                return f"分析生成失败: {response.status_code}"

            result = response.json()
            duration = int((_time.time() - start) * 1000)
            _log_llm_usage(self.model, "analysis", result, duration)
            return result["choices"][0]["message"]["content"]

        except Exception as e:
            return f"分析生成失败: {str(e)}"


def _ds_standard_context(standard_type: str) -> dict:
    """DeepSeek 报告/分析 Prompt 的「检查体系背景」按 standard_type 提供。
    蝶城/非蝶城返回既有的八大模块5分制背景；砺质返回5模块+4×25+扣分背景。"""
    # 自定义封顶制标准：按其模块配置生成通用背景
    from core import standards as _stds
    if standard_type != "lizhi" and standard_type.startswith("custom_") and _stds.get_scoring_model(standard_type) == "point_cap":
        mods = _stds.get_modules(standard_type)
        mod_lines = "\n".join(
            f"- {m}（满分{_stds.get_module_max_score(standard_type, m) or 0}）" for m in mods
        )
        return {
            "background": (
                "本检查采用自定义检查标准（封顶计分制），模块与满分：\n" + mod_lines +
                "\n扣分模块只减分。请按此体系输出分析。"
            )
        }
    if standard_type == "lizhi":
        return {
            "background": (
                "本检查采用「砺质行动」检查标准（8月版），围绕5个模块开展：\n"
                "- 管家礼韵塑新颜（满分25）：管家2341抽查、幸福驿站形象展示、响应不及时/服务态度投诉量\n"
                "- 安防礼韵塑新颜（满分25）：消防通道杂物堆放治理、安全岗亭形象展示、消防通道堵塞/服务态度投诉量\n"
                "- 环境礼韵塑新颜（满分25）：垃圾桶整洁、环境岗形象展示、垃圾清运不及时/服务态度投诉量\n"
                "- 技术礼韵塑新颜（满分25）：电梯轿厢与机房、技术岗形象展示、乘梯体验/服务态度投诉量、休闲椅凳焕新、路灯焕新\n"
                "- 其他场所5S（只扣分）：工作场所5S，每发现1处不合格扣3分\n\n"
                "砺质计分：每个检查项有各自满分(max_score)，按各项评分规则评分；"
                "前4个模块各封顶25分，其他场所5S只扣分；项目总分=四个计分模块之和−其他场所5S扣分，满分100。"
            ),
            "scoring_rule": (
                "评分规则说明：检查采用「砺质行动」检查标准（8月版），5个模块（管家礼韵塑新颜、"
                "安防礼韵塑新颜、环境礼韵塑新颜、技术礼韵塑新颜各满分25，其他场所5S只扣分），"
                "项目总分=四个计分模块之和−其他场所5S扣分，满分100。"
            ),
            "system_suffix": (
                "\n\n注意：本次为「砺质行动」检查（5模块、4×25+扣分=100），"
                "分析请基于砺质体系与各项max_score计分，不要套用八大模块5分制。"
            ),
        }
    return {
        "background": (
            "本检查采用物业品质内审检查标准V3.0（标准版/简化版），涵盖8大模块：\n"
            "- 客户服务（15%）：管家服务、客户信息管理、投诉处理、社区文化、便民服务、装修管理等\n"
            "- 安全管理（15%）：人行/车行出入口、门岗管理、消防管理、秩序维护、应急预案等\n"
            "- EHS及风险管理（10%）：职业健康安全、特种作业、防汛防寒、泳池安全、值班管理等\n"
            "- 环境管理（15%）：保洁质量、绿化养护、消杀管理、垃圾清运、垃圾分类等\n"
            "- 机电运维（15%）：供配电、给排水、电梯、消防设施、弱电系统等\n"
            "- 设施维护（15%）：房屋本体、公共设施、装修管理、充电桩、能耗管理等\n"
            "- 综合管理（10%）：品质督导、数字化建设、档案管理、仓库管理、办公区管理等\n"
            "- 财务管理（5%）：收费管控、票据管理、固定资产、公共资源经营等\n\n"
            "评分采用5分制，根据每项权重加权计算模块百分制得分。"
        ),
        "scoring_rule": (
            "评分规则说明：检查采用物业品质内审检查标准V3.0，涵盖8大模块（客户服务15%、安全管理15%、EHS及风险管理10%、环境管理15%、机电运维15%、设施维护15%、综合管理10%、财务管理5%），"
            "各模块检查项采用5分制评分，根据权重加权计算模块百分制得分，再按模块权重汇总项目总分。"
        ),
        "system_suffix": "",
    }


class DeepSeekClient:
    """DeepSeek客户端（用于Agent 3报告生成）"""

    # 全局共享连接池
    _shared_client: httpx.AsyncClient = None
    _lock = asyncio.Lock()  # 线程安全锁

    # 统一系统提示词（模块分析和综合报告共用）
    SYSTEM_PROMPT = """你是一位拥有15年以上大型物业集团品质管理经验的资深专家，现任集团品质审计总监。你具备以下核心专业能力：

【行业知识体系】
- 精通物业品质内审标准体系(V3.0，含标准版及简化版)，深度理解八大模块检查逻辑：
  · 客户服务(15%)：触点管理、投诉闭环率、满意度调查、管家服务标准化
  · 安全管理(15%)：门岗管控、巡逻覆盖、消防设施完好率、应急预案演练、智慧安防系统运维
  · EHS及风险管理(10%)：危险源辨识、合规性评价、职业健康、环境因素识别、事故隐患排查治理双重预防机制
  · 环境管理(15%)：绿化养护标准、保洁作业SOP、垃圾分类执行、四害消杀频次、景观水系维护
  · 机电运维(15%)：设备全生命周期管理(TPM)、预防性维护计划、能耗监测与节能优化、特种设备年检合规
  · 设施维护(15%)：房屋本体维修、公区设施完好率、装修管控、承接查验遗留问题追踪
  · 综合管理(10%)：档案管理规范性、培训体系完整性、供方评估与履约监管、制度执行一致性
  · 财务管理(5%)：收费率、预算执行偏差、公共收益管理透明度、成本管控有效性

【评分机制理解】
采用5分制单项评分：5分完全符合(标杆水准)、4分基本符合(小幅优化空间)、3分部分符合需改进(明显差距)、2分较严重不符合(系统性缺失)、1分严重不符合(底线失守)、0分完全不符合或触犯禁止项(红线违规)。加权汇总为模块百分制得分及项目总分。

【分析框架】
你进行分析时必须遵循以下专业方法论：
1. 根因分析法(RCA)：从"人-机-料-法-环"五个维度追溯问题根因，区分表象问题与系统性问题
2. 风险矩阵：按"发生概率×影响程度"对问题进行风险分级(高/中/低)
3. PDCA闭环：整改建议必须形成"Plan计划→Do执行→Check检查→Act改进"的完整闭环
4. 标杆对标：参照行业头部企业的成熟做法，给出可对标的改进方向

【职业准则】
1. 数据驱动：所有分析和结论必须基于检查数据，不得凭空编造
2. 客观公正：评价用语客观中性，问题定性准确（偶发性 vs 系统性 vs 制度性）
3. 引用原文：列举问题时必须引用原始检查标准和问题描述，确保可追溯
4. 量化呈现：用数据说话（如"扣分率"、"问题密度"、"偏离基准值X%"）
5. 可操作性：整改建议必须明确"谁来做(责任方)"、"做什么(具体动作)"、"何时完成(时间节点)"、"如何验证(验收标准)"
6. 行业术语：使用物业管理行业规范术语（如"触点管理"、"前置服务"、"首问负责制"、"闭环率"等）
7. 公文风格：正式、简洁、逻辑严密的管理报告风格"""

    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.model = getattr(settings, 'DEEPSEEK_REPORT_MODEL', 'deepseek-chat')
        self.fallback_model = getattr(settings, 'DEEPSEEK_FALLBACK_MODEL', 'deepseek-chat')

    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        """获取或创建全局共享的 httpx 客户端（双重检查锁定）"""
        if cls._shared_client is not None and not cls._shared_client.is_closed:
            return cls._shared_client
        async with cls._lock:
            if cls._shared_client is not None and not cls._shared_client.is_closed:
                return cls._shared_client
            cls._shared_client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=10.0),
                limits=httpx.Limits(max_connections=4, max_keepalive_connections=2)
            )
            return cls._shared_client

    @classmethod
    def reset_client(cls):
        """关闭并重置共享客户端（在后台线程新 event loop 中使用前调用）"""
        if cls._shared_client is not None and not cls._shared_client.is_closed:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(cls._shared_client.aclose())
                else:
                    loop.run_until_complete(cls._shared_client.aclose())
            except Exception:
                pass
        cls._shared_client = None

    @with_retry(max_retries=2, base_delay=3, breaker=_deepseek_breaker, breaker_key="generate_report")
    async def generate_report(
        self,
        project_name: str,
        inspection_date: str,
        module_summaries: list,
        total_score: float,
        standard_type: str = "diecheng",
    ) -> str:
        """
        生成完整的检查报告

        Args:
            project_name: 项目名称
            inspection_date: 检查日期
            module_summaries: 各模块摘要列表
            total_score: 项目总分
            standard_type: 检查标准（影响报告中的检查体系描述）

        Returns:
            完整报告文本
        """
        if not self.api_key:
            return "报告生成需要配置 DEEPSEEK_API_KEY"

        prompt = self._build_report_prompt(
            project_name, inspection_date, module_summaries, total_score, standard_type
        )

        try:
            client = await self.get_client()
            start = _time.time()
            std_ctx = _ds_standard_context(standard_type)
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": self.SYSTEM_PROMPT + std_ctx["system_suffix"] + "\n\n当前任务：根据各模块的检查分析结果，生成一份完整的物业内审检查综合报告。\n【新增要求】\n1. 必须包含根因分析章节（从制度/人员/资源/外部协同四个维度）\n2. 必须识别跨模块共性问题并分析责任归属\n3. 整改建议必须明确责任方（项目/阵地/供应商）和完成时间节点\n4. 必须包含检查亮点章节，不得省略"
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 4096
                }
            )

            if response.status_code != 200:
                return f"报告生成失败: {response.status_code} - {response.text}"

            result = response.json()
            duration = int((_time.time() - start) * 1000)
            _log_llm_usage(self.model, "report", result, duration)
            return result["choices"][0]["message"]["content"]

        except Exception as e:
            # 降级模型尝试
            if self.fallback_model and self.fallback_model != self.model:
                logger.warning(f"DeepSeek 主模型失败，尝试降级模型 {self.fallback_model}: {e}")
                try:
                    client = await self.get_client()
                    start = _time.time()
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": self.fallback_model,
                            "messages": [
                                {
                                    "role": "system",
                                    "content": self.SYSTEM_PROMPT + "\n\n当前任务：根据各模块的检查分析结果，生成一份完整的物业内审检查综合报告。"
                                },
                                {"role": "user", "content": prompt}
                            ],
                            "max_tokens": 4096
                        },
                        timeout=60.0
                    )
                    if response.status_code == 200:
                        result = response.json()
                        duration = int((_time.time() - start) * 1000)
                        _log_llm_usage(self.fallback_model, "report_fallback", result, duration)
                        content = result["choices"][0]["message"]["content"]
                        logger.info(f"报告生成降级模型 {self.fallback_model} 成功")
                        return content
                    else:
                        logger.warning(f"降级模型返回 {response.status_code}")
                except Exception as fb_err:
                    logger.warning(f"降级模型 {self.fallback_model} 也失败: {fb_err}")
            return f"报告生成失败: {str(e)}"

    @with_retry(max_retries=2, base_delay=2, breaker=_deepseek_breaker, breaker_key="ds_analyze_module")
    async def analyze_module(
        self,
        module_name: str,
        module_score: float,
        items: list,
        memory_context: str = "",
        standard_type: str = "diecheng",
    ) -> dict:
        """
        分析单个模块的检查情况

        Args:
            module_name: 模块名称
            module_score: 模块得分（百分制/砺质为模块得分）
            items: 检查项列表（包含分数和问题）
            memory_context: 该项目历史记忆上下文（可选，来自长期记忆）
            standard_type: 检查标准（影响检查体系背景描述）

        Returns:
            模块分析结果
        """
        if not self.api_key:
            return {"error": "DEEPSEEK_API_KEY 未配置"}

        std_ctx = _ds_standard_context(standard_type)

        # 历史记忆段落（仅在有记忆时注入，无记忆则保持原行为，零风险）
        memory_section = ""
        if memory_context and memory_context.strip():
            memory_section = f"""

【该项目历史检查记忆】（参考历史模式，识别反复出现的问题和趋势）
{memory_context}

请在分析中结合历史记忆：若发现反复出现的问题（recurring_issue），应在 main_issues 中明确标注"历史重复问题"并强调；若发现改善趋势，也应在评价中体现。
"""

        score_label = "模块得分（满分25）" if standard_type == "lizhi" else "模块得分（百分制）"
        prompt = f"""你是物业品质检查分析专家。请根据以下模块的检查评分数据，对该模块的物业品质管理情况进行专业分析。

【模块信息】
模块名称：{module_name}
{score_label}：{module_score:.2f}分
检查项数量：{len(items)}项{memory_section}

【检查项详情（含评分、权重、检查标准、问题记录）】
{json.dumps(items, ensure_ascii=False, indent=2)}

【检查体系背景】
{std_ctx['background']}

【分析要求】
1. 逐项审视得分情况，重点关注扣分项和问题项
2. 分析扣分项所反映的管理缺陷，识别是偶发性问题还是系统性问题
3. 整体评价应根据得分区间确定分析深度：
   - ≥85分：侧重提炼亮点和优势，简洁概括（150字以内）
   - 70-84分：侧重改进空间和具体不足（200-300字）
   - <70分：侧重问题根因分析和系统性缺陷诊断（400字以上）
4. 整体评价必须引用具体检查项名称和数据，不得笼统描述
5. main_issues 最多输出5条，仅列出扣分最严重的检查项，说明扣分原因及反映的管理缺陷
6. improvement_suggestions 每条建议必须包含：责任方（谁做）+ 具体动作（做什么）+ 操作要点（怎么做）

【输出格式】
请输出JSON格式，不要包含其他文字：
```json
{{
    "overall_evaluation": "<对该模块的整体评价，需引用具体检查项名称和数据，得分<70时应包含根因分析>",
    "main_issues": ["<问题1：检查项名称+扣分原因+反映的管理缺陷>", "<问题2>", "...（最多5条）"],
    "improvement_suggestions": ["<建议1：责任方+具体动作+操作要点>", "<建议2>", "<建议3>"]
}}
```"""

        try:
            client = await self.get_client()
            start = _time.time()
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": self.SYSTEM_PROMPT + std_ctx["system_suffix"] + "\n\n当前任务：对单个模块的检查评分数据进行分析，输出该模块的整体评价、主要问题和改进建议。输出必须是合法的JSON格式。\n【额外要求】\n1. 得分<70分的模块必须包含根因分析，不能仅罗列问题\n2. 改进建议必须包含责任方（谁做）、具体动作（做什么）、操作要点（怎么做）\n3. 分析应区分偶发性问题与系统性问题"
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 2560
                }
            )

            if response.status_code != 200:
                return {"error": f"API调用失败: {response.status_code}"}

            result = response.json()
            duration = int((_time.time() - start) * 1000)
            _log_llm_usage(self.model, "analysis", result, duration)
            content = result["choices"][0]["message"]["content"]

            # 解析JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())

        except json.JSONDecodeError:
            return {
                "overall_evaluation": "分析结果解析失败",
                "main_issues": [],
                "improvement_suggestions": []
            }
        except Exception as e:
            return {"error": str(e)}

    def _build_report_prompt(
        self,
        project_name: str,
        inspection_date: str,
        module_summaries: list,
        total_score: float,
        standard_type: str = "diecheng",
    ) -> str:
        """构建报告生成的Prompt"""

        std_ctx = _ds_standard_context(standard_type)
        # 按得分从低到高排序，便于优先关注低分模块
        sorted_summaries = sorted(module_summaries, key=lambda x: x.get('score', 0))

        summaries_text = ""
        for summary in sorted_summaries:
            summaries_text += f"""
### {summary.get('module_name', '未知模块')}
- 得分：{summary.get('score', 0):.2f}分
- 整体评价：{summary.get('overall_evaluation', '无')}
- 主要问题：{', '.join(summary.get('main_issues', []))}
- 改进建议：{', '.join(summary.get('improvement_suggestions', []))}
"""

        # 等级评定（按业态细分）
        if total_score >= 90:
            grade = "优秀"
        elif total_score >= 80:
            grade = "良好"
        elif total_score >= 70:
            grade = "合格"
        else:
            grade = "待提升"

        prompt = f"""你是物业品质检查分析专家。请根据以下物业品质检查数据，撰写一份专业的物业内审检查综合报告。

【项目信息】
项目名称：{project_name}
检查日期：{inspection_date}
项目总分：{total_score:.2f}分（满分100分）
等级评定：{grade}

{std_ctx['scoring_rule']}

【各模块检查结果摘要】（按得分从低到高排列）
{summaries_text}

【报告结构要求】（Markdown格式）
请按以下章节结构生成报告，每章均需有实质性内容，不得留空：

## 一、检查概况

### 1.1 检查基本信息
用表格列出：项目名称、检查日期、检查标准版本、检查模块数

### 1.2 总体得分情况
- 项目总分及等级评定：{total_score:.2f}分（{grade}）
- 各模块得分汇总表（按得分从高到低排序），包含：模块名称、百分制得分、权重、加权贡献

## 二、各模块检查结果

对每个模块逐一说明（按得分从低到高排列，低分模块重点关注）：
- 模块百分制得分及排名
- 该模块的主要检查发现（引用模块分析中的具体问题描述）
- 该模块需优先关注的重点问题

## 三、跨模块综合分析（重点章节）

### 3.1 根因分析
从以下维度分析问题产生的根本原因：
- 制度流程层面：是否存在制度漏洞或执行流程缺失？
- 人员管理层面：是否存在人员配置不足或培训不到位的问题？
- 资源配置层面：是否存在投入不足或资源配置不合理的情况？
- 外部协同层面：是否存在供应商或外包单位服务质量问题？

### 3.2 跨模块共性问题
识别2-3个在多个模块中同时出现的系统性问题（仅当存在共性时输出，如无共性则说明"各模块问题相对独立"）

### 3.3 责任归属分析
按以下维度归类整改责任：
- 项目层面：项目自身管理问题，由项目驻场经理/项目团队整改
- 阵地层面：需要阵地线条支持或制定统一标准的，由阵地专家负责
- 供应商层面：涉及外包单位服务质量问题，由阵地专家跟进

## 四、重点问题清单与整改建议

### 4.1 重点关注问题
汇总各模块中发现的主要问题（仅列扣分最严重的问题，最多10条），按严重程度排列：
- 严重问题（触犯强制标准/存在安全隐患）：需立即整改
- 一般问题（管理不到位/服务品质不达标）：限期整改

### 4.2 整改行动计划
针对上述重点问题，给出分优先级的整改建议，每条建议必须包含：
- 整改事项：具体描述
- 责任方：项目团队/阵地线条/供应商
- 建议完成时间：即时整改（1周内）/短期整改（1个月内）/持续改进

## 五、检查亮点与优势

总结本次检查中表现较好的方面（引用具体数据和模块），不得省略此章节。

## 六、总结

对本次检查的整体评价，包括：
1. 项目品质管理工作的综合判断（1-2句话）
2. 最需要优先改进的1-2个方面

【写作要求】
1. 所有分析和结论必须基于输入的检查数据，不得凭空编造
2. 引用具体检查项名称和数据，不得笼统描述
3. 整改建议必须具体可执行，明确责任方和时间节点
4. 语言风格：正式、简洁、专业的公文写作风格
5. 直接输出Markdown格式，不要包含```markdown等包装"""

        return prompt

    @with_retry(max_retries=3, base_delay=3, breaker=_deepseek_breaker, breaker_key="compare_reports")
    async def compare_reports(self, comparison_data: dict) -> dict:
        """
        综合对比分析（用于 Agent 4 - 综合分析Agent）

        Args:
            comparison_data: 包含 mode, reports_data, comparison_matrix 等的字典

        Returns:
            结构化分析结果 + Markdown 完整报告
        """
        if not self.api_key:
            return {"error": "DEEPSEEK_API_KEY 未配置", "ai_analysis": "", "executive_summary": ""}

        import json as _json
        mode = comparison_data.get("mode", "cross_project")
        label_a = comparison_data.get("label_a", "对象A")
        label_b = comparison_data.get("label_b", "对象B")
        comparison_matrix = comparison_data.get("comparison_matrix", [])
        summary_a = comparison_data.get("summary_a", {})
        summary_b = comparison_data.get("summary_b", {})
        module_analyses = comparison_data.get("module_analyses", [])

        # 构建对比矩阵文本
        matrix_text = "| 模块名称 | 权重 | {a}得分 | {b}得分 | 差值 | 判定 |\n|---|---|---|---|---|---|\n".format(
            a=label_a, b=label_b
        )
        for m in comparison_matrix:
            diff = m.get("diff", 0)
            if abs(diff) > 1.0:
                judgment = "显著差异"
            elif abs(diff) > 0.2:
                judgment = "轻微差异"
            else:
                judgment = "基本持平"
            matrix_text += f"| {m.get('module_name','')} | {m.get('weight',0)*100:.0f}% | {m.get('score_a',0):.2f} | {m.get('score_b',0):.2f} | {diff:+.2f} | {judgment} |\n"

        # 历史记忆段落（仅在有记忆时注入，零风险）
        memory_context = comparison_data.get("memory_context", "")
        memory_section = ""
        if memory_context and memory_context.strip():
            memory_section = f"\n\n【相关项目的历史检查记忆】（参考历史模式、反复问题和改善趋势，使分析具备纵向视角）\n{memory_context}\n"

        # 模式特定提示
        if mode == "cross_time":
            mode_desc = "跨时段趋势对比"
            extra_req = """3. 趋势研判：对每个模块判断趋势方向(↑改善/↓下滑/→持平)，量化变化幅度，分析变化动因(人员变动/制度调整/设备老化等)
4. 问题追踪：区分"已闭环问题"(说明整改措施有效性)、"新增暴露问题"(说明管理盲区)、"顽固性复发问题"(说明根因未消除)
5. 风险预警：识别连续下滑或长期低分的模块，按"红/橙/黄"三级预警，给出干预建议"""
        elif mode == "all_projects":
            mode_desc = "全项目全局概览"
            extra_req = """3. 排行评级：对所有项目按总分排名，评定等级(A+/A/A-/B+/B/C)，并说明评级依据和与基准的偏离程度
4. 共性问题诊断：识别影响面最广的TOP 5系统性问题，分析是否为集团层面的制度性或资源性短板
5. 标杆做法提取：指出各模块表现最优项目的可复制管理做法，供其他项目学习借鉴"""
        else:
            mode_desc = "跨项目对决对比"
            extra_req = """3. 优劣势诊断：分别指出双方的优势模块和薄弱模块，分析优势成因(管理做法/资源配置/人员能力)和薄弱根因(制度缺失/执行不力/资源不足)
4. 差异化分析：对比共性问题(说明区域性或系统性风险)与独有问题(说明项目个性短板)，给出差异化管理建议
5. 对标改进建议：参照行业标杆做法，为薄弱方提供可落地的提升路径"""

        prompt = f"""请对以下物业品质检查数据进行专业的{mode_desc}分析。

【检查对象概况】
{label_a}：总分 {summary_a.get('total_score', 0):.2f} | 严重问题 {summary_a.get('serious_count', 0)} 项、一般问题 {summary_a.get('general_count', 0)} 项、轻微问题 {summary_a.get('minor_count', 0)} 项
{label_b}：总分 {summary_b.get('total_score', 0):.2f} | 严重问题 {summary_b.get('serious_count', 0)} 项、一般问题 {summary_b.get('general_count', 0)} 项、轻微问题 {summary_b.get('minor_count', 0)} 项

【各模块对比矩阵】
{matrix_text}

【模块分析详情】
{_json.dumps(module_analyses, ensure_ascii=False)[:2000]}{memory_section}

【分析要求】
请按以下框架进行深度分析：
1. 执行摘要(100-150字)：概括核心发现、关键风险和总体判断
2. 得分对比分析：从总分差距切入，聚焦差异最大的2-3个模块进行深度解读
{extra_req}
6. 行动计划(3-5条)：每条包含具体动作、责任方(项目/阵地/集团)、完成时限、验收标准

【输出格式】
直接输出合法JSON（不要markdown代码块），格式如下：
{{"executive_summary":"100-150字概括性摘要，含核心发现和关键风险提示","overall_verdict":"基于数据的专业判断，包含品质水平定位和主要风险提示","score_comparison":{{"winner":"A/B/持平","diff":0.0,"analysis":"从总分差距切入的深度分析，聚焦差异最大的模块及其背后原因"}},"strengths_a":["{{label_a}}的优势模块，引用具体模块名和得分，分析优势成因"],"strengths_b":["{{label_b}}的优势模块，引用具体模块名和得分，分析优势成因"],"weaknesses_a":["{{label_a}}的薄弱环节，引用具体数据，从人/机/料/法/环维度分析根因"],"weaknesses_b":["{{label_b}}的薄弱环节，引用具体数据，从人/机/料/法/环维度分析根因"],"key_differences":["关键差异点，需说明差异背后的管理原因而非仅罗列数据"],"common_issues":["共性问题，分析是否为系统性/制度性问题，影响范围评估"],"risk_warnings":["风险预警项，按红/橙/黄分级，说明风险场景和可能的后果"],"action_items":[{{"action":"具体整改动作，描述要做什么","responsible":"责任方(如：项目经理/品质督导/集团品质部/供应商)","deadline":"完成时限","acceptance":"验收标准和验证方式"}}],"final_conclusion":"50字以内的结论性判断，包含品质定位和核心建议方向"}}"""

        last_error = None
        for attempt in range(3):
            try:
                if attempt > 0:
                    import asyncio as _asyncio
                    await _asyncio.sleep(3)
                    logger.warning(f"重试第 {attempt+1} 次...")

                client = await self.get_client()
                payload = {
                    "model": getattr(settings, 'DEEPSEEK_REPORT_MODEL', 'deepseek-chat'),
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一位拥有15年以上大型物业集团品质管理经验的资深专家。你的分析必须体现以下专业水准：\n1. 根因思维：不只罗列数据差异，更要从「人-机-料-法-环」五维度追溯根因\n2. 风险意识：识别潜在的品质风险点，按发生概率和影响程度分级预警\n3. 行业对标：参照行业头部企业的成熟做法给出改进建议\n4. 落地导向：每条建议都必须明确责任方、时间节点和验收标准\n5. 直接输出合法JSON，不要任何其他文字。"
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 4096,
                    "response_format": {"type": "json_object"}
                }
                start = _time.time()
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )

                if response.status_code != 200:
                    raise Exception(f"API调用失败: {response.status_code} - {response.text[:200]}")

                result = response.json()
                duration = int((_time.time() - start) * 1000)
                _log_llm_usage(getattr(settings, 'DEEPSEEK_REPORT_MODEL', 'deepseek-chat'), "analysis", result, duration)
                content = result["choices"][0]["message"]["content"]
                finish_reason = result["choices"][0].get("finish_reason", "")

                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                content = content.strip()

                # 如果响应被截断，尝试修复 JSON
                if finish_reason == "length" or not content.rstrip().endswith("}"):
                    logger.warning(f"响应被截断(finish_reason={finish_reason})，尝试修复JSON...")
                    last_brace = content.rfind("}")
                    if last_brace > 0:
                        content = content[:last_brace + 1]
                        opens = content.count("{") - content.count("}")
                        brackets = content.count("[") - content.count("]")
                        content += "]" * max(0, brackets) + "}" * max(0, opens)

                parsed = _json.loads(content)
                logger.info(f"综合分析完成")
                return parsed

            except _json.JSONDecodeError as e:
                last_error = e
                logger.warning(f"JSON解析失败 (尝试 {attempt+1}/3): {e}")
            except Exception as e:
                last_error = e
                logger.error(f"分析失败 (尝试 {attempt+1}/3): {e}")

        # 降级返回
        logger.error(f"所有重试失败: {last_error}")
        return {
            "executive_summary": "AI分析暂时不可用",
            "overall_verdict": "AI分析降级模式",
            "error": str(last_error),
            "full_report_markdown": ""
        }

    async def generate_diagnosis_suggestion(self, diagnosis: dict) -> dict:
        """
        基于诊断结果生成 LLM 根因解释 + 可执行改进建议（P2）。
        失败时返回确定性降级结果（不影响主流程）。
        """
        if not self.api_key:
            return {"root_cause": diagnosis.get("root_cause", ""), "suggestion": "", "action_type": "", "expected_impact": ""}

        import json as _json
        module = diagnosis.get("module_name", "")
        pattern = diagnosis.get("pattern", "")
        problem = diagnosis.get("problem", "")
        hotspots = diagnosis.get("evidence", {}).get("hotspots", [])
        metrics = diagnosis.get("evidence", {}).get("module_metrics", {})

        hotspot_text = "\n".join([
            f"- {h.get('item_name') or h.get('item_id')}: 被人工修改{h.get('edit_count')}次, AI置信度{h.get('avg_confidence')}"
            for h in hotspots[:5]
        ]) or "(暂无足够修改样本)"

        prompt = f"""你是AI评分系统的诊断专家。基于以下确定性诊断数据，给出根因分析和一条最优先的改进建议。

【异常模块】{module}
【偏差模式】{pattern}
【问题】{problem}
【模块指标】一致性率{metrics.get('consistency_rate')}%, 编辑率{metrics.get('edit_rate')}%, 平均置信度{metrics.get('avg_confidence')}
【修改热点检查项】
{hotspot_text}

请输出合法JSON(不要markdown代码块)，格式：
{{
  "root_cause": "<一句话根因: AI评分在哪方面缺失或偏差, 引用具体检查项>",
  "action_type": "add_rule|adjust_threshold|refine_prompt|add_edge_case",
  "suggestion": "<具体可执行建议: 补充什么案例/调什么阈值/改什么prompt>",
  "expected_impact": "<预计提升什么指标, 幅度多少>"
}}

action_type 选择规则:
- 漏检型/过严型 -> add_rule
- 不确定型/低置信度 -> adjust_threshold 或 add_edge_case
- 盲目自信型 -> refine_prompt"""

        try:
            client = await self.get_client()
            start = _time.time()
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": getattr(settings, 'DEEPSEEK_REPORT_MODEL', 'deepseek-chat'),
                    "messages": [
                        {"role": "system", "content": "你是AI评分系统的诊断专家，擅长从评分数据中追溯根因并给出可落地的改进建议。直接输出合法JSON。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.4,
                    "max_tokens": 800,
                    "response_format": {"type": "json_object"},
                },
            )
            if response.status_code != 200:
                raise Exception(f"API失败:{response.status_code}")
            result = response.json()
            _log_llm_usage(getattr(settings, 'DEEPSEEK_REPORT_MODEL', 'deepseek-chat'), "diagnosis", result, int((_time.time() - start) * 1000))
            content = result["choices"][0]["message"]["content"].strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            parsed = _json.loads(content)
            valid = {"add_rule", "adjust_threshold", "refine_prompt", "add_edge_case"}
            if parsed.get("action_type") not in valid:
                parsed["action_type"] = "add_rule"
            return parsed
        except Exception as e:
            logger.warning(f"诊断建议生成失败(降级): {e}")
            return {"root_cause": diagnosis.get("root_cause", ""), "suggestion": "", "action_type": "", "expected_impact": ""}
