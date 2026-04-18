# 物业品质检查多Agent系统 - 技术设计文档 (TECH_DESIGN)

## 1. 文档概述

| 项目名称 | 物业品质检查多Agent系统 |
|---------|----------------------|
| 版本号 | V1.0 |
| 创建日期 | 2026-03-26 |
| 文档状态 | 初稿 |

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户界面层 (UI Layer)                           │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    前端应用 (Vue 3 + Vite)                           │    │
│  │  ┌─────────────────────┐        ┌─────────────────────────────┐    │    │
│  │  │    移动端界面        │        │         PC端界面             │    │    │
│  │  │  (Vant 4组件库)      │        │    (Element Plus组件库)      │    │    │
│  │  │  • 模块选择          │        │    • 检查任务管理            │    │    │
│  │  │  • 现场检查录入       │        │    • 报告查看与导出          │    │    │
│  │  │  • 检查任务管理       │        │    • 用户/项目管理           │    │    │
│  │  │  • 评分与报告查看     │        │    （使用 /docs API调试页）  │    │    │
│  │  └─────────────────────┘        └─────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ HTTP/REST API
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              后端服务层 (Backend Layer)                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      FastAPI 后端服务                                │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐  │    │
│  │  │  认证服务    │  │  业务API    │  │        文件服务             │  │    │
│  │  │  JWT Token  │  │  RESTful    │  │    照片上传/报告导出        │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Agent协调层 (LangGraph)                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │   Agent 1       │  │   Agent 2       │  │          Agent 3            │  │
│  │   数据采集       │  │   智能评分       │  │          总结分析           │  │
│  │   (规则驱动)     │  │   (qwen-plus)   │  │       (deepseek-chat)        │  │
│  │   无LLM调用     │  │  按模块批量评分  │  │        报告生成             │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据存储层 (Data Layer)                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │   检查表模板     │  │   业务数据库     │  │        文件存储             │  │
│  │   (Excel)       │  │   (SQLite)      │  │    (照片/报告本地目录)       │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 架构说明

| 层级 | 职责 | 技术选型 |
|-----|------|---------|
| 用户界面层 | 提供移动端和PC端交互界面 | Vue 3 + Vant 4（移动端主界面）+ Element Plus（PC管理） |
| 后端服务层 | 提供RESTful API、认证、文件服务 | FastAPI |
| Agent协调层 | 三个Agent的编排和协同，状态管理 | LangGraph |
| 数据存储层 | 数据持久化存储 | SQLite + 本地文件系统 |

---

## 3. 技术选型

### 3.1 技术栈总览

| 类别 | 技术选型 | 版本要求 | 选型理由 |
|-----|---------|---------|---------|
| 编程语言 | Python | 3.9+ | 生态丰富，AI库支持好 |
| 前端框架 | Vue 3 + Vite | 3.x + 5.x | 现代化前端框架，支持响应式设计 |
| 移动端UI | Vant 4 | 4.x | 移动端组件丰富，体验好 |
| PC端UI | Element Plus | 2.x | 企业级组件库，功能完善 |
| 后端框架 | FastAPI | 0.100+ | 高性能异步框架，自动API文档 |
| Agent框架 | LangGraph | 0.0.40+ | 有状态工作流管理，支持循环和人工介入 |
| LLM (评分) | 通义千问 qwen-plus | - | 评分推理能力强，中文理解准确 |
| LLM (分析) | DeepSeek deepseek-chat | - | 长文本分析能力强，报告生成质量高 |
| 数据存储 | SQLite | 3.x | 轻量级，无需额外服务 |
| 文档生成 | python-docx | - | 生成Word报告 |
| Excel处理 | pandas + openpyxl | - | 读取检查表模板 |
| 认证 | JWT | - | 无状态认证，支持多端 |
| 文件存储 | 本地文件系统 | - | 简单可靠，无需额外服务 |

### 3.2 前后端分离架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           前后端分离架构                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         前端 (Vue 3)                                 │   │
│   │                                                                     │   │
│   │   移动端 (Vant 4)              PC端 (Element Plus，管理用)           │   │
│   │   ┌─────────────────┐          ┌─────────────────────────────┐     │   │
│   │   │ • 检查录入       │          │ • 任务创建与模块分配         │     │   │
│   │   │ • 检查任务管理   │          │ • 报告查看与导出             │     │   │
│   │   │ • 报告查看       │          │ • 用户/项目管理              │     │   │
│   │   │                 │          │                             │     │   │
│   │   └─────────────────┘          └─────────────────────────────┘     │   │
│   │                                                                     │   │
│   │   状态管理: Pinia    路由: Vue Router    HTTP: Axios               │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                        │                                    │
│                                        │ REST API (JSON)                    │
│                                        ▼                                    │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         后端 (FastAPI)                               │   │
│   │                                                                     │   │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐    │   │
│   │   │   路由层     │  │   服务层     │  │       Agent层           │    │   │
│   │   │  (API路由)   │  │  (业务逻辑)  │  │  (LangGraph工作流)      │    │   │
│   │   └─────────────┘  └─────────────┘  └─────────────────────────┘    │   │
│   │                                                                     │   │
│   │   认证: JWT    数据: SQLAlchemy    文件: 本地存储                   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 依赖清单

