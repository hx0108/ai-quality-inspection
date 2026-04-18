# 物业品质检查多Agent系统 - Agent详细设计文档 (AGENTS)

> **文档定位说明：**
> 本文档（AGENTS.md）为**概念设计文档**，描述各Agent的职责、业务逻辑和数据流。
> 具体的代码接口实现规范以 **TECH_DESIGN.md** 为准，两者不一致时以 TECH_DESIGN.md 为准。

## 1. 文档概述

| 项目名称 | 物业品质检查多Agent系统 |
|---------|----------------------|
| 版本号 | V1.0 |
| 创建日期 | 2026-03-28 |
| 文档状态 | 初稿 |

---

## 2. Agent系统总览

### 2.1 Agent架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Agent System Overview                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         Agent Coordinator                            │   │
│   │                    (负责Agent间的协调与数据传递)                       │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│          ┌─────────────────────────┼─────────────────────────┐              │
│          │                         │                         │              │
│          ▼                         ▼                         ▼              │
│   ┌─────────────┐          ┌─────────────┐          ┌─────────────┐        │
│   │   Agent 1   │  ──────> │   Agent 2   │  ──────> │   Agent 3   │        │
│   │  数据采集    │          │  智能评分    │          │  总结分析    │        │
│   │             │          │(qwen-plus)  │          │(deepseek)   │        │
│   │ 规则驱动     │          │  AI驱动     │          │  AI驱动     │        │
│   │ 无LLM调用   │          │ 按模块批量  │          │  LLM必需    │        │
│   └─────────────┘          └─────────────┘          └─────────────┘        │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │              检查闭环: 数据采集 → 批量评分 → 报告生成                   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Agent对比

| 特性 | Agent 1 | Agent 2 | Agent 3 |
|-----|---------|---------|---------|
| 名称 | DataCollectionAgent | ScoringAgent | AnalysisAgent |
| 类型 | 规则驱动 | AI驱动 | AI驱动 |
| LLM模型 | 无 | qwen-plus | deepseek-chat |
| 执行时机 | 检查阶段 | 全部模块检查完成后，点击"开始评分" | 评分完成后，自动触发 |
| 输入 | 检查任务数据 | 全部模块的检查记录JSON | 评分结果JSON |
| 输出 | 检查记录JSON（每模块一条） | 评分结果JSON（含百分制得分） | 检查报告（Word/PDF） |
| LLM调用次数 | 0 | 8次（每模块1次批量调用） | 9次（8次模块分析+1次综合） |

---

## 3. Agent 1: 数据采集Agent

### 3.1 Agent概述

| 属性 | 描述 |
|-----|------|
| 名称 | DataCollectionAgent |
| 类型 | 规则驱动型Agent |
| 职责 | 检查数据采集、问题记录、照片管理 |
| AI能力 | 无 |

### 3.2 核心功能

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Agent 1: 数据采集Agent                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 功能模块 1: 项目管理                                                    │  │
│  │   • 创建新检查任务                                                      │  │
│  │   • 加载历史检查记录                                                    │  │
│  │   • 项目信息维护                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 功能模块 2: 模板解析                                                    │  │
│  │   • 读取Excel检查表模板                                                 │  │
│  │   • 解析8个检查模块                                                     │  │
│  │   • 逐一提取检查项详情                                                      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 功能模块 3: 检查导航                                                    │  │
│  │   • 模块选择与切换                                                      │  │
│  │   • 检查项顺序展示                                                      │  │
│  │   • 检查进度跟踪                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 功能模块 4: 问题记录                                                    │  │
│  │   • 问题描述录入                                                        │  │
│  │   • 问题位置标记                                                        │  │
│  │   • 照片上传与管理                                                      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 功能模块 5: 数据持久化                                                  │  │
│  │   • 保存检查数据（自动持久化到数据库）                                   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 类设计

