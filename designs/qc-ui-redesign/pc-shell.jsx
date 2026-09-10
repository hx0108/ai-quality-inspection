// pc-shell.jsx —— 应用外壳 + 页面路由 + Tweaks 面板（入口，最后加载）
const { useState, useEffect } = React;

const NAV = [
  { group: null, items: [{ key: "dashboard", label: "数据概览", icon: "grid" }] },
  { group: "品质管理", items: [
    { key: "tasks", label: "任务中心", icon: "list" },
    { key: "scoring", label: "评分复核", icon: "play" },
    { key: "reports", label: "报告管理", icon: "doc" },
    { key: "rectifications", label: "整改跟踪", icon: "loop" },
  ]},
  { group: "数据中心", items: [{ key: "analysis", label: "分析看板", icon: "chart" }] },
  { group: "智能运营", items: [
    { key: "llm", label: "模型监控", icon: "pulse" },
    { key: "aimetrics", label: "效果评估", icon: "star" },
  ]},
  { group: "系统", items: [{ key: "settings", label: "系统设置", icon: "gear" }] },
];

const PAGES = {
  dashboard: { title: "数据概览", group: "数据中心", comp: () => <PageDashboard /> },
  tasks:      { title: "任务中心", group: "品质管理", comp: () => <PageTasks /> },
  scoring:    { title: "评分复核", group: "品质管理", comp: () => <PageScoring /> },
  reports:    { title: "报告管理", group: "品质管理", comp: () => <PageReports /> },
  rectifications: { title: "整改跟踪", group: "品质管理", comp: () => <PageRects /> },
  analysis:   { title: "分析看板", group: "数据中心", comp: () => <PageAnalysis /> },
  llm:        { title: "模型监控", group: "智能运营", comp: () => <PageLlm /> },
  aimetrics:  { title: "效果评估", group: "智能运营", comp: () => <PageAiMetrics /> },
  settings:   { title: "系统设置", group: "系统", comp: () => <PageSettings /> },
};

function Todo({ title }) {
  return (
    <div className="page" style={{ paddingTop: 40 }}>
      <div className="empty">
        {I.empty}
        <div style={{ fontSize: 14, fontWeight: 600, color: "var(--ink-600)", marginBottom: 4 }}>该页面原型在 A2 阶段补齐</div>
        <div>设计系统与整体框架已就绪</div>
      </div>
    </div>
  );
}

function App() {
  const [page, setPage] = useState("dashboard");
  const meta = PAGES[page];

  if (location.hash === "#shot") document.documentElement.classList.add("no-anim");

  useEffect(() => {
    document.title = `${meta.title} · AI 品质检查系统原型`;
  }, [page]);

  return (
    <div className="shell">
      <aside className="side">
        <div className="side-brand">
          <span className="side-logo">{I.logo}</span>
          <span className="side-name">AI 品质检查</span>
        </div>
        <nav className="side-nav">
          {NAV.map((g, gi) => (
            <React.Fragment key={gi}>
              {g.group && <div className="sn-label">{g.group}</div>}
              {g.items.map(it => (
                <div key={it.key} className={"sn-item" + (page === it.key ? " on" : "")} onClick={() => setPage(it.key)}>
                  {I[it.icon]}<span>{it.label}</span>
                  {it.key === "rectifications" && <span className="sn-badge">18</span>}
                </div>
              ))}
            </React.Fragment>
          ))}
        </nav>
        <div className="side-foot">
          <div className="side-user">
            <span className="avatar">贺</span>
            <span>贺星 · 管理员</span>
          </div>
        </div>
      </aside>

      <div className="main">
        <header className="top">
          <div style={{ display: "flex", alignItems: "baseline" }}>
            <span className="top-crumb">{meta.group}</span>
            <span className="top-title">{meta.title}</span>
          </div>
          <div className="top-right">
            <button className="proj-chip">
              {I.shield}全部项目{I.chevD}
            </button>
            <button className="icon-btn" title="通知">{I.bell}<span className="bubble" /></button>
            <div className="user-chip">
              <span className="avatar">贺</span>
              <b>贺星</b>{I.chevD}
            </div>
          </div>
        </header>
        <div className="cnt">{meta.comp()}</div>
      </div>

      <TweaksPanel />
    </div>
  );
}

// —— Tweaks 面板：主色 / 圆角 / 密度 ——
const ACCENTS = [
  ["#0f8a80", "#14a094", "#0c7168", "#e7f5f3", "#b5e0da", "#0a6b62"],
  ["#5e6ad2", "#6e78dc", "#4d58bd", "#eef0fb", "#c9cdf2", "#4148a8"],
  ["#3f7ad6", "#5288de", "#3568bd", "#e9f1fb", "#c3d8f2", "#2b5aa8"],
  ["#8a5cf6", "#9b76f8", "#7448d9", "#f2edfd", "#dccdfa", "#6a3fc4"],
  ["#d05858", "#da6e6e", "#b84545", "#fceeee", "#f2c8c8", "#a83a3a"],
];

function TweaksPanel() {
  const [open, setOpen] = useState(false);
  const [accent, setAccent] = useState(0);
  const [radius, setRadius] = useState(10);
  const [gap, setGap] = useState(14);

  useEffect(() => {
    const a = ACCENTS[accent];
    const r = document.documentElement.style;
    r.setProperty("--brand", a[0]);
    r.setProperty("--brand-hover", a[1]);
    r.setProperty("--brand-active", a[2]);
    r.setProperty("--brand-soft", a[3]);
    r.setProperty("--brand-border", a[4]);
    r.setProperty("--brand-ink", a[5]);
    r.setProperty("--side-active-bg", a[0] + "29");
    r.setProperty("--side-active-line", a[1]);
    r.setProperty("--r-lg", radius + "px");
    r.setProperty("--focus-ring", `0 0 0 3px ${a[0]}47`);
  }, [accent, radius]);

  useEffect(() => {
    document.documentElement.style.setProperty("--chart-1", ACCENTS[accent][0]);
    document.documentElement.style.setProperty("--gap-blk", gap + "px");
  }, [accent, gap]);

  if (!open) {
    return <button className="tweaks-open" onClick={() => setOpen(true)}>Tweaks</button>;
  }
  return (
    <div className="tweaks">
      <h4>调整设计参数<button onClick={() => setOpen(false)}>收起</button></h4>
      <label>主色</label>
      <div className="swatches">
        {ACCENTS.map((a, i) => (
          <div key={i} className={"sw" + (i === accent ? " on" : "")} style={{ background: a[0] }} onClick={() => setAccent(i)} />
        ))}
      </div>
      <label>圆角 {radius}px</label>
      <input type="range" min="4" max="14" value={radius} onChange={e => setRadius(+e.target.value)} />
      <label>卡片间距 {gap}px</label>
      <input type="range" min="8" max="20" value={gap} onChange={e => setGap(+e.target.value)} />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