#### 后端依赖 (requirements.txt)

```txt
# Web框架
fastapi>=0.100.0
uvicorn>=0.23.0
python-multipart>=0.0.6

# 数据处理
pandas>=2.0.0
openpyxl>=3.1.0
sqlalchemy>=2.0.0

# Agent框架
langgraph>=0.0.40
langchain>=0.1.0

# LLM调用 - 通义千问 (评分Agent)
dashscope>=1.14.0

# LLM调用 - DeepSeek (分析Agent)
openai>=1.0.0

# 文档生成
python-docx>=0.8.11
reportlab>=4.0.0

# 认证
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4

# 工具库
python-dateutil>=2.8.0
Pillow>=10.0.0
tenacity>=8.0.0
python-dotenv>=1.0.0
pydantic>=2.0.0
```

#### 前端依赖 (package.json)

```json
{
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "pinia": "^2.1.0",
    "axios": "^1.6.0",
    "vant": "^4.8.0",
    "element-plus": "^2.5.0",
    "@element-plus/icons-vue": "^2.3.0"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "@vitejs/plugin-vue": "^5.0.0",
    "typescript": "^5.3.0",
    "unplugin-vue-components": "^0.26.0",
    "unplugin-auto-import": "^0.17.0"
  }
}
```

---

## 4. 项目结构

```
quality_inspection_system/
│
├── backend/                        # 后端服务
│   ├── main.py                     # FastAPI入口
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py             # 配置管理 (含双LLM API Key)
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                 # 依赖注入
│   │   ├── auth.py                 # 认证API
│   │   ├── tasks.py                # 检查任务API（父任务管理）
│   │   ├── inspection.py           # 检查记录API（模块级别）
│   │   ├── scoring.py              # 评分API
│   │   └── report.py               # 报告API
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py           # Agent基类
│   │   ├── data_collection_agent.py    # Agent 1: 数据采集
│   │   ├── scoring_agent.py        # Agent 2: 智能评分 (qwen-plus，按模块批量)
│   │   └── analysis_agent.py       # Agent 3: 总结分析 (deepseek-chat)
│   │
│   ├── workflow/
│   │   ├── __init__.py
│   │   ├── state.py                # LangGraph状态定义
│   │   ├── nodes.py                # 工作流节点
│   │   └── graph.py                # LangGraph工作流构建
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py             # 安全认证
│   │   ├── template_parser.py      # 模板解析器（含Excel列映射）
│   │   ├── llm_client.py           # 双LLM调用封装
│   │   ├── data_manager.py         # 数据管理
│   │   └── report_generator.py     # 报告生成器
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py                 # 用户模型
│   │   ├── task.py                 # 检查任务模型（父任务）
│   │   ├── inspection.py           # 检查记录模型（模块级别）
│   │   ├── scoring.py              # 评分模型
│   │   └── report.py               # 报告模型
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── task.py
│   │   ├── inspection.py
│   │   ├── scoring.py
│   │   └── report.py
│   │
│   ├── data/
│   │   ├── templates/              # 检查表模板目录
│   │   ├── database.db             # SQLite数据库
│   │   ├── photos/                 # 照片存储（按任务ID分目录）
│   │   └── reports/                # 生成的报告
│   │
│   └── requirements.txt
│
├── frontend/                       # 前端应用
│   ├── src/
│   │   ├── main.ts                 # 入口文件（含设备检测路由跳转）
│   │   ├── App.vue                 # 根组件
│   │   │
│   │   ├── api/
│   │   │   ├── auth.ts             # 认证API
│   │   │   ├── tasks.ts            # 检查任务API
│   │   │   ├── inspection.ts       # 检查API
│   │   │   ├── scoring.ts          # 评分API
│   │   │   └── report.ts           # 报告API
│   │   │
│   │   ├── views/
│   │   │   ├── mobile/             # 移动端页面（品质检查员现场使用）
│   │   │   │   ├── TaskList.vue    # 我的检查任务列表
│   │   │   │   ├── Inspection.vue  # 检查录入（按模块）
│   │   │   │   └── Report.vue      # 报告查看
│   │   │   │
│   │   │   └── pc/                 # PC端页面（质量主管/管理员使用）
│   │   │       ├── Tasks.vue       # 检查任务管理（创建任务/分配模块）
│   │   │       ├── Report.vue      # 报告管理与导出（Word/PDF）
│   │   │       └── Settings.vue    # 系统设置（用户/项目管理）
│   │   │
│   │   ├── components/
│   │   │   ├── common/             # 通用组件
│   │   │   ├── mobile/             # 移动端组件
│   │   │   └── pc/                 # PC端组件
│   │   │
│   │   ├── stores/
│   │   │   ├── auth.ts             # 认证状态
│   │   │   ├── task.ts             # 检查任务状态
│   │   │   └── inspection.ts       # 检查状态
│   │   │
│   │   ├── router/
│   │   │   └── index.ts            # 路由配置（含设备自动检测跳转）
│   │   │
│   │   └── utils/
│   │       ├── request.ts          # HTTP请求封装
│   │       └── storage.ts          # 本地存储
│   │
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
└── docker-compose.yml              # Docker部署配置
```

