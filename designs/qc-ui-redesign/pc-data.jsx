// pc-data.jsx —— 演示数据（形态对齐真实 API 字段，数值为编造）
const D = {};

D.user = { name: "贺星", role: "admin", roleName: "系统管理员" };

D.projects = [
  "云鹭湾", "翡翠公园", "梧桐郡", "澜山府", "蝶城·虹桥", "星河印",
];

D.modules = [
  "客户服务", "安全管理", "EHS及风险管理", "环境管理",
  "机电运维", "设施维护", "综合管理", "财务管理",
];

// 概览 KPI（字段与后端 summary 一致）
D.summary = {
  total_tasks: 47,
  pending_tasks: 3,
  in_progress_tasks: 6,
  coverage_rate: 83,
  monthly_checked_projects: 5,
  total_projects: 6,
  total_issues: 102,
  serious_issues: 9,
  general_issues: 93,
  pending_rectifications: 18,
  submitted_rectifications: 11,
  rectification_rate: 64,
  approved_rectifications: 32,
  score_avg: 4.2,
  score_prev: 4.0,
};

// 项目 × 模块 得分（最新一次检查）
D.projectScores = [
  { project_name: "云鹭湾",   modules: { "客户服务": 4.6, "安全管理": 4.8, "EHS及风险管理": 4.2, "环境管理": 4.5, "机电运维": 3.8, "设施维护": 4.1, "综合管理": 4.4, "财务管理": 4.7 }, latest_score: 4.4, checked_at: "09-08" },
  { project_name: "翡翠公园", modules: { "客户服务": 4.1, "安全管理": 4.5, "EHS及风险管理": 3.9, "环境管理": 4.2, "机电运维": 4.4, "设施维护": 4.0, "综合管理": 4.3, "财务管理": 4.2 }, latest_score: 4.2, checked_at: "09-07" },
  { project_name: "梧桐郡",   modules: { "客户服务": 3.8, "安全管理": 4.2, "EHS及风险管理": 3.4, "环境管理": 3.9, "机电运维": 3.2, "设施维护": 3.6, "综合管理": 4.0, "财务管理": 4.1 }, latest_score: 3.8, checked_at: "09-05" },
  { project_name: "澜山府",   modules: { "客户服务": 4.3, "安全管理": 4.0, "EHS及风险管理": 4.4, "环境管理": 3.7, "机电运维": null, "设施维护": 3.9, "综合管理": 4.1, "财务管理": 3.8 }, latest_score: 4.0, checked_at: "09-03" },
  { project_name: "蝶城·虹桥", modules: { "客户服务": 3.5, "安全管理": 3.9, "EHS及风险管理": 3.6, "环境管理": 3.3, "机电运维": 3.5, "设施维护": 3.1, "综合管理": 3.8, "财务管理": null }, latest_score: 3.5, checked_at: "08-30" },
  { project_name: "星河印",   modules: null, latest_score: null, checked_at: null },
];

// 问题按模块分布（含严重拆分）
D.issueByModule = [
  { module: "机电运维",   total: 26, serious: 4 },
  { module: "安全管理",   total: 21, serious: 3 },
  { module: "环境管理",   total: 18, serious: 1 },
  { module: "设施维护",   total: 15, serious: 1 },
  { module: "客户服务",   total: 11, serious: 0 },
  { module: "综合管理",   total: 7,  serious: 0 },
  { module: "EHS及风险管理", total: 4, serious: 0 },
].sort((a, b) => b.total - a.total);

// 各项目整改完成率
D.rectByProject = [
  { project: "云鹭湾",   ok: 24, pending: 4,  over: 0 },
  { project: "翡翠公园", ok: 19, pending: 6,  over: 1 },
  { project: "梧桐郡",   ok: 15, pending: 9,  over: 2 },
  { project: "澜山府",   ok: 12, pending: 5,  over: 1 },
  { project: "蝶城·虹桥", ok: 7,  pending: 10, over: 2 },
];