```python
class DataCollectionAgent(BaseAgent):
    
    def __init__(self, template_path: str, data_dir: str):
        super().__init__("DataCollectionAgent")
        self.template_path = template_path
        self.data_dir = data_dir
        self.current_record = None
        self.template_data = None
    
    def load_template(self) -> Dict[str, Any]:
        """
        加载检查表模板
        
        Returns:
            包含所有模块和检查项的字典
        """
        pass
    
    def create_record(self, project_info: Dict[str, str]) -> str:
        """
        创建新的检查记录
        
        Args:
            project_info: 项目信息字典
            
        Returns:
            记录ID
        """
        pass
    
    def get_modules(self) -> List[Dict[str, Any]]:
        """
        获取所有检查模块
        
        Returns:
            模块列表
        """
        pass
    
    def get_module_items(self, module_id: int) -> List[Dict[str, Any]]:
        """
        获取指定模块的所有检查项
        
        Args:
            module_id: 模块ID
            
        Returns:
            检查项列表
        """
        pass
    
    def record_issue(
        self, 
        module_id: int, 
        item_id: str, 
        description: str,
        location: str,
        severity: str
    ) -> str:
        """
        记录问题点
        
        Args:
            module_id: 模块ID
            item_id: 检查项ID
            description: 问题描述
            location: 问题位置
            severity: 严重程度
            
        Returns:
            问题ID
        """
        pass
    
    def upload_photo(
        self, 
        issue_id: str, 
        photo_data: bytes, 
        filename: str
    ) -> str:
        """
        上传问题照片
        
        Args:
            issue_id: 问题ID
            photo_data: 照片二进制数据
            filename: 文件名
            
        Returns:
            照片存储路径
        """
        pass
    
    def update_item_status(
        self, 
        module_id: int, 
        item_id: str, 
        status: str
    ) -> None:
        """
        更新检查项状态
        
        Args:
            module_id: 模块ID
            item_id: 检查项ID
            status: 状态 (pending/checked/skipped)
        """
        pass
    
    def save_progress(self) -> str:
        """
        保存检查进度
        
        Returns:
            保存的文件路径
        """
        pass
    
    def load_progress(self, record_id: str) -> Dict[str, Any]:
        """
        加载检查进度
        
        Args:
            record_id: 记录ID
            
        Returns:
            检查记录数据
        """
        pass
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """
        获取检查进度摘要
        
        Returns:
            进度摘要数据
        """
        pass
    
    def export_record(self, format: str = "json") -> str:
        """
        导出检查记录
        
        Args:
            format: 导出格式
            
        Returns:
            导出文件路径
        """
        pass
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行数据采集
        
        Args:
            input_data: 输入数据
            
        Returns:
            检查记录数据
        """
        pass
```

### 3.4 数据流转

```
输入:
┌─────────────────────────────────────────────────────────────────┐
│ 检查表模板 (Excel)                                               │
│ └── 内审检查表模板V2.0.xlsx                                      │
│     ├── 客户服务 (Sheet)                                         │
│     ├── 安全管理 (Sheet)                                         │
│     └── ...                                                      │
└─────────────────────────────────────────────────────────────────┘

处理:
┌─────────────────────────────────────────────────────────────────┐
│ 1. 解析Excel模板                                                 │
│    • 读取所有Sheet                                               │
│    • 提取所有Sheet内的检查项数据                                    │
│                                                                 │
│ 2. 用户交互采集                                                   │
│    • 选择模块                                                    │
│    • 逐项检查                                                    │
│    • 记录问题                                                    │
│    • 上传照片                                                    │
│                                                                 │
│ 3. 数据组织                                                      │
│    • 构建检查记录结构                                             │
│    • 关联照片文件                                                │
└─────────────────────────────────────────────────────────────────┘

输出:
┌─────────────────────────────────────────────────────────────────┐
│ 检查记录 (JSON)                                                  │
│ {                                                               │
│   "record_id": "REC-20260326-001",                              │
│   "project_info": {...},                                        │
│   "modules": [                                                  │
│     {                                                           │
│       "module_name": "客户服务",                                 │
│       "items": [                                                │
│         {                                                       │
│           "item_id": "1.1",                                     │
│           "issues": [...]                                       │
│         }                                                       │
│       ]                                                         │
│     }                                                           │
│   ]                                                             │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

### 3.5 状态管理

```
检查项状态流转:

  ┌─────────┐      开始检查      ┌─────────┐      完成检查      ┌─────────┐
  │ pending │ ────────────────> │checking │ ────────────────> │ checked │
  │ (待检)  │                    │ (检查中) │                    │ (已检)  │
  └─────────┘                    └─────────┘                    └─────────┘
       │                              │
       │ 跳过检查                      │ 跳过检查
       │                              │
       ▼                              ▼
  ┌─────────┐                   ┌─────────┐
  │ skipped │                   │ skipped │
  │ (已跳过) │                   │ (已跳过) │
  └─────────┘                   └─────────┘