---

## 5. 数据库设计

### 5.1 数据库表结构

#### 用户表 (users)

| 字段名 | 类型 | 说明 | 约束 |
|-------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| username | VARCHAR(50) | 用户名 | UNIQUE, NOT NULL |
| password_hash | VARCHAR(255) | 密码哈希 | NOT NULL |
| real_name | VARCHAR(50) | 真实姓名 | NOT NULL |
| role | VARCHAR(20) | 角色 | NOT NULL |
| is_active | BOOLEAN | 是否激活 | DEFAULT TRUE |
| created_at | DATETIME | 创建时间 | DEFAULT CURRENT_TIMESTAMP |
| updated_at | DATETIME | 更新时间 | DEFAULT CURRENT_TIMESTAMP |

> **注意**：`users` 表不再含 `project_id` 字段。用户与项目的关联通过检查任务分配（`task_assignments`）动态绑定，支持一名检查员负责多个项目的不同模块。

#### 项目表 (projects)

| 字段名 | 类型 | 说明 | 约束 |
|-------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| name | VARCHAR(100) | 项目名称 | UNIQUE, NOT NULL |
| code | VARCHAR(20) | 项目编码 | UNIQUE |
| address | VARCHAR(255) | 项目地址 | |
| created_at | DATETIME | 创建时间 | DEFAULT CURRENT_TIMESTAMP |

#### 检查任务表 (inspection_tasks) — 父任务

| 字段名 | 类型 | 说明 | 约束 |
|-------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| task_id | VARCHAR(50) | 任务ID，格式：TASK-YYYYMMDD-XXX | UNIQUE, NOT NULL |
| project_id | INTEGER | 项目ID | FOREIGN KEY, NOT NULL |
| check_date | DATE | 检查日期 | NOT NULL |
| status | VARCHAR(20) | 任务状态：in_progress / completed | NOT NULL |
| total_score | DECIMAL(5,2) | 项目总分（0-100） | |
| created_by | INTEGER | 创建人ID | FOREIGN KEY |
| created_at | DATETIME | 创建时间 | DEFAULT CURRENT_TIMESTAMP |
| updated_at | DATETIME | 更新时间 | DEFAULT CURRENT_TIMESTAMP |

#### 任务模块分配表 (task_assignments) — 记录每个模块分配给哪位检查员

| 字段名 | 类型 | 说明 | 约束 |
|-------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| task_id | VARCHAR(50) | 检查任务ID | FOREIGN KEY, NOT NULL |
| module_name | VARCHAR(50) | 检查模块名称 | NOT NULL |
| inspector_id | INTEGER | 分配的检查员ID | FOREIGN KEY, NOT NULL |
| UNIQUE | - | (task_id, module_name) | 每个任务每个模块只能分配一人 |

#### 检查记录表 (inspection_records) — 模块级别

| 字段名 | 类型 | 说明 | 约束 |
|-------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| record_id | VARCHAR(50) | 记录ID，格式：REC-YYYYMMDD-XXX | UNIQUE, NOT NULL |
| task_id | VARCHAR(50) | 所属检查任务ID | FOREIGN KEY, NOT NULL |
| project_id | INTEGER | 项目ID | FOREIGN KEY |
| module_name | VARCHAR(50) | 检查模块 | NOT NULL |
| inspector_id | INTEGER | 检查人ID | FOREIGN KEY |
| check_date | DATE | 检查日期 | NOT NULL |
| status | VARCHAR(20) | 状态：in_progress / completed | NOT NULL |
| data_json | TEXT | 完整JSON数据 | NOT NULL |
| created_at | DATETIME | 创建时间 | DEFAULT CURRENT_TIMESTAMP |
| updated_at | DATETIME | 更新时间 | DEFAULT CURRENT_TIMESTAMP |

#### 问题表 (issues)

