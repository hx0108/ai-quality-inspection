# 品质检查系统 — 生产环境改善实施方案

> 生成日期: 2026-04-13 | 最后更新: 2026-05-09

---

## 执行状态总览

| 优先级 | 改善项 | 状态 | 说明 |
|---|---|---|---|
| P0 | P0-1 文件上传安全加固 | ✅ 已实施 | config.py 增加 MAX_PHOTO_SIZE 限制 |
| P0 | P0-2 注册接口安全加固 | ✅ 已实施 | 注册流程增加权限校验 |
| P0 | P0-3 照片路径安全校验 | ✅ 已实施 | 路径遍历防护 |
| P0 | P0-4 DEBUG 模式环境变量化 | ✅ 已实施 | config.py 读取环境变量控制 |
| P0 | P0-5 健康检查状态码修复 | ✅ 已实施 | /health 端点规范化 |
| P1 | P1-1 LLM 调用统一重试 + 熔断器 | ✅ 已实施 | llm_client.py 含重试逻辑 |
| P1 | P1-2 报告 Word 生成异常处理 | ✅ 已实施 | 报告生成增加错误兜底 |
| P1 | P1-3 优雅关机逻辑 | ⬜ 待实施 | |
| P1 | P1-4 共享 httpx 客户端线程安全 | ✅ 已实施 | llm_client.py 统一管理 |
| P1 | P1-5 指标计算运算符优先级 Bug | ✅ 已实施 | |
| P2 | P2-1 N+1 查询优化 | ⬜ 待实施 | 查询量较小，暂未成为瓶颈 |
| P2 | P2-2 数据库添加缺失索引 | ⬜ 待实施 | SQLite 场景下收益有限 |
| P2 | P2-3 长期记忆哈希稳定性修复 | ✅ 已实施 | |
| P2 | P2-4 CORS 配置收紧 | ✅ 已实施 | config.py 白名单模式 |
| P2 | P2-5 信息泄露修复 | ✅ 已实施 | 错误信息脱敏 |
| P3 | P3-1 Dashboard 组件拆分 | ✅ 已实施 | PC Dashboard 重构为子组件 |
| P3 | P3-2 ECharts 按需导入 | ✅ 已实施 | utils/echarts.js 统一封装 |
| P3 | P3-3 离线同步可靠性加固 | ✅ 已实施 | offlineDB + syncManager 双保险 |
| P3 | P3-4 前端 Token 过期检查 | ✅ 已实施 | request.js 拦截器自动检测 |
| P3 | P3-5 Logout 清理一致性修复 | ✅ 已实施 | auth store 统一清理 |
| P4 | P4-1 补充 API 端点测试 | ✅ 已实施 | backend/tests/ 含 7 个测试文件 |
| P4 | P4-2 指标采集定时调度 | ✅ 已实施 | metrics_collector.py 已部署 |

> **实施率: 19/22 (86%)** — 剩余 3 项（P1-3 优雅关机、P2-1 N+1 优化、P2-2 数据库索引）因当前规模未达到瓶颈而暂缓。

---

## 目录