// 近 8 周平均分趋势
D.trend = [3.9, 3.8, 4.0, 4.1, 3.9, 4.2, 4.3, 4.2];
D.trendLabels = ["W32", "W33", "W34", "W35", "W36", "W37", "W38", "W39"];

// 任务列表（任务中心页用）
D.tasks = [
  { id: "T-240910-01", project: "云鹭湾", inspector: "李国栋", modules: 8, items: 96, score: 4.4, status: "scored",   created: "09-08", serious: 2, general: 12 },
  { id: "T-240907-03", project: "翡翠公园", inspector: "王敏", modules: 8, items: 96, score: 4.2, status: "scored",   created: "09-07", serious: 1, general: 15 },
  { id: "T-240905-02", project: "梧桐郡", inspector: "赵成", modules: 8, items: 96, score: 3.8, status: "rectifying", created: "09-05", serious: 4, general: 21 },
  { id: "T-240903-01", project: "澜山府", inspector: "李国栋", modules: 6, items: 72, score: 4.0, status: "rectifying", created: "09-03", serious: 3, general: 14 },
  { id: "T-240901-04", project: "蝶城·虹桥", inspector: "陈璐", modules: 8, items: 96, score: 3.5, status: "reported",  created: "08-30", serious: 5, general: 19 },
  { id: "T-240830-02", project: "星河印", inspector: "—", modules: 0, items: 0, score: null, status: "pending",  created: "—", serious: 0, general: 0 },
  { id: "T-240828-01", project: "云鹭湾", inspector: "王敏", modules: 8, items: 96, score: 4.1, status: "done",     created: "08-28", serious: 3, general: 16 },
];

D.statusMeta = {
  pending:    { label: "待处理", cls: "kt-muted" },
  inspecting: { label: "检查中", cls: "kt-brand" },
  scored:     { label: "已评分", cls: "kt-brand" },
  rectifying: { label: "整改中", cls: "kt-warn" },
  reported:   { label: "已报告", cls: "kt-ok" },
  done:       { label: "已归档", cls: "kt-muted" },
};

// ===== 以下为 A2 页面数据 =====

// 评分复核
D.scoring = [
  { id: "SR-2409-011", task: "T-240910-01", project: "云鹭湾", inspector: "李国栋", ai_score: 4.4, human_score: null, diff: null, status: "pending_review", time: "09-10 09:12", serious: 2 },
  { id: "SR-2409-010", task: "T-240907-03", project: "翡翠公园", inspector: "王敏", ai_score: 4.2, human_score: 4.3, diff: 0.1, status: "reviewed", time: "09-09 15:40", serious: 1 },
  { id: "SR-2409-009", task: "T-240905-02", project: "梧桐郡", inspector: "赵成", ai_score: 3.8, human_score: 3.5, diff: 0.3, status: "reviewed", time: "09-08 11:05", serious: 4 },
  { id: "SR-2409-008", task: "T-240903-01", project: "澜山府", inspector: "李国栋", ai_score: 4.0, human_score: 4.0, diff: 0.0, status: "reviewed", time: "09-06 17:22", serious: 3 },
  { id: "SR-2409-007", task: "T-240901-04", project: "蝶城·虹桥", inspector: "陈璐", ai_score: 3.5, human_score: 3.1, diff: 0.4, status: "disputed", time: "09-04 10:48", serious: 5 },
];
D.scoringMeta = {
  pending_review: { label: "待复核", cls: "kt-warn" },
  reviewed: { label: "已复核", cls: "kt-ok" },
  disputed: { label: "有争议", cls: "kt-err" },
};

// 报告
D.reports = [
  { id: "R-240910", title: "云鹭湾 9 月品质检查报告", project: "云鹭湾", score: 4.4, modules: 8, status: "ready", created: "09-10 09:30", gen_sec: 96 },
  { id: "R-240907", title: "翡翠公园 9 月品质检查报告", project: "翡翠公园", score: 4.2, modules: 8, status: "ready", created: "09-07 16:10", gen_sec: 88 },
  { id: "R-240905", title: "梧桐郡 9 月品质检查报告", project: "梧桐郡", score: 3.8, modules: 8, status: "ready", created: "09-05 14:45", gen_sec: 103 },
  { id: "R-240903", title: "澜山府 9 月专项检查报告", project: "澜山府", score: 4.0, modules: 6, status: "generating", created: "09-03 10:20", gen_sec: 0 },
  { id: "R-240828", title: "云鹭湾 8 月品质检查报告", project: "云鹭湾", score: 4.1, modules: 8, status: "ready", created: "08-28 15:00", gen_sec: 91 },
];
D.reportMeta = { ready: { label: "已生成", cls: "kt-ok" }, generating: { label: "生成中", cls: "kt-brand" }, failed: { label: "生成失败", cls: "kt-err" } };