| 字段名 | 类型 | 说明 | 约束 |
|-------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| issue_id | VARCHAR(50) | 问题ID，格式：ISS-YYYYMMDD-XXX | UNIQUE, NOT NULL |
| record_id | VARCHAR(50) | 检查记录ID | FOREIGN KEY |
| module_name | VARCHAR(50) | 所属模块 | NOT NULL |
| item_id | VARCHAR(20) | 检查项ID | NOT NULL |
| description | TEXT | 问题描述 | NOT NULL |
| location | VARCHAR(255) | 问题位置 | |
| severity | VARCHAR(20) | 严重程度：严重 / 一般 / 轻微 | NOT NULL |
| status | VARCHAR(20) | 检查项状态：pending / checked / skipped | NOT NULL |
| created_at | DATETIME | 创建时间 | DEFAULT CURRENT_TIMESTAMP |

#### 照片表 (photos)

| 字段名 | 类型 | 说明 | 约束 |
|-------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| photo_id | VARCHAR(50) | 照片ID，格式：PHO-YYYYMMDD-XXX | UNIQUE, NOT NULL |
| issue_id | VARCHAR(50) | 问题ID | FOREIGN KEY |
| file_path | VARCHAR(255) | 文件路径 | NOT NULL |
| file_name | VARCHAR(100) | 文件名 | NOT NULL |
| photo_type | VARCHAR(20) | 照片类型 | NOT NULL |
| upload_time | DATETIME | 上传时间 | DEFAULT CURRENT_TIMESTAMP |

#### 评分结果表 (scoring_results)

| 字段名 | 类型 | 说明 | 约束 |
|-------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| scoring_id | VARCHAR(50) | 评分ID | UNIQUE, NOT NULL |
| record_id | VARCHAR(50) | 记录ID | FOREIGN KEY |
| module_name | VARCHAR(50) | 模块名称 | NOT NULL |
| item_id | VARCHAR(20) | 检查项ID | NOT NULL |
| score | DECIMAL(3,1) | 评价得分（0-5，skipped项默认5） | NOT NULL |
| weight | DECIMAL(6,4) | 权重系数 | NOT NULL |
| weighted_score | DECIMAL(6,4) | 单项加权得分 = score × weight | NOT NULL |
| module_pct_score | DECIMAL(5,2) | 模块百分制得分（模块汇总后填入） | |
| scoring_basis | TEXT | 评分依据 | |
| is_skipped | BOOLEAN | 是否为跳过项（自动给满分） | DEFAULT FALSE |
| scored_at | DATETIME | 评分时间 | DEFAULT CURRENT_TIMESTAMP |

#### 报告表 (reports)

| 字段名 | 类型 | 说明 | 约束 |
|-------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| report_id | VARCHAR(50) | 报告ID | UNIQUE, NOT NULL |
| task_id | VARCHAR(50) | 检查任务ID | FOREIGN KEY |
| project_id | INTEGER | 项目ID | FOREIGN KEY |
| report_type | VARCHAR(20) | 报告类型 | NOT NULL |
| total_score | DECIMAL(5,2) | 项目总分（0-100） | NOT NULL |
| file_path | VARCHAR(255) | 文件路径 | |
| generated_at | DATETIME | 生成时间 | DEFAULT CURRENT_TIMESTAMP |

### 5.2 数据库关系图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           数据库关系图                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                  │
│   │   users     │     │  projects   │     │ inspection  │                  │
│   │   用户表     │     │   项目表     │     │  _records   │                  │
│   └─────────────┘     └─────────────┘     └─────────────┘                  │
│          │                   │                   │                          │
│          │                   │                   │                          │
│          └───────────────────┼───────────────────┘                          │
│                              │                                              │
│                              ▼                                              │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                  │
│   │   issues    │────▶│   photos    │     │  scoring    │                  │
│   │   问题表     │     │   照片表     │     │  _results   │                  │
│   └─────────────┘     └─────────────┘     └─────────────┘                  │
│                                                  │                         │
│                                                  │                         │
│                                                  ▼                         │
│   ┌─────────────┐                        ┌─────────────┐                   │
│   │   reports   │                        │  (其他表关联 │                   │
│   │   报告表     │                        │  见文字说明) │                   │
│   └─────────────┘                        └─────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. API接口设计

### 6.1 API概览

| 模块 | 路径前缀 | 说明 |
|------|---------|------|
| 认证 | /api/v1/auth | 用户登录、登出、Token刷新 |
| 用户 | /api/v1/users | 用户管理 |
| 项目 | /api/v1/projects | 项目管理 |
| 检查任务 | /api/v1/tasks | 检查任务管理（父任务、模块分配） |
| 检查 | /api/v1/inspections | 检查记录管理（模块级别） |
| 评分 | /api/v1/scoring | 评分管理 |
| 报告 | /api/v1/reports | 报告管理（含Word/PDF导出） |

