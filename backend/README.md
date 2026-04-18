# 后端 API 文档

## 环境配置

### 环境变量 (.env)

```env
# 数据库
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/quality_check
# 或使用 SQLite
# DATABASE_URL=sqlite:///./quality_check.db

# JWT 密钥（必填）
SECRET_KEY=your-secret-key-here

# AI API
DASHSCOPE_API_KEY=your-dashscope-api-key

# CORS 允许的域名（逗号分隔）
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# 日志级别
LOG_LEVEL=INFO
```

### 依赖安装

```bash
pip install -r requirements.txt
```

## 启动服务

```bash
# 开发模式
uvicorn main:app --reload --port 8000

# 生产模式
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API 端点

### 认证 (/api/v1/auth)

| 方法 | 端点 | 描述 |
|-----|------|-----|
| POST | /login | 用户登录 |
| POST | /register | 用户注册 |
| GET | /me | 获取当前用户信息 |
| GET | /inspectors | 获取检查员列表 |

### 任务 (/api/v1/tasks)

| 方法 | 端点 | 描述 |
|-----|------|-----|
| GET | / | 获取任务列表 |
| POST | / | 创建新任务 |
| GET | /{task_id} | 获取任务详情 |
| POST | /{task_id}/assign | 分配模块给检查员 |
| GET | /module-template/{module} | 获取模块检查项模板 |

### 检查记录 (/api/v1/records)

| 方法 | 端点 | 描述 |
|-----|------|-----|
| POST | / | 创建检查记录 |
| GET | /{record_id} | 获取检查记录详情 |
| PUT | /{record_id}/items/{item_id} | 更新检查项状态 |
| POST | /{record_id}/issues | 提交问题点 |
| PUT | /{record_id}/complete | 完成模块检查 |

### 评分 (/api/v1/scoring)

| 方法 | 端点 | 描述 |
|-----|------|-----|
| POST | /start/{task_id} | 触发AI评分 |
| GET | /status/{task_id} | 获取评分进度 |
| GET | /module-status/{task_id} | 获取模块评分状态 |

### 报告 (/api/v1/reports)

| 方法 | 端点 | 描述 |
|-----|------|-----|
| POST | /generate/{task_id} | 生成报告 |
| GET | /status/{task_id} | 获取报告生成状态 |
| GET | /list/all | 获取报告列表 |
| GET | /{task_id} | 获取报告详情 |
| GET | /{task_id}/download | 下载报告文件 |

### 整改 (/api/v1/rectifications)

| 方法 | 端点 | 描述 |
|-----|------|-----|
| GET | /pending | 获取待整改列表 |
| GET | /all | 获取所有整改记录 |
| POST | /{rectification_id}/submit | 提交整改 |
| POST | /{rectification_id}/recheck | 重新AI核查 |

### 编排器 (/api/v1/orchestrator)

| 方法 | 端点 | 描述 |
|-----|------|-----|
| POST | /run | 一键执行完整流程 |
| GET | /status/{task_id} | 获取流水线状态 |

## 测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行指定测试
python -m pytest tests/test_api.py -v

# 运行测试并查看输出
python -m pytest tests/test_workflow.py -v -s
```

## 数据库

### 初始化

```bash
# 创建数据库
mysql -u root -p -e "CREATE DATABASE quality_check CHARACTER SET utf8mb4;"

# 初始化表（启动时自动创建）
python -c "from database import init_db; init_db()"
```

### 常用操作

```bash
# 进入 Python Shell
python -c "
from database import SessionLocal
from models.models import User, Project

db = SessionLocal()
# 查询所有用户
users = db.query(User).all()
for u in users:
    print(f'{u.username} - {u.role}')
db.close()
"
```

## 日志

日志文件位置：`backend/logs/app.log`

查看实时日志：
```bash
tail -f logs/app.log
```

## 常见问题

### 1. 报告生成失败

检查任务状态是否为 `completed`，以及是否有评分结果：
```python
# 诊断脚本
python test_scoring.py
```

### 2. AI 评分超时

调整超时设置或检查网络连接。评分是异步进行的，可以稍后查询状态。

### 3. 数据库连接失败

确认 MySQL 服务正在运行，以及 `.env` 中的 `DATABASE_URL` 配置正确。