1. [P0 紧急修复（生产安全）](#p0-紧急修复)
2. [P1 高优先级（系统可靠性）](#p1-高优先级)
3. [P2 中优先级（性能与架构）](#p2-中优先级)
4. [P3 前端改善](#p3-前端改善)
5. [P4 测试与可观测性](#p4-测试与可观测性)
6. [整体风险评估](#整体风险评估)
7. [实施顺序与回滚策略](#实施顺序与回滚策略)

---

## P0 紧急修复

### P0-1: 文件上传安全加固

**问题:** 照片上传接口无文件大小限制，仅检查扩展名，可导致 DoS 和任意文件上传。

**修改文件:**
- `backend/api/inspection.py`
- `backend/config.py`

**具体方案:**

**config.py** — 新增配置常量:
```python
# 在 Settings 类中添加（约第42行后）
MAX_PHOTO_SIZE: int = int(os.getenv("MAX_PHOTO_SIZE", 10 * 1024 * 1024))  # 默认10MB
ALLOWED_PHOTO_TYPES: list = ["image/jpeg", "image/png", "image/gif"]
```

**inspection.py** — upload_photo 函数（约第385-441行）中添加校验:
```python
# 在 file = upload_file 之前添加
content = await file.read()
if len(content) > settings.MAX_PHOTO_SIZE:
    raise HTTPException(400, f"文件大小超过限制({settings.MAX_PHOTO_SIZE // 1024 // 1024}MB)")

# 替换原来的 content = await file.read()
# 添加 MIME 类型校验（通过文件头 magic bytes）
import struct
def _validate_image(content: bytes) -> bool:
    """通过文件头校验真实图片类型"""
    if len(content) < 4:
        return False
    signatures = {
        b'\xff\xd8\xff': 'jpeg',
        b'\x89PNG': 'png',
        b'GIF8': 'gif',
    }
    for sig in signatures:
        if content[:len(sig)] == sig:
            return True
    return False

if not _validate_image(content):
    raise HTTPException(400, "不支持的图片格式")
```

**inspection.py** — batch_sync_offline（约第679-840行）同样添加大小校验。

**对现有系统影响:**
- 影响: 合法用户无感知（正常照片通常 <5MB）
- 风险: 无。向后兼容，仅拒绝超大/伪造文件
- 回滚: 移除校验代码即可

---

### P0-2: 注册接口安全加固

**问题:** `/register` 无认证、无限流、无验证码，可被批量注册。

**修改文件:**
- `backend/api/auth.py`

**具体方案:**

**auth.py** — 将登录限流扩展为通用限流器:
```python
# 第26行附近，改造现有 _login_attempts
from collections import OrderedDict

class LRURateLimiter:
    """固定容量、自动清理的限流器"""
    def __init__(self, max_ips: int = 10000, max_attempts: int = 5, window: int = 60):
        self._data: OrderedDict[str, list] = OrderedDict()
        self.max_ips = max_ips
        self.max_attempts = max_attempts
        self.window = window

    def check(self, key: str):
        now = time.time()
        attempts = self._data.get(key, [])
        attempts = [t for t in attempts if now - t < self.window]

        if len(attempts) >= self.max_attempts:
            self._data[key] = attempts
            self._data.move_to_end(key)
            raise HTTPException(429, "操作过于频繁，请稍后再试")

        attempts.append(now)
        self._data[key] = attempts
        self._data.move_to_end(key)

        # 超容量时清理最早的条目
        if len(self._data) > self.max_ips:
            self._data.popitem(last=False)

_register_limiter = LRURateLimiter(max_ips=5000, max_attempts=3, window=300)  # 5分钟3次
```

**auth.py** — register 端点添加限流:
```python
@router.post("/register")
async def register(request: RegisterRequest, req: Request, db: Session = Depends(get_db)):
    client_ip = req.client.host
    _register_limiter.check(f"register:{client_ip}")  # 新增
    # ... 原有逻辑
```

**对现有系统影响:**
- 影响: 正常注册用户不受影响（5分钟内最多3次已足够）
- 风险: 低。限流器内存有上限（5000 IP），不会 OOM
- 回滚: 移除 `_register_limiter.check()` 调用即可

---

### P0-3: 照片路径安全校验

**问题:** `FileResponse(photo.file_path)` 未验证路径在 `PHOTOS_DIR` 内。

**修改文件:**
- `backend/api/inspection.py`

**具体方案:**

**inspection.py** — get_photo 函数（约第233-282行）中添加:
```python
# 在 return FileResponse(photo.file_path, ...) 之前添加
import os
real_path = os.path.realpath(photo.file_path)
allowed_dir = os.path.realpath(str(settings.PHOTOS_DIR))
if not real_path.startswith(allowed_dir):
    logger.error(f"非法文件路径访问: {photo.file_path}")
    raise HTTPException(403, "禁止访问")
```

**对现有系统影响:**
- 影响: 零。所有合法照片路径都在 `PHOTOS_DIR` 内
- 风险: 无
- 回滚: 移除校验即可

---

### P0-4: DEBUG 模式环境变量化

**问题:** `DEBUG: bool = True` 硬编码。

**修改文件:**
- `backend/config.py`

**具体方案:**

**config.py** 第19行:
```python
# 改为
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
```

**对现有系统影响:**
- 影响: 生产环境必须设置 `DEBUG=true` 才会开启调试（默认关闭）
- 风险: 需确认 `.env` 中无需显式添加 `DEBUG=true`（开发环境需手动设置）
- 回滚: 改回 `DEBUG: bool = True`

---

### P0-5: 健康检查状态码修复

**问题:** 数据库断连时返回 HTTP 200。

**修改文件:**
- `backend/main.py`

**具体方案:**

**main.py** `/health` 端点（约第195-223行）:
```python
@app.get("/health")
async def health():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected", "error": str(e)}
        )
```

**对现有系统影响:**
- 影响: 无。负载均衡器/Nginx 可正确识别 503
- 风险: 无
- 回滚: 改回 `return {...}` 即可

---

## P1 高优先级

### P1-1: LLM 调用统一重试 + 熔断器

**问题:** 关键 LLM 方法（报告生成、模块分析）零重试，非关键方法反而有重试。

**修改文件:**
- `backend/core/llm_client.py`

**具体方案:**

在文件顶部新增通用重试装饰器和熔断器:
```python
import asyncio
from functools import wraps
from datetime import datetime, timedelta
from collections import defaultdict

class CircuitBreaker:
    """简单的熔断器：连续失败 N 次后断开，一段时间后半开"""
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self._failure_count = defaultdict(int)
        self._last_failure = defaultdict(float)
        self._state = defaultdict(lambda: "closed")  # closed / open / half_open
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout

    def is_open(self, key: str) -> bool:
        if self._state[key] == "open":
            if time.time() - self._last_failure[key] > self._recovery_timeout:
                self._state[key] = "half_open"
                return False
            return True
        return False

    def record_success(self, key: str):
        self._failure_count[key] = 0
        self._state[key] = "closed"

    def record_failure(self, key: str):
        self._failure_count[key] += 1
        self._last_failure[key] = time.time()
        if self._failure_count[key] >= self._failure_threshold:
            self._state[key] = "open"

# 全局熔断器实例
_qwen_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=120)
_deepseek_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=180)

def with_retry(max_retries=2, base_delay=2, breaker=None, breaker_key=None):
    """LLM 调用重试装饰器"""
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
```

**为关键方法添加重试:**

```python
# DeepSeekClient.generate_report — 添加重试
@with_retry(max_retries=2, base_delay=3, breaker=_deepseek_breaker, breaker_key="generate_report")
async def generate_report(self, ...):
    # 原有代码不变

# DeepSeekClient.analyze_module — 添加重试
@with_retry(max_retries=2, base_delay=2, breaker=_deepseek_breaker, breaker_key="analyze_module")
async def analyze_module(self, ...):
    # 原有代码不变

# DeepSeekClient.compare_reports — 保留原有3次重试，替换为统一装饰器
@with_retry(max_retries=3, base_delay=3, breaker=_deepseek_breaker, breaker_key="compare_reports")
async def compare_reports(self, ...):
    # 移除方法内部的 sleep/retry 逻辑，装饰器统一处理
```

**对现有系统影响:**
- 影响: 无副作用。成功时行为完全一致
- 风险: 中。重试会增加 LLM API 调用成本（预计增加 5-10% 在故障场景下）
  - 缓解: 熔断器在连续失败后短路，避免无意义重试
  - 缓解: 最大重试次数可配置
- 回滚: 移除装饰器即可

---

### P1-2: 报告 Word 生成异常处理

**问题:** `generate_word_report()` 无 try/except。

**修改文件:**
- `backend/agents/report/nodes.py`

**具体方案:**

**report/nodes.py** export_files 函数（约第290-325行）:
```python
async def export_files(state: dict) -> dict:
    # ... 现有代码 ...

    # Word 生成 — 添加异常保护
    word_success = False
    try:
        generate_word_report(report_content, word_path)
        word_success = True
        logger.info(f"Word 报告已生成: {word_path}")
    except Exception as e:
        logger.error(f"Word 报告生成失败: {e}", exc_info=True)
        # 降级: 仅使用 PDF

    # PDF 生成 — 已有保护，保持不变
    pdf_success = False
    try:
        generate_pdf_report(report_content, pdf_path)
        pdf_success = True
        logger.info(f"PDF 报告已生成: {pdf_path}")
    except Exception as e:
        logger.error(f"PDF 报告生成失败: {e}", exc_info=True)

    if not word_success and not pdf_success:
        return {"errors": state.get("errors", []) + ["报告文件导出失败"]}

    return {
        "word_path": word_path if word_success else None,
        "pdf_path": pdf_path if pdf_success else None,
        # ... 其余字段
    }
```

**对现有系统影响:**
- 影响: 正常情况无变化。异常时降级为仅生成 PDF，而非整个节点崩溃
- 风险: 低
- 回滚: 移除 try/except 即可

---

### P1-3: 优雅关机逻辑

**问题:** 应用关闭时未释放 httpx 客户端和数据库引擎。

**修改文件:**
- `backend/main.py`

**具体方案:**

**main.py** lifespan 函数（约第17-43行）:
```python
@asynccontextmanager
async def lifespan(app):
    # ===== 启动逻辑（保持不变）=====
    secret_key = os.getenv("SECRET_KEY", "")
    if not secret_key:
        raise RuntimeError("SECRET_KEY 环境变量未设置")
    logger.info(f"启动 {settings.APP_NAME} ...")
    init_db()
    # ... 其余启动逻辑 ...

    yield

    # ===== 关机逻辑（新增）=====
    logger.info("应用正在关闭，清理资源...")

    # 关闭共享 httpx 客户端
    from core.llm_client import QwenClient, DeepSeekClient
    for client_cls in [QwenClient, DeepSeekClient]:
        try:
            if client_cls._shared_client and not client_cls._shared_client.is_closed:
                await client_cls._shared_client.aclose()
                logger.info(f"已关闭 {client_cls.__name__} httpx 客户端")
        except Exception as e:
            logger.error(f"关闭 {client_cls.__name__} 客户端失败: {e}")

    # 释放数据库引擎
    try:
        from database import engine
        engine.dispose()
        logger.info("数据库引擎已释放")
    except Exception as e:
        logger.error(f"释放数据库引擎失败: {e}")

    logger.info("资源清理完成")
```

**对现有系统影响:**
- 影响: 无。仅在关机时执行清理
- 风险: 无
- 回滚: 移除 yield 后的代码即可

---

### P1-4: 共享 httpx 客户端线程安全

**问题:** `get_client()` 无锁保护，可能创建多个客户端。

**修改文件:**
- `backend/core/llm_client.py`

**具体方案:**

**llm_client.py** QwenClient 类（约第131行）:
```python
import asyncio

class QwenClient:
    _shared_client: Optional[httpx.AsyncClient] = None
    _lock = asyncio.Lock()  # 新增

    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        if cls._shared_client is not None and not cls._shared_client.is_closed:
            return cls._shared_client
        async with cls._lock:  # 新增锁保护
            # 双重检查
            if cls._shared_client is not None and not cls._shared_client.is_closed:
                return cls._shared_client
            cls._shared_client = httpx.AsyncClient(
                timeout=httpx.Timeout(45.0),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
            )
            return cls._shared_client
```

DeepSeekClient 同样处理。

**对现有系统影响:**
- 影响: 无。仅增加锁保护，不改变正常流程
- 风险: 极低。asyncio.Lock 在高并发下有微秒级开销
- 回滚: 移除锁即可

---

### P1-5: 指标计算运算符优先级 Bug

**问题:** `1 - total_edited / total_scored * 100` 运算顺序错误。

**修改文件:**
- `backend/core/metrics_collector.py`

**具体方案:**

**metrics_collector.py** 第50行:
```python
# 修改前（错误）
consistency_rate = (1 - total_edited / total_scored * 100) if total_scored > 0 else 100

# 修改后（正确）
consistency_rate = (1 - total_edited / total_scored) * 100 if total_scored > 0 else 100
```

第276行同样修改:
```python
# 修改前（错误）
"consistency_rate": round((1 - today_edited / today_scored * 100), 1) if today_scored > 0 else 100,

# 修改后（正确）
"consistency_rate": round((1 - today_edited / today_scored) * 100, 1) if today_scored > 0 else 100,
```

**对现有系统影响:**
- 影响: **数据修正**。修复后一致性率从负数/错误值变为正确的百分比
- 风险: 低。此值目前仅用于展示，不影响业务逻辑
- 回滚: 改回原公式
- 注意: 需检查已保存的 `ai_metrics` 表中历史数据是否需要重算

---

## P2 中优先级

### P2-1: N+1 查询优化

**问题:** 多处循环内查询数据库。

**修改文件:**
- `backend/api/inspection.py`

**具体方案:**

**inspection.py** get_record_detail（约第285-341行）— 添加预加载:
```python
# 修改前
record = db.query(InspectionRecord).filter(
    InspectionRecord.record_id == record_id
).first()

# 修改后 — 使用 joinedload 预加载关联数据
from sqlalchemy.orm import joinedload, selectinload

record = db.query(InspectionRecord).options(
    joinedload(InspectionRecord.issues).selectinload(Issue.photos),
    joinedload(InspectionRecord.task).joinedload(InspectionTask.project),
    joinedload(InspectionRecord.inspector),
).filter(
    InspectionRecord.record_id == record_id
).first()
```

**inspection.py** complete_record（约第891-906行）— 批量查询整改记录:
```python
# 修改前
for issue in issues:
    existing_rect = db.query(Rectification).filter(
        Rectification.issue_id == issue.issue_id
    ).first()

# 修改后 — 批量查询
issue_ids = [issue.issue_id for issue in issues]
existing_rects = db.query(Rectification).filter(
    Rectification.issue_id.in_(issue_ids)
).all()
existing_rect_map = {r.issue_id: r for r in existing_rects}

for issue in issues:
    existing_rect = existing_rect_map.get(issue.issue_id)
    # ... 原有逻辑
```

**对现有系统影响:**
- 影响: **性能提升**。减少数据库查询次数（从 N+1 降至 1-2 次）
- 风险: 低。`joinedload` 是 SQLAlchemy 标准用法
- 回滚: 移除 `options()` 调用即可

---

### P2-2: 数据库添加缺失索引

**问题:** 多个外键列缺少索引。

**修改文件:**
- `backend/database.py`（通过迁移添加）
- `backend/models/models.py`（模型定义同步更新）

**具体方案:**

**models.py** — 修改以下列定义（添加 `index=True`）:
```python
# Issue 表 (第156行)
record_id = Column(String(50), ForeignKey("inspection_records.record_id"), nullable=False, index=True)

# Photo 表 (第176行)
issue_id = Column(String(50), ForeignKey("issues.issue_id"), nullable=True, index=True)

# Rectification 表 (第275行)
issue_id = Column(String(50), ForeignKey("issues.issue_id"), nullable=False, index=True)

# InspectionRecord 表
project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
inspector_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

# LlmUsageLog 表 (第339行)
task_id = Column(String(50), nullable=True, index=True)

# Notification 表 (第506行)
user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
```

**database.py** — 添加迁移函数:
```python
def _migrate_add_indexes():
    """为缺少索引的外键列添加索引"""
    indexes_to_add = [
        ("issues", "record_id", "ix_issues_record_id"),
        ("photos", "issue_id", "ix_photos_issue_id"),
        ("rectifications", "issue_id", "ix_rects_issue_id"),
        ("inspection_records", "project_id", "ix_records_project_id"),
        ("inspection_records", "inspector_id", "ix_records_inspector_id"),
        ("llm_usage_logs", "task_id", "ix_llm_task_id"),
        ("notifications", "user_id", "ix_notifications_user_id"),
    ]
    for table, column, idx_name in indexes_to_add:
        try:
            engine.execute(text(
                f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})"
            ))
        except Exception as e:
            logger.debug(f"索引 {idx_name} 已存在或创建失败: {e}")
```

**对现有系统影响:**
- 影响: 首次启动时创建索引（大表可能需要几秒），之后查询加速
- 风险: 低。`CREATE INDEX IF NOT EXISTS` 安全幂等
- 注意: 如果 `inspection.db` 数据量大（>10万行），索引创建可能耗时较长，建议在低峰期执行
- 回滚: `DROP INDEX` 即可

---

### P2-3: 长期记忆哈希稳定性修复

**问题:** Python `hash()` 跨进程不稳定。

**修改文件:**
- `backend/core/long_memory.py`

**具体方案:**

**long_memory.py** 第357行:
```python
# 修改前（不稳定）
content_hash = str(hash(desc_text))

# 修改后（跨进程稳定）
import hashlib
content_hash = hashlib.sha256(desc_text.encode("utf-8")).hexdigest()[:32]
```

**对现有系统影响:**
- 影响: 修复后 `find_similar_memory` 可正确去重
- 风险: **中低**。已有的 `content_hash` 值将全部失效（因为哈希算法变了），需要清理或接受一段时间内的重复记忆
  - 缓解: 可运行一次性脚本重新计算所有现有记忆的 hash
- 回滚: 改回 `hash()` 即可

---

### P2-4: CORS 配置收紧

**问题:** `allow_methods=["*"]` + `allow_headers=["*"]` 过于宽松。

**修改文件:**
- `backend/main.py`

**具体方案:**

**main.py** 第166-172行:
```python
# 修改前
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 修改后
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)
```

**对现有系统影响:**
- 影响: 无。前端仅使用 GET/POST/PUT/DELETE 和 Authorization/Content-Type 头
- 风险: 低。如后续引入新 header 需要在此处添加
- 回滚: 改回 `["*"]` 即可

---

### P2-5: 信息泄露修复

**问题:** 异常详情直接返回给客户端。

**修改文件:**
- `backend/api/orchestrator.py`
- `backend/api/auth.py`
- `backend/api/inspection.py`

**具体方案:**

统一模式 — 将 `detail=f"...{str(e)}"` 改为通用消息:
```python
# orchestrator.py 第133行
# 修改前
raise HTTPException(500, detail=f"流水线执行失败: {str(e)}")
# 修改后
logger.error(f"流水线执行失败: {e}", exc_info=True)
raise HTTPException(500, detail="流水线执行失败，请稍后重试")

# auth.py 第207行
# 修改前
raise HTTPException(404, detail=f"项目「{request.project_name}」不存在，请刷新页面后重试")
# 修改后（保留项目名称，移除内部信息即可）
raise HTTPException(404, detail=f"项目「{request.project_name}」不存在")
```

**对现有系统影响:**
- 影响: 前端错误提示更简洁，不泄露内部信息
- 风险: 无
- 回滚: 改回原样

---

## P3 前端改善

### P3-1: Dashboard.vue 组件拆分

**问题:** 单文件1541行，包含7个子视图。

**修改文件:**
- 新建 7 个子组件文件
- 修改 `frontend/src/views/pc/Dashboard.vue`

**具体方案:**

拆分为:
```
frontend/src/views/pc/dashboard/
├── index.vue                  # 主组件（布局+数据加载）
├── StatsCards.vue             # 统计卡片
├── TaskDrawer.vue             # 任务抽屉
├── CoverageDrawer.vue         # 覆盖率抽屉
├── IssueDrawer.vue            # 问题抽屉
├── RectificationDrawer.vue    # 整改抽屉
├── ModuleDialog.vue           # 模块详情对话框
└── ProjectDrawer.vue          # 项目抽屉
```

**对现有系统影响:**
- 影响: 无功能变化，仅代码组织优化
- 风险: 中。拆分过程可能引入变量/事件传递遗漏
  - 缓解: 拆分后逐个验证各抽屉功能
- 回滚: 恢复原 Dashboard.vue

---

### P3-2: ECharts 按需导入

**问题:** `import * as echarts from 'echarts'` 导入全部 (~800KB)。

**修改文件:**
- `frontend/src/views/pc/Dashboard.vue`

**具体方案:**

```javascript
// 修改前（第442行）
import * as echarts from 'echarts'

// 修改后 — 按需导入（与 Analysis.vue 保持一致）
import * as echarts from 'echarts/core'
import { BarChart, LineChart, PieChart, GaugeChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, LegendComponent,
  GridComponent, DatasetComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart, LineChart, PieChart, GaugeChart,
  TitleComponent, TooltipComponent, LegendComponent,
  GridComponent, DatasetComponent, CanvasRenderer
])
```

**对现有系统影响:**
- 影响: **包体积减少约 500-600KB**（生产环境 gzip 后约减少 150KB）
- 风险: 低。如果使用了未列出的图表类型会报错，可快速补上
- 回滚: 改回全量导入

---

### P3-3: 离线同步可靠性加固

**问题:** syncing 状态在标签页崩溃后永久卡住；合格项同步在首个失败后中断。

**修改文件:**
- `frontend/src/utils/syncManager.js`
- `frontend/src/utils/offlineDB.js`

**具体方案:**

**offlineDB.js** — getPendingOps 恢复 syncing 状态:
```javascript
// 第133行，增加对 syncing 的处理
export async function getPendingOps(recordId) {
    const store = await getStore('readonly')
    return new Promise((resolve, reject) => {
        const index = store.index('record_id')
        const request = index.getAll(recordId)
        request.onsuccess = async () => {
            const results = request.result || []
            // 将 syncing 状态重置为 pending（标签页崩溃残留）
            const stuckOps = results.filter(r => r.status === 'syncing')
            if (stuckOps.length > 0) {
                console.warn(`[OfflineDB] 发现 ${stuckOps.length} 条 syncing 状态残留，重置为 pending`)
                for (const op of stuckOps) {
                    await updateOpStatus(op.id, 'pending')
                }
            }
            // 返回 pending 和 failed 的（syncing 已被重置为 pending）
            resolve(results.filter(r => r.status === 'pending' || r.status === 'failed'))
        }
        request.onerror = () => reject(request.error)
    })
}
```

**syncManager.js** — 合格项同步失败不中断:
```javascript
// 第147-163行，修改合格项同步逻辑
if (qualifiedOps.length > 0) {
    syncProgress.value = `正在同步合格项 0/${qualifiedOps.length}`
    for (let i = 0; i < qualifiedOps.length; i++) {
        const op = qualifiedOps[i]
        syncProgress.value = `正在同步合格项 ${i + 1}/${qualifiedOps.length}`
        try {
            await updateOpStatus(op.id, 'syncing')
            await updateItemStatus(recordId, op.item_id, { status: 'checked' })
            await updateOpStatus(op.id, 'synced')
            totalSynced++
            if (onQualifiedSyncedCb) {
                onQualifiedSyncedCb(op.item_id)
            }
        } catch (e) {
            console.error('[SyncManager] 合格项同步失败:', op.item_id, e)
            await updateOpStatus(op.id, 'failed')  // 标记为 failed 而非 pending
            // 不再 break，继续同步下一项
            if (!e.response) {
                // 网络错误，设置延迟重试
                console.warn('[SyncManager] 网络不可用，暂停同步')
                break  // 仅在真正的网络断开时中断
            }
        }
    }
}
```

**对现有系统影响:**
- 影响: 离线同步更可靠，不会因单项失败丢失后续数据
- 风险: 低。逻辑更健壮，不影响正常流程
- 回滚: 恢复原文件

---

### P3-4: 前端 Token 过期检查

**问题:** 路由守卫仅检查 Token 存在性，不检查过期时间。

**修改文件:**
- `frontend/src/router/index.js`

**具体方案:**

```javascript
// 新增 Token 过期检查函数
function isTokenExpired(token) {
    try {
        const payload = JSON.parse(atob(token.split('.')[1]))
        return payload.exp * 1000 < Date.now()
    } catch {
        return true  // 无法解析则视为过期
    }
}

// 在 beforeEach 中使用（第159行后）
const token = localStorage.getItem('token')

// 新增：Token 过期检查
if (token && isTokenExpired(token)) {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    // 如果不在登录页，跳转登录
    if (to.path !== '/login' && to.path !== '/') {
        next('/login')
        return
    }
}
```

**对现有系统影响:**
- 影响: Token 过期后立即跳转登录页，而非等到 API 401 才跳转
- 风险: 低。仅增加前端校验，后端仍独立校验
- 回滚: 移除 `isTokenExpired` 检查即可

---

### P3-5: logout 清理一致性修复

**问题:** `logout()` 未调用 `_clearAllState()`。

**修改文件:**
- `frontend/src/stores/auth.js`

**具体方案:**

```javascript
// 修改前（第51-57行）
logout() {
    this.token = ''
    this.user = {}
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    router.push('/login')
}

// 修改后
logout() {
    this._clearAllState()
    router.push('/login')
}
```

**对现有系统影响:**
- 影响: 登出后 localStorage 完全清空，避免跨账号数据残留
- 风险: 低。`_clearAllState()` 仅清除 localStorage，IndexedDB 数据不受影响
- 回滚: 恢复原 logout 方法

---

## P4 测试与可观测性

### P4-1: 补充 API 端点测试

**新增文件:**
- `backend/tests/test_auth_security.py`
- `backend/tests/test_rectification.py`
- `backend/tests/test_analysis.py`

**具体方案:**

优先补充以下测试:
```
test_auth_security.py:
  - test_register_rate_limited          # 注册限流
  - test_login_invalid_credentials       # 错误凭证
  - test_expired_token_rejected          # 过期 Token
  - test_disabled_user_rejected          # 禁用用户

test_rectification.py:
  - test_submit_rectification            # 提交整改
  - test_ai_check_rectification          # AI 核查
  - test_admin_review_rectification      # 管理员审核
  - test_unauthorized_access             # 越权访问

test_analysis.py:
  - test_cross_project_analysis          # 跨项目分析
  - test_cross_time_analysis             # 跨时间分析
  - test_analysis_progress_tracking      # 进度追踪
```

**对现有系统影响:**
- 影响: 无。仅新增测试文件
- 风险: 无
- 回滚: 删除测试文件

---

### P4-2: 指标采集定时调度

**问题:** `run_metrics_collection` 函数存在但从未被调度。

**修改文件:**
- `backend/main.py`

**具体方案:**

使用 APScheduler 添加定时任务:
```python
# 在 lifespan 中启动调度器
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from core.metrics_collector import run_metrics_collection

scheduler = AsyncIOScheduler()

# 在 yield 之前添加
scheduler.add_job(
    run_metrics_collection,
    'cron',
    hour=2, minute=0,  # 每天凌晨2点执行
    id='metrics_collection',
    replace_existing=True
)
scheduler.start()
logger.info("定时任务调度器已启动")

# 在 yield 之后（关机逻辑中）
scheduler.shutdown(wait=False)
```

**对现有系统影响:**
- 影响: 新增依赖 `apscheduler`（需 `pip install APScheduler`）
- 风险: 低。定时任务独立运行，失败不影响主服务
- 回滚: 移除调度器代码和依赖

---

## 整体风险评估

### 改动量统计

| 优先级 | 修改文件数 | 新增文件数 | 预计代码变更行数 |
|--------|-----------|-----------|-----------------|
| P0 紧急 | 3 | 0 | ~80 行 |
| P1 高优 | 4 | 0 | ~200 行 |
| P2 中优 | 6 | 0 | ~120 行 |
| P3 前端 | 5 | 7 | ~400 行（含新组件） |
| P4 测试 | 1 | 3 | ~300 行 |
| **合计** | **19** | **10** | **~1100 行** |

### 对架构的影响

| 维度 | 影响程度 | 说明 |
|------|---------|------|
| 数据库 Schema | 低 | 仅添加索引，不修改表结构 |
| API 接口 | 无 | 无新增/删除/修改接口签名 |
| 前端路由 | 无 | 无路由变化 |
| 部署方式 | 低 | 新增 `APScheduler` 依赖 |
| 运行时行为 | 低 | 重试/熔断器仅影响故障场景 |
| 数据一致性 | 中 | 指标计算修复会改变历史展示数据 |

### 需要特别注意的变更

1. **P1-5 指标计算修复**: 修复后所有历史一致性率数据将变为正确值，但 `ai_metrics` 表中已存储的错误值不会自动修正。可选择:
   - 方案A: 接受历史数据偏差，仅修复后计算正确
   - 方案B: 运行一次性脚本重算历史指标

2. **P2-3 哈希算法变更**: 已存储的 `content_hash` 全部失效，`find_similar_memory` 短期内可能出现重复记忆。可选择:
   - 方案A: 接受过渡期重复，新记忆将正确去重
   - 方案B: 运行一次性脚本重新计算所有记忆的 hash

3. **P3-1 Dashboard 拆分**: 最大的单次改动，建议独立测试后再合入。

---

## 实施顺序与回滚策略

### 推荐实施顺序

```
第1步 (1天):  P0-1 ~ P0-5  紧急安全修复 → 部署验证
第2步 (2天):  P1-1 ~ P1-5  可靠性提升 → 部署验证
第3步 (2天):  P2-1 ~ P2-5  性能优化 → 部署验证
第4步 (3天):  P3-1 ~ P3-5  前端改善 → 部署验证
第5步 (持续): P4-1 ~ P4-2  测试补充
```

### 回滚策略

每一步骤独立提交 Git，出问题时回滚到上一个稳定提交:
```bash
# 回滚示例
git revert <commit-hash>  # 安全回滚单个提交
```

所有变更满足:
- 不修改数据库表结构（仅添加索引）
- 不修改 API 接口签名
- 不修改前端路由
- 每项改动可独立回滚

---

> **请审阅以上方案，确认后我将按优先级逐项实施。**
> 如有任何项需要调整或暂缓，请告知。