// 整改
D.rects = [
  { id: "RC-1024", project: "梧桐郡", module: "机电运维", item: "3.2 电梯机房维保记录", severity: "serious", status: "overdue", assignee: "赵成", created: "09-05", due: "09-12", photos: 2 },
  { id: "RC-1023", project: "蝶城·虹桥", module: "设施维护", item: "6.1 消防通道堆物", severity: "serious", status: "submitted", assignee: "陈璐", created: "08-30", due: "09-10", photos: 3 },
  { id: "RC-1022", project: "翡翠公园", module: "安全管理", item: "2.4 监控盲区", severity: "general", status: "submitted", assignee: "王敏", created: "09-07", due: "09-17", photos: 1 },
  { id: "RC-1021", project: "云鹭湾", module: "环境管理", item: "4.3 垃圾清运不及时", severity: "general", status: "approved", assignee: "李国栋", created: "09-02", due: "09-09", photos: 2 },
  { id: "RC-1020", project: "澜山府", module: "客户服务", item: "1.3 工单闭环超时", severity: "general", status: "approved", assignee: "周航", created: "08-29", due: "09-05", photos: 1 },
];
D.rectMeta = {
  pending: { label: "待整改", cls: "kt-muted" },
  submitted: { label: "已提交待核查", cls: "kt-warn" },
  approved: { label: "已通过", cls: "kt-ok" },
  overdue: { label: "已逾期", cls: "kt-err" },
  disputed: { label: "申诉中", cls: "kt-brand" },
};
D.rectKpi = { pending: 18, submitted: 11, approved: 32, overdue: 5, disputed: 2 };

// 分析看板
D.analysis = {
  cross: [
    { project: "云鹭湾", score: 4.4, issues: 18, rect_rate: 86 },
    { project: "翡翠公园", score: 4.2, issues: 22, rect_rate: 73 },
    { project: "澜山府", score: 4.0, issues: 17, rect_rate: 67 },
    { project: "梧桐郡", score: 3.8, issues: 31, rect_rate: 58 },
    { project: "蝶城·虹桥", score: 3.5, issues: 34, rect_rate: 37 },
  ],
  period: [
    { month: "5月", avg: 3.7 }, { month: "6月", avg: 3.9 }, { month: "7月", avg: 3.8 },
    { month: "8月", avg: 4.0 }, { month: "9月", avg: 4.2 },
  ],
  radar: { axes: D.modules, series: [
    { name: "本项目 云鹭湾", color: "var(--chart-1)", values: [4.6, 4.8, 4.2, 4.5, 3.8, 4.1, 4.4, 4.7] },
    { name: "项目均值", color: "var(--ink-300)", values: [4.06, 4.23, 3.9, 3.92, 3.73, 3.74, 4.12, 4.2] },
  ] },
  insights: [
    "机电运维连续 3 个月为问题最集中模块，占全部问题 25%，建议专项治理电梯机房维保。",
    "蝶城·虹桥整改完成率 37% 显著低于均值 64%，主因是设施维护类问题人力不足。",
    "9 月平均分 4.2 创近 5 个月新高，其中安全管理提升最快（+0.3）。",
  ],
};