### 6.2 认证API

```yaml
POST /api/v1/auth/login
  描述: 用户登录
  请求体:
    {
      "username": "string",
      "password": "string"
    }
  响应:
    {
      "code": 200,
      "data": {
        "access_token": "string",
        "token_type": "bearer",
        "expires_in": 86400,
        "user": {
          "id": 1,
          "username": "string",
          "real_name": "string",
          "role": "string"
        }
      }
    }

POST /api/v1/auth/logout
  描述: 用户登出
  请求头: Authorization: Bearer {token}
  响应:
    {
      "code": 200,
      "message": "登出成功"
    }

POST /api/v1/auth/refresh
  描述: 刷新Token
  请求头: Authorization: Bearer {token}
  响应:
    {
      "code": 200,
      "data": {
        "access_token": "string",
        "token_type": "bearer",
        "expires_in": 86400
      }
    }
```

### 6.3 检查记录API

```yaml
GET /api/v1/inspections
  描述: 获取检查记录列表
  请求头: Authorization: Bearer {token}
  查询参数:
    - project_id: 项目ID (可选)
    - status: 状态 (可选)
    - page: 页码
    - page_size: 每页数量
  响应:
    {
      "code": 200,
      "data": {
        "total": 100,
        "items": [
          {
            "record_id": "REC-20260326-001",
            "project_name": "幸福悦花园",
            "module_name": "客户服务",
            "inspector": "张三",
            "check_date": "2026-03-26",
            "status": "completed"
          }
        ]
      }
    }

POST /api/v1/inspections
  描述: 创建检查记录
  请求头: Authorization: Bearer {token}
  请求体:
    {
      "project_id": 1,
      "module_name": "客户服务",
      "check_date": "2026-03-26"
    }
  响应:
    {
      "code": 200,
      "data": {
        "record_id": "REC-20260326-001"
      }
    }

GET /api/v1/inspections/{record_id}
  描述: 获取检查记录详情
  请求头: Authorization: Bearer {token}
  响应:
    {
      "code": 200,
      "data": {
        "record_id": "REC-20260326-001",
        "project_info": {...},
        "modules": [...]
      }
    }

POST /api/v1/inspections/{record_id}/issues
  描述: 记录问题点
  请求头: Authorization: Bearer {token}
  请求体:
    {
      "item_id": "1.1",
      "description": "管家手机存在卡顿现象",
      "location": "A栋管家服务中心",
      "severity": "一般"
    }
  响应:
    {
      "code": 200,
      "data": {
        "issue_id": "ISS-001"
      }
    }

POST /api/v1/inspections/{record_id}/issues/{issue_id}/photos
  描述: 上传问题照片
  请求头: 
    Authorization: Bearer {token}
    Content-Type: multipart/form-data
  请求体: FormData with file
  响应:
    {
      "code": 200,
      "data": {
        "photo_id": "PHO-001",
        "file_path": "data/photos/..."
      }
    }
```

### 6.4 评分API

**评分模式说明：**
采用"检查完成后统一评分"模式，检查人员在现场完成所有模块的检查、问题记录和照片上传后，点击"开始评分"按钮，系统统一调用AI进行批量评分。

```yaml
POST /api/v1/scoring/{record_id}
  描述: 执行AI评分（检查完成后统一批量评分）
  请求头: Authorization: Bearer {token}
  响应:
    {
      "code": 200,
      "data": {
        "scoring_id": "SCR-001",
        "module_scores": [...],
        "total_score": 85.5
      }
    }

```

### 6.5 报告API

```yaml
POST /api/v1/reports/{record_id}
  描述: 生成检查报告
  请求头: Authorization: Bearer {token}
  请求体:
    {
      "report_type": "full"
    }
  响应:
    {
      "code": 200,
      "data": {
        "report_id": "RPT-001",
        "file_path": "data/reports/..."
      }
    }

GET /api/v1/reports/{report_id}
  描述: 获取报告详情
  请求头: Authorization: Bearer {token}
  响应:
    {
      "code": 200,
      "data": {
        "report_id": "RPT-001",
        "summary": {...},
        "module_analyses": [...]
      }
    }

GET /api/v1/reports/{report_id}/download
  描述: 下载报告文件
  请求头: Authorization: Bearer {token}
  查询参数:
    - format: 导出格式 (word/pdf)
  响应: 文件流
```

---

## 7. 安全性设计