模块状态:

  ┌─────────────┐     开始检查     ┌─────────────┐     完成检查     ┌─────────────┐
  │ not_started │ ─────────────> │ in_progress │ ─────────────> │  completed  │
  │   (未开始)   │                 │   (进行中)   │                 │   (已完成)   │
  └─────────────┘                 └─────────────┘                 └─────────────┘
```

---

## 4. Agent 2: 智能评分Agent

### 4.1 Agent概述

| 属性 | 描述 |
|-----|------|
| 名称 | ScoringAgent |
| 类型 | AI驱动型Agent |
| 职责 | 在检查完成后，统一进行批量智能评分 |
| AI能力 | LLM推理、评分规则理解 |
| 执行时机 | 检查人员完成所有模块检查后，点击"开始评分"按钮触发 |

**评分模式说明：**
采用"检查完成后统一评分"模式，检查人员在现场完成所有模块的检查、问题记录和照片上传后，系统统一调用AI进行批量评分。

**评分时机优势：**
| 优势 | 说明 |
|------|------|
| AI评分更准确 | 完整上下文，AI可综合判断同一类别下所有问题 |
| 用户体验更好 | 检查流程不中断，支持离线检查 |
| 成本更低 | API调用次数减少，按模块批量处理 |
| 便于复核 | 统一评分后可整体把控，提高复核效率 |

### 4.2 核心功能

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Agent 2: 智能评分Agent                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 功能模块 1: 评分规则解析                                                │  │
│  │   • 解析评分标准文本                                                    │  │
│  │   • 提取评分条件                                                        │  │
│  │   • 理解扣分逻辑                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 功能模块 2: 问题分析                                                    │  │
│  │   • 分析问题描述                                                        │  │
│  │   • 判断问题严重程度                                                    │  │
│  │   • 关联评分规则                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 功能模块 3: 批量智能评分                                               │  │
│  │   • 按模块批量调用LLM进行评分推理                                       │  │
│  │   • 计算每个检查项的评价得分                                            │  │
│  │   • 计算权重后的总得分                                                  │  │
│  │   • 生成评分依据                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 类设计

```python
class ScoringAgent(BaseAgent):
    
    def __init__(self, llm_client: LLMClient):
        super().__init__("ScoringAgent")
        self.llm_client = llm_client
        self.scoring_results = []
    
    def parse_scoring_rule(self, rule_text: str) -> Dict[str, Any]:
        """
        解析评分规则
        
        Args:
            rule_text: 评分规则文本
            
        Returns:
            解析后的评分规则结构
        """
        pass
    
    def analyze_issue(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析问题点
        
        Args:
            issue: 问题数据
            
        Returns:
            问题分析结果
        """
        pass
    
    def calculate_score(
        self, 
        item: Dict[str, Any], 
        issues: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        计算检查项得分
        
        Args:
            item: 检查项数据
            issues: 问题列表
            
        Returns:
            评分结果
        """
        pass
    
    def build_scoring_prompt(
        self, 
        item: Dict[str, Any], 
        issues: List[Dict[str, Any]]
    ) -> str:
        """
        构建评分Prompt
        
        Args:
            item: 检查项数据
            issues: 问题列表
            
        Returns:
            Prompt字符串
        """
        pass
    
    def call_llm_for_scoring(self, prompt: str) -> Dict[str, Any]:
        """
        调用LLM进行评分
        
        Args:
            prompt: Prompt字符串
            
        Returns:
            LLM返回的评分结果
        """
        pass
    
    def generate_scoring_basis(
        self, 
        item: Dict[str, Any],
        issues: List[Dict[str, Any]],
        score: int
    ) -> str:
        """
        生成评分依据
        
        Args:
            item: 检查项数据
            issues: 问题列表
            score: 得分
            
        Returns:
            评分依据文本
        """
        pass
    
    def generate_improvement_suggestion(
        self, 
        issues: List[Dict[str, Any]]
    ) -> str:
        """
        生成改进建议
        
        Args:
            issues: 问题列表
            
        Returns:
            改进建议文本
        """
        pass
    
    def score_all_items(
        self, 
        record_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        对所有检查项进行评分
        
        Args:
            record_data: 检查记录数据
            
        Returns:
            所有评分结果列表
        """
        pass
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行智能评分
        
        Args:
            input_data: 包含检查记录的输入数据
            
        Returns:
            包含评分结果的数据
        """
        pass
```

### 4.4 Prompt模板设计

> **设计说明：** Agent 2 采用**按模块批量评分**模式，每个模块一次LLM调用，将该模块所有检查项的评分任务打包发送，减少API调用次数（8次模块调用 vs 432次逐项调用）。

#### 批量评分Prompt模板（按模块）

```
你是一名专业的物业品质检查评分专家。请对以下【{module_name}】模块的所有检查项进行评分。

【评分规则说明】
- 每个检查项的评价得分范围为 0-5 分
- 严格按照每个检查项对应的"评价方法"进行评分
- 若检查项标记为"跳过"（skipped），直接给5分（满分）
- 输出必须是合法的JSON数组格式

【检查项列表】
{items_json}

其中每个检查项的结构为：
{{
  "item_id": "检查项编号",
  "item_name": "检查项名称",
  "check_method": "抽样标准与检查方法",
  "scoring_rule": "评价方法（如：完全符合5分，每项不符合扣X分）",
  "issues": [  // 空列表表示无问题
    {{"description": "问题描述", "severity": "严重/一般/轻微"}}
  ],
  "is_skipped": false  // true时直接给5分
}}

【输出格式】（JSON数组，与输入items顺序一一对应）
[
  {{
    "item_id": "<与输入一致>",
    "score": <0-5的整数或小数>,
    "scoring_basis": "<简要说明评分依据>",
    "improvement_suggestion": "<针对问题的改进建议，无问题时填'符合要求'>"
  }},
  ...
]
```

#### 示例

```
输入（部分）:
模块名称：客户服务
检查项：
[
  {
    "item_id": "1.2",
    "item_name": "管家手机配置",
    "check_method": "现场核查手机品牌、配置及运行状态",
    "scoring_rule": "完全符合要求，评5分；每出现1项不符合扣2分；均不符合要求评0分。",
    "issues": [{"description": "管家手机存在卡顿现象，影响正常使用", "severity": "一般"}],
    "is_skipped": false
  }
]

输出:
[
  {
    "item_id": "1.2",
    "score": 3,
    "scoring_basis": "根据评分规则，完全符合评5分，每出现1项不符合扣2分。发现手机卡顿1项不符合，扣2分，最终得分3分。",
    "improvement_suggestion": "建议对卡顿手机进行系统优化或更换设备，确保管家能及时响应业主需求。"
  }
]
```

### 4.5 数据流转

```
输入 (来自Agent 1):
┌─────────────────────────────────────────────────────────────────┐
│ 检查记录 JSON                                                    │
│ {                                                               │
│   "modules": [                                                  │
│     {                                                           │
│       "module_name": "客户服务",                                 │
│       "items": [                                                │
│         {                                                       │
│           "item_id": "1.1",                                     │
│           "item_name": "管家手机配置",                           │
│           "scoring_rule": "完全符合5分...",                      │
│           "issues": [                                           │
│             {                                                   │
│               "description": "手机卡顿",                        │
│               "severity": "一般"                                │
│             }                                                   │
│           ]                                                     │
│         }                                                       │
│       ]                                                         │
│     }                                                           │
│   ]                                                             │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘

处理:
┌─────────────────────────────────────────────────────────────────┐
│ 1. 遍历所有检查项                                                │
│                                                                 │
│ 2. 对每个检查项:                                                 │
│    a. 解析评分规则                                               │
│    b. 分析问题点                                                 │
│    c. 构建Prompt                                                 │
│    d. 调用LLM                                                    │
│    e. 解析返回结果                                               │
│    f. 存储评分结果                                               │
│                                                                 │
│ 3. 汇总所有评分结果                                              │
└─────────────────────────────────────────────────────────────────┘

输出:
┌─────────────────────────────────────────────────────────────────┐
│ 评分结果 JSON                                                    │
│ {                                                               │
│   "scoring_results": [                                          │
│     {                                                           │
│       "module_id": 1,                                           │
│       "item_id": "1.1",                                         │
│       "score": 3,                                               │
│       "max_score": 5,                                           │
│       "scoring_basis": "根据评分规则...",                        │
│       "improvement_suggestion": "建议..."                        │
│     }                                                           │
│   ],                                                            │
│   "summary": {                                                  │
│     "total_score": 85,                                          │
│     "max_score": 100                                            │
│   }                                                             │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Agent 3: 总结分析Agent

### 5.1 Agent概述

| 属性 | 描述 |
|-----|------|
| 名称 | AnalysisAgent |
| 类型 | AI驱动型Agent |
| 职责 | 模块分析、综合分析、报告生成 |
| AI能力 | LLM推理、报告撰写 |

### 5.2 核心功能

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Agent 3: 总结分析Agent                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 功能模块 1: 模块级分析 (执行8次)                                        │  │
│  │   • 分析模块得分情况                                                    │  │
│  │   • 统计问题分布                                                        │  │
│  │   • 识别关键问题                                                        │  │
│  │   • 生成模块改进建议                                                    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 功能模块 2: 项目级综合分析 (执行1次)                                     │  │
│  │   • 汇总各模块分析结果                                                  │  │
│  │   • 计算总体得分                                                        │  │
│  │   • 识别重点问题                                                        │  │
│  │   • 生成综合改进建议                                                    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 功能模块 3: 报告生成                                                    │  │
│  │   • 组织报告结构                                                        │  │
│  │   • 填充分析内容                                                        │  │
│  │   • 生成问题清单                                                        │  │
│  │   • 添加改进建议                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 功能模块 4: 报告导出                                                    │  │
│  │   • 导出Word格式                                                        │  │
│  │   • 导出PDF格式                                                         │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 类设计

```python
class AnalysisAgent(BaseAgent):
    
    def __init__(self, llm_client: LLMClient):
        super().__init__("AnalysisAgent")
        self.llm_client = llm_client
        self.module_analyses = []
        self.final_report = None
    
    def analyze_module(
        self, 
        module_data: Dict[str, Any], 
        scoring_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析单个模块
        
        Args:
            module_data: 模块数据
            scoring_results: 该模块的评分结果
            
        Returns:
            模块分析结果
        """
        pass
    
    def build_module_analysis_prompt(
        self, 
        module_data: Dict[str, Any], 
        scoring_results: List[Dict[str, Any]]
    ) -> str:
        """
        构建模块分析Prompt
        
        Args:
            module_data: 模块数据
            scoring_results: 评分结果
            
        Returns:
            Prompt字符串
        """
        pass
    
    def analyze_all_modules(
        self, 
        record_data: Dict[str, Any], 
        scoring_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        分析所有模块
        
        Args:
            record_data: 检查记录数据
            scoring_data: 评分数据
            
        Returns:
            所有模块分析结果列表
        """
        pass
    
    def analyze_overall(
        self, 
        module_analyses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        综合分析所有模块
        
        Args:
            module_analyses: 所有模块分析结果
            
        Returns:
            综合分析结果
        """
        pass
    
    def build_overall_analysis_prompt(
        self, 
        module_analyses: List[Dict[str, Any]]
    ) -> str:
        """
        构建综合分析Prompt
        
        Args:
            module_analyses: 模块分析结果
            
        Returns:
            Prompt字符串
        """
        pass
    
    def identify_priority_issues(
        self, 
        module_analyses: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        识别重点问题
        
        Args:
            module_analyses: 模块分析结果
            
        Returns:
            重点问题列表
        """
        pass
    
    def generate_report(
        self, 
        record_data: Dict[str, Any],
        scoring_data: Dict[str, Any],
        analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成检查报告
        
        Args:
            record_data: 检查记录数据
            scoring_data: 评分数据
            analysis_data: 分析数据
            
        Returns:
            报告数据
        """
        pass
    
    def export_to_word(
        self, 
        report_data: Dict[str, Any], 
        output_path: str
    ) -> str:
        """
        导出Word格式报告
        
        Args:
            report_data: 报告数据
            output_path: 输出路径
            
        Returns:
            文件路径
        """
        pass
    
    def export_to_pdf(
        self, 
        report_data: Dict[str, Any], 
        output_path: str
    ) -> str:
        """
        导出PDF格式报告
        
        Args:
            report_data: 报告数据
            output_path: 输出路径
            
        Returns:
            文件路径
        """
        pass
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行总结分析
        
        Args:
            input_data: 包含检查记录和评分结果的输入数据
            
        Returns:
            包含报告数据的结果
        """
        pass
```

### 5.4 Prompt模板设计

#### 模块分析Prompt模板

```
你是一名专业的物业品质检查分析专家。请对以下模块的检查情况进行分析。

【模块信息】
模块名称：{module_name}
检查项数量：{total_items}
已检查数量：{checked_items}

【评分情况】
模块得分：{module_score}/{module_max_score}
得分率：{score_rate}%

【各检查项得分明细】
{items_score_details}

【各检查问题汇总】
{issues_summary}

【分析要求】
请从以下几个方面进行分析：
1. 模块整体表现评价
2. 主要问题分析
3. 改进建议

【输出格式】
{{
    "overall_evaluation": "<整体表现评价>",
    "main_issues": ["<主要问题1>", "<主要问题2>"],
    "severity_distribution": {{
        "严重": <数量>,
        "一般": <数量>,
        "轻微": <数量>
    }},
    "improvement_suggestions": ["<建议1>", "<建议2>"]
}}
```

#### 综合分析Prompt模板

```
你是一名专业的物业品质检查分析专家。请根据各模块的分析结果，生成项目综合检查报告。

【项目信息】
项目名称：{project_name}
检查日期：{check_date}
检查人员：{inspector}

【总体得分】
总分：{total_score}/{max_score}
得分率：{score_rate}%

【各模块分析结果】
{module_analyses_text}

【分析要求】
请生成完整的检查报告，包含以下内容：

一、检查概况
   - 检查基本信息
   - 总体得分情况

二、各模块检查情况
   - 模块得分排名
   - 各模块详细分析

三、重点问题清单
   - 严重问题（需立即整改）
   - 一般问题（限期整改）

四、整改建议
   - 短期整改措施
   - 长期提升建议

【输出格式】
输出完整的报告文本。
```

### 5.5 数据流转

```
输入 (来自Agent 2):
┌─────────────────────────────────────────────────────────────────┐
│ 评分结果 JSON                                                    │
│ {                                                               │
│   "record_data": {...},                                         │
│   "scoring_results": [...]                                      │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘

处理:
┌─────────────────────────────────────────────────────────────────┐
│ 第一次分析: 模块级分析 (循环8次)                                  │
│                                                                 │
│ For each module:                                                │
│   1. 提取模块数据                                                │
│   2. 提取该模块评分结果                                          │
│   3. 构建分析Prompt                                              │
│   4. 调用LLM                                                     │
│   5. 存储模块分析结果                                            │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ 第二次分析: 项目级综合分析 (执行1次)                              │
│                                                                 │
│ 1. 汇总8个模块分析结果                                           │
│ 2. 计算总体得分                                                  │
│ 3. 识别重点问题                                                  │
│ 4. 构建综合分析Prompt                                            │
│ 5. 调用LLM生成报告                                               │
│ 6. 格式化报告内容                                                │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ 报告导出                                                         │
│                                                                 │
│ 1. 生成Word文档                                                  │
│ 2. 嵌入问题照片                                                  │
│ 3. 保存报告文件                                                  │
└─────────────────────────────────────────────────────────────────┘

输出:
┌─────────────────────────────────────────────────────────────────┐
│ 检查报告文件                                                     │
│ └── reports/RPT-20260326-001.docx                               │
│                                                                 │
│ 报告数据 JSON                                                    │
│ {                                                               │
│   "report_id": "RPT-20260326-001",                              │
│   "summary": {...},                                             │
│   "module_analyses": [...],                                     │
│   "overall_analysis": {...},                                    │
│   "report_file_path": "reports/RPT-20260326-001.docx"           │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Agent协同机制

### 6.1 协同流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Agent协同流程                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 阶段 1: 数据采集 (Agent 1)                                           │   │
│  │                                                                     │   │
│  │   用户操作 → Agent 1 处理 → 生成检查记录JSON（每模块一条）            │   │
│  │                                                                     │   │
│  │   完成条件: 全部模块检查完成（8人各自提交，汇聚到同一检查任务）        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    │ 传递检查记录                           │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 阶段 2: 智能评分 (Agent 2) - 检查完成后统一评分                      │   │
│  │                                                                     │   │
│  │   用户点击"开始评分" → Agent 2 处理:                                 │   │
│  │     1. 按模块批量调用LLM进行评分（8次调用）                          │   │
│  │     2. 跳过项（skipped）自动给满分5分                                │   │
│  │     3. 应用权重计算模块百分制得分及项目总分                          │   │
│  │   → 生成评分结果JSON                                                │   │
│  │                                                                     │   │
│  │   完成条件: 所有模块（8个）评分完成                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    │ 传递评分结果                           │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 阶段 3: 总结分析 (Agent 3)                                           │   │
│  │                                                                     │   │
│  │   评分结果 → Agent 3 处理:                                          │   │
│  │     1. 模块分析 (8次LLM调用)                                        │   │
│  │     2. 综合分析 (1次LLM调用)                                        │   │
│  │     3. 报告生成并导出                                               │   │
│  │   → 生成检查报告文件                                                │   │
│  │                                                                     │   │
│  │   完成条件: 报告生成并导出                                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              完整检查闭环: 数据采集 → 批量评分 → 报告生成              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 数据传递格式

```python
class AgentCoordinator:

    def __init__(self):
        self.agent1 = DataCollectionAgent(template_path, data_dir)
        self.agent2 = ScoringAgent(llm_client)
        self.agent3 = AnalysisAgent(llm_client)
        self.current_data = {}

    def run_data_collection(self, project_info: Dict) -> Dict:
        """运行Agent 1"""
        result = self.agent1.execute({
            "action": "collect",
            "project_info": project_info
        })
        self.current_data["record"] = result
        return result

    def run_scoring(self) -> Dict:
        """运行Agent 2"""
        result = self.agent2.execute({
            "record_data": self.current_data["record"]
        })
        self.current_data["scoring"] = result
        return result

    def run_analysis(self) -> Dict:
        """运行Agent 3"""
        result = self.agent3.execute({
            "record_data": self.current_data["record"],
            "scoring_data": self.current_data["scoring"]
        })
        self.current_data["report"] = result
        return result

    def run_full_pipeline(self, project_info: Dict) -> Dict:
        """运行完整3-Agent流程"""
        self.run_data_collection(project_info)
        self.run_scoring()
        return self.run_analysis()
```

---

## 7. 错误处理

### 7.1 Agent 1 错误处理

| 错误类型 | 处理方式 |
|---------|---------|
| 模板文件不存在 | 提示用户选择正确的模板文件 |
| 模板格式错误 | 提示模板格式不符合要求 |
| 照片上传失败 | 提示重新上传，支持重试 |
| 数据保存失败 | 自动重试，提示用户检查磁盘空间 |

### 7.2 Agent 2 错误处理

| 错误类型 | 处理方式 |
|---------|---------|
| LLM调用超时 | 自动重试，最多3次 |
| LLM返回格式错误 | 解析失败时使用默认评分逻辑 |
| API Key无效 | 提示用户检查API配置 |

### 7.3 Agent 3 错误处理

| 错误类型 | 处理方式 |
|---------|---------|
| LLM调用超时 | 自动重试，最多3次 |
| 报告生成失败 | 使用模板生成基础报告 |
| 文件导出失败 | 提示用户检查文件权限 |

---

## 8. 扩展性设计

### 8.1 新增检查模块

系统支持动态添加新的检查模块：

1. 在Excel模板中添加新的Sheet
2. Agent 1自动识别并加载新模块
3. 无需修改代码

### 8.2 新增Agent

系统支持扩展新的Agent：

```python
class CustomAgent(BaseAgent):
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

coordinator.add_agent("custom", CustomAgent())
```

### 8.3 切换LLM

系统支持切换不同的LLM：

```python
class LLMClient:
    
    def __init__(self, provider: str, api_key: str):
        if provider == "qwen":
            self.client = QwenClient(api_key)
        elif provider == "openai":
            self.client = OpenAIClient(api_key)
```