// 模型监控
D.llm = {
  kpi: { calls_24h: 1284, success_rate: 99.1, avg_latency: 3.2, tokens_24h: "2.4M", failed_24h: 12 },
  trend: [52, 61, 58, 73, 69, 84, 92, 88, 96, 104, 99, 112],
  trendLabels: ["00","02","04","06","08","10","12","14","16","18","20","22"],
  byAgent: [
    { name: "评分 Agent（Qwen-Plus）", share: 58, latency: 2.1 },
    { name: "整改核查 Agent（Qwen-VL）", share: 22, latency: 4.6 },
    { name: "报告 Agent（DeepSeek）", share: 12, latency: 18.3 },
    { name: "分析 Agent（DeepSeek）", share: 8, latency: 22.8 },
  ],
  logs: [
    { time: "09-10 22:41", agent: "评分", model: "qwen-plus", tokens: 1830, latency: 2.0, status: "ok" },
    { time: "09-10 22:38", agent: "整改核查", model: "qwen-vl-max", tokens: 4210, latency: 4.4, status: "ok" },
    { time: "09-10 22:31", agent: "报告", model: "deepseek-chat", tokens: 12800, latency: 17.9, status: "ok" },
    { time: "09-10 22:24", agent: "评分", model: "qwen-plus", tokens: 1755, latency: 2.3, status: "retry" },
    { time: "09-10 22:18", agent: "分析", model: "deepseek-chat", tokens: 15400, latency: 0, status: "failed" },
  ],
};
D.llmLogMeta = { ok: { label: "成功", cls: "kt-ok" }, retry: { label: "重试", cls: "kt-warn" }, failed: { label: "失败", cls: "kt-err" } };

// 效果评估
D.ai = {
  kpi: [
    { lbl: "人机一致率", val: "92.4%", trend: "up", delta: "1.2pp" },
    { lbl: "严重问题召回率", val: "96.0%", trend: "flat", delta: "0" },
    { lbl: "评分标准差（人机）", val: "0.31", trend: "down", delta: "0.05" },
    { lbl: "复核覆盖率", val: "38%", trend: "up", delta: "6pp" },
    { lbl: "申诉率", val: "1.8%", trend: "down", delta: "0.4pp" },
    { lbl: "人工复核节省", val: "62%", trend: "up", delta: "—" },
  ],
  calibration: [
    { band: "3.0–3.5", ai: 6, human: 7 },
    { band: "3.5–4.0", ai: 21, human: 22 },
    { band: "4.0–4.5", ai: 48, human: 46 },
    { band: "4.5–5.0", ai: 25, human: 25 },
  ],
  consistency: [
    { module: "客户服务", agree: 96, samples: 120 },
    { module: "安全管理", agree: 94, samples: 132 },
    { module: "EHS及风险管理", agree: 91, samples: 98 },
    { module: "环境管理", agree: 93, samples: 110 },
    { module: "机电运维", agree: 88, samples: 141 },
    { module: "设施维护", agree: 90, samples: 105 },
    { module: "综合管理", agree: 95, samples: 88 },
    { module: "财务管理", agree: 97, samples: 76 },
  ],
};

// 系统设置
D.users = [
  { id: 1, name: "贺星", account: "admin", role: "系统管理员", projects: "全部", active: true },
  { id: 2, name: "李国栋", account: "13800000001", role: "检查员", projects: "云鹭湾、澜山府", active: true },
  { id: 3, name: "王敏", account: "13800000002", role: "检查员", projects: "翡翠公园", active: true },
  { id: 4, name: "赵成", account: "13800000003", role: "检查员", projects: "梧桐郡", active: true },
  { id: 5, name: "陈璐", account: "13800000004", role: "驻场经理", projects: "蝶城·虹桥", active: false },
];
D.projectsCfg = [
  { name: "云鹭湾", modules: 8, items: 96, contact: "李国栋", enabled: true },
  { name: "翡翠公园", modules: 8, items: 96, contact: "王敏", enabled: true },
  { name: "梧桐郡", modules: 8, items: 96, contact: "赵成", enabled: true },
  { name: "澜山府", modules: 6, items: 72, contact: "周航", enabled: true },
  { name: "蝶城·虹桥", modules: 8, items: 96, contact: "陈璐", enabled: true },
  { name: "星河印", modules: 8, items: 96, contact: "—", enabled: false },
];

Object.assign(window, { D });