### 7.1 认证机制

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           JWT认证流程                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   客户端                        服务端                                       │
│     │                             │                                         │
│     │  1. 登录请求                 │                                         │
│     │  (username/password)        │                                         │
│     │ ─────────────────────────▶  │                                         │
│     │                             │                                         │
│     │  2. 验证凭证                 │                                         │
│     │                             │  • 验证用户名密码                         │
│     │                             │  • 生成JWT Token                         │
│     │                             │  • 设置过期时间(24h)                      │
│     │                             │                                         │
│     │  3. 返回Token               │                                         │
│     │ ◀─────────────────────────  │                                         │
│     │                             │                                         │
│     │  4. 业务请求                 │                                         │
│     │  (Header: Bearer Token)     │                                         │
│     │ ─────────────────────────▶  │                                         │
│     │                             │                                         │
│     │                             │  • 验证Token签名                          │
│     │                             │  • 检查过期时间                           │
│     │                             │  • 提取用户信息                           │
│     │                             │  • 检查权限                               │
│     │                             │                                         │
│     │  5. 返回数据                 │                                         │
│     │ ◀─────────────────────────  │                                         │
│     │                             │                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 权限控制

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

class PermissionChecker:
    
    def __init__(self, required_permissions: list[str]):
        self.required_permissions = required_permissions
    
    def __call__(
        self, 
        credentials: HTTPAuthorizationCredentials = Depends(security),
        current_user: User = Depends(get_current_user)
    ):
        user_permissions = ROLE_PERMISSIONS.get(current_user.role, [])
        
        for permission in self.required_permissions:
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="权限不足"
                )
        
        return current_user

ROLE_PERMISSIONS = {
    "品质检查员": [
        "inspection:create", "inspection:read", "inspection:update",
        "scoring:read",
        "report:read", "report:export"
    ],
    "质量主管": [
        "inspection:*", "scoring:*", "report:*"
    ],
    "项目人员": [
        "report:read"
    ],
    "系统管理员": [
        "*"
    ]
}
```

### 7.3 API Key管理

```python
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    QWEN_API_KEY: str
    DEEPSEEK_API_KEY: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

**.env文件示例：**
```env
QWEN_API_KEY=sk-xxxxxxxxxxxx
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxx
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

### 7.4 数据安全

| 安全措施 | 说明 |
|---------|------|
| 密码加密 | 使用bcrypt进行密码哈希存储 |
| Token安全 | JWT Token设置合理过期时间，支持主动失效 |
| API Key保护 | 环境变量存储，禁止硬编码 |
| 文件上传限制 | 限制文件类型、大小，防止恶意上传 |
| SQL注入防护 | 使用SQLAlchemy ORM，参数化查询 |
| XSS防护 | 前端输入过滤，后端输出转义 |

---

## 8. 前端技术设计

### 8.1 响应式设计策略

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           响应式设计策略                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         设备检测                                     │   │
│   │                                                                     │   │
│   │   屏幕宽度 < 768px          屏幕宽度 >= 768px                        │   │
│   │        │                           │                                │   │
│   │        ▼                           ▼                                │   │
│   │   ┌─────────────┐           ┌─────────────────┐                     │   │
│   │   │  移动端布局  │           │    PC端布局      │                     │   │
│   │   │  (Vant 4)   │           │  (Element Plus) │                     │   │
│   │   └─────────────┘           └─────────────────┘                     │   │
│   │                                                                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 移动端页面设计

| 页面 | 功能 | 核心组件 |
|------|------|---------|
| 模块选择 | 选择检查模块 | van-grid, van-cell |
| 检查录入 | 填写检查结果 | van-form, van-field, van-uploader |
| 整改提交 | 上传整改材料 | van-uploader, van-datetime-picker |
| 整改验收 | 验收整改结果 | van-card, van-image-preview |
| 报告查看 | 查看检查报告 | van-doc, van-collapse |

### 8.3 PC端页面设计

| 页面 | 功能 | 核心组件 |
|------|------|---------|
| 仪表盘 | 数据概览 | el-card, el-statistic, el-chart |
| 检查管理 | 检查记录列表 | el-table, el-pagination, el-filter |
| 评分管理 | 评分复核 | el-table, el-dialog, el-rate |
| 报告管理 | 报告生成导出 | el-table, el-button, el-download |
| 整改管理 | 整改跟踪 | el-table, el-timeline, el-steps |
| 系统设置 | 用户权限配置 | el-form, el-tree, el-transfer |

### 8.4 前端路由配置

```typescript
const routes = [
  {
    path: '/',
    redirect: '/mobile/modules'
  },
  {
    path: '/mobile',
    component: () => import('@/layouts/MobileLayout.vue'),
    children: [
      { path: 'modules', component: () => import('@/views/mobile/Modules.vue') },
      { path: 'inspection/:id', component: () => import('@/views/mobile/Inspection.vue') },
      { path: 'report/:id', component: () => import('@/views/mobile/Report.vue') }
    ]
  },
  {
    path: '/pc',
    component: () => import('@/layouts/PcLayout.vue'),
    children: [
      { path: 'tasks', component: () => import('@/views/pc/Tasks.vue') },
      { path: 'reports', component: () => import('@/views/pc/Report.vue') },
      { path: 'settings', component: () => import('@/views/pc/Settings.vue') }
    ]
  }
]
```

---

## 9. Agent核心实现

### 9.1 Agent接口设计

#### Agent基类

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseAgent(ABC):
    
    def __init__(self, name: str):
        self.name = name
        self.status = "idle"
    
    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    def get_status(self) -> str:
        return self.status
```

#### Agent 1 接口

```python
class DataCollectionAgent(BaseAgent):
    
    def load_template(self, template_path: str) -> Dict[str, Any]:
        """加载检查表模板"""
        pass
    
    def get_modules(self) -> List[Dict[str, Any]]:
        """获取所有检查模块"""
        pass
    
    def get_check_items(self, module_id: int) -> List[Dict[str, Any]]:
        """获取指定模块的检查项"""
        pass
    
    def record_issue(self, item_id: str, issue: Dict[str, Any]) -> str:
        """记录问题点"""
        pass
    
    def upload_photo(self, issue_id: str, photo_file: bytes) -> str:
        """上传照片"""
        pass
    
    def save_progress(self) -> str:
        """保存检查进度"""
        pass
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行数据采集"""
        pass
```

#### Agent 2 接口

```python
class ScoringAgent(BaseAgent):
    """智能评分Agent - 使用Qwen3.5-plus"""
    
    def __init__(self, qwen_client: QwenClient):
        super().__init__("ScoringAgent")
        self.llm_client = qwen_client
    
    def analyze_issue(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """分析问题点"""
        pass
    
    async def calculate_score(self, item: Dict[str, Any], issues: List[Dict]) -> Dict[str, Any]:
        """计算得分 - 调用Qwen3.5-plus"""
        pass
    
    def generate_scoring_basis(self, item: Dict, issues: List, score: int) -> str:
        """生成评分依据"""
        pass
    
    def generate_improvement_suggestion(self, issues: List[Dict]) -> str:
        """生成改进建议"""
        pass
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行智能评分"""
        pass
```

#### Agent 3 接口

```python
class AnalysisAgent(BaseAgent):
    """总结分析Agent - 使用DeepSeek V3.2"""
    
    def __init__(self, deepseek_client: DeepSeekClient):
        super().__init__("AnalysisAgent")
        self.llm_client = deepseek_client
    
    async def analyze_module(self, module_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析单个模块 - 调用DeepSeek"""
        pass
    
    async def analyze_overall(self, all_modules: List[Dict]) -> Dict[str, Any]:
        """综合分析所有模块"""
        pass
    
    async def generate_report(self, analysis_data: Dict[str, Any]) -> str:
        """生成检查报告 - 调用DeepSeek"""
        pass
    
    def export_report(self, report_data: Dict, format: str) -> str:
        """导出报告"""
        pass
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行总结分析"""
        pass
```

### 9.2 LLM调用接口

```python
import json
from openai import AsyncOpenAI
from typing import Dict, Any, List

class QwenClient:
    """通义千问客户端 - 用于Agent 2智能评分（按模块批量）"""

    def __init__(self, api_key: str, model: str = "qwen-plus"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.base_url
        )

    async def score_module(self, prompt: str) -> Dict[str, Any]:
        """按模块批量评分接口，返回解析后的Dict（修复：原返回str类型错误）"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一名专业的物业品质检查评分专家。请严格按照JSON格式输出。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000,   # 按模块批量，需要更大token
            temperature=0.3
        )
        raw_text: str = response.choices[0].message.content
        return json.loads(raw_text)   # 显式解析为Dict，调用方无需再处理

    async def chat(self, messages: List[Dict], temperature: float = 0.3) -> str:
        """通用对话接口"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content


class DeepSeekClient:
    """DeepSeek客户端 - 用于Agent 3总结分析"""

    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.deepseek.com/v1"
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.base_url
        )

    async def analyze_module(self, prompt: str) -> Dict[str, Any]:
        """模块分析接口，返回解析后的Dict（修复：原返回str类型错误）"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一名资深的物业品质管理专家。请严格按照JSON格式输出。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.3
        )
        raw_text: str = response.choices[0].message.content
        return json.loads(raw_text)   # 显式解析为Dict

    async def generate_report(self, prompt: str) -> str:
        """报告生成接口，返回str（报告为自由文本，不需要解析）"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一名资深的物业品质管理专家，擅长撰写专业的检查报告。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000,
            temperature=0.3
        )
        return response.choices[0].message.content


class DualLLMClient:
    """双LLM客户端管理器"""

    def __init__(self, qwen_api_key: str, deepseek_api_key: str):
        self.qwen_client = QwenClient(qwen_api_key)
        self.deepseek_client = DeepSeekClient(deepseek_api_key)

    def get_scoring_client(self) -> QwenClient:
        """获取评分用LLM客户端 (qwen-plus)"""
        return self.qwen_client

    def get_analysis_client(self) -> DeepSeekClient:
        """获取分析用LLM客户端 (deepseek-chat)"""
        return self.deepseek_client
```

---

## 10. LLM模型配置

### 10.1 模型分配策略

| Agent | 模型ID | 用途 | 选型理由 |
|-------|--------|------|---------|
| Agent 1 (数据采集) | 无LLM | 规则驱动 | 纯数据采集，无需AI推理 |
| Agent 2 (智能评分) | qwen-plus | 按模块批量评分 | 中文理解准确，评分逻辑推理能力强 |
| Agent 3 (总结分析) | deepseek-chat | 模块分析+报告生成 | 长文本处理能力强，报告生成质量高 |

### 10.2 API配置

```python
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    QWEN_API_KEY: str
    DEEPSEEK_API_KEY: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    QWEN_MODEL: str = "qwen-plus"
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

---

## 11. Excel模板列映射

### 11.1 检查表Excel格式规范

检查表模板（`内审检查表V3.0.xlsx`）每个Sheet对应一个检查模块。解析规则如下：

**Sheet命名规范：**
Sheet名称即模块名，如"客户服务"、"安全管理"等，与系统中的 `module_name` 字段一一对应。

**表头行位置：** 第1行为表头，第2行起为数据行。

### 11.2 列名与字段映射表

| Excel列名（表头） | 系统字段 | 类型 | 说明 |
|-----------------|---------|------|------|
| 序号 | `item_id` | str | 检查项唯一编号，如 "1.1", "1.2" |
| 检查点 | `item_name` | str | 检查项名称 |
| 检查标准与依据 | `check_standard` | str | 检查依据（法规/标准） |
| 抽样标准与检查方法 | `check_method` | str | 具体抽样方式和检查操作方法 |
| 评价方法 | `scoring_rule` | str | 评分规则文本，如"完全符合5分，每项不符合扣X分" |
| 权重 | `weight` | float | 权重系数，如 0.0034 |

**解析注意事项：**
1. 合并单元格：遇到合并单元格时，使用 `openpyxl` 的 `merged_cells` 属性拆分并向下填充
2. 空行处理：跳过 `item_id` 为空的行
3. 权重格式：Excel中可能存储为文本或数值，统一转换为 `float`
4. 编码：Excel文件默认UTF-8，无需额外处理

### 11.3 解析代码示例

```python
import openpyxl
from typing import Dict, List, Any

COLUMN_MAP = {
    "序号":          "item_id",
    "检查点":         "item_name",
    "检查标准与依据":  "check_standard",
    "抽样标准与检查方法": "check_method",
    "评价方法":       "scoring_rule",
    "权重":           "weight",
}

def parse_template(file_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    解析检查表Excel模板
    返回: {module_name: [item_dict, ...]}
    """
    wb = openpyxl.load_workbook(file_path, data_only=True)
    result = {}

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        headers = [cell.value for cell in ws[1]]   # 第1行为表头
        col_index = {
            COLUMN_MAP[h]: idx
            for idx, h in enumerate(headers)
            if h in COLUMN_MAP
        }

        items = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            item_id = row[col_index["item_id"]] if "item_id" in col_index else None
            if not item_id:
                continue   # 跳过空行
            item = {field: row[idx] for field, idx in col_index.items()}
            item["weight"] = float(item.get("weight") or 0)
            items.append(item)

        result[sheet_name] = items

    return result
```

---

## 12. 部署方案

### 11.1 后端部署

```bash
cd backend

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env

uvicorn main:app --host 0.0.0.0 --port 8000
```

### 11.2 前端部署

```bash
cd frontend

npm install

npm run build

npm run preview
```

### 12.3 Docker部署

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - QWEN_API_KEY=${QWEN_API_KEY}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
  
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
```

---

## 13. 性能优化

| 优化点 | 策略 |
|-------|------|
| 模板加载 | 首次加载后缓存到内存 |
| LLM调用 | 批量处理，减少调用次数 |
| 照片存储 | 压缩后存储，按日期分目录 |
| 报告生成 | 使用模板引擎，预定义样式 |
| 前端缓存 | 使用Pinia持久化状态 |
| API响应 | 启用Gzip压缩 |

---

## 14. 测试策略

### 13.1 单元测试

- 各Agent核心功能测试
- 数据解析和转换测试
- LLM调用Mock测试
- API接口测试

### 13.2 集成测试

- 完整检查流程测试
- Agent协同测试
- 数据持久化测试
- 前后端集成测试

### 13.3 用户验收测试

- 真实检查场景测试
- 报告质量评估
- 用户反馈收集
- 移动端兼容性测试
