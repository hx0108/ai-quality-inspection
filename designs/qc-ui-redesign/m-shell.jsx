// m-shell.jsx —— 移动端原型舞台：左侧屏幕导航 + 手机框
const { useState, useEffect } = React;

const SCREENS = [
  { key: "login", label: "登录 / 注册", tag: "游客", render: () => <MLogin />, noStatus: false },
  { key: "dash", label: "概览", tag: "tab1", render: (go) => <MDash go={go} /> },
  { key: "tasks", label: "任务列表", tag: "tab2", render: (go) => <MTasks go={go} /> },
  { key: "taskdetail", label: "任务详情", tag: "二级", render: (go) => <MTaskDetail go={go} /> },
  { key: "inspect", label: "巡检 · 列表式", tag: "核心", render: (go) => <MInspect go={go} /> },
  { key: "inspectcard", label: "巡检 · 卡片式", tag: "核心", render: (go) => <MInspectCard go={go} /> },
  { key: "scoring", label: "AI 评分", tag: "核心", render: (go) => <MScoring go={go} /> },
  { key: "report", label: "检查报告", tag: "tab3", render: (go) => <MReport go={go} /> },
  { key: "rects", label: "整改列表", tag: "tab4", render: (go) => <MRects go={go} /> },
  { key: "rectsubmit", label: "整改提交", tag: "核心", render: (go) => <MRectSubmit go={go} /> },
];

function App() {
  const [cur, setCur] = useState("dash");
  const scr = SCREENS.find(s => s.key === cur) || SCREENS[1];

  useEffect(() => {
    if (location.hash === "#shot") document.documentElement.classList.add("no-anim");
    document.title = "移动端原型 · AI 品质检查系统";
  }, []);

  return (
    <div className="stage">
      <aside className="m-rail">
        <h1>移动端 · 10 屏</h1>
        <div className="sub">巡检员核心流 · 点按屏幕内元素可交互</div>
        {SCREENS.map((s, i) => (
          <button key={s.key} className={"m-nav-item" + (cur === s.key ? " on" : "")} onClick={() => setCur(s.key)}>
            <span className="idx">{String(i + 1).padStart(2, "0")}</span>
            {s.label}
            <span className="tag">{s.tag}</span>
          </button>
        ))}
        <div style={{ padding: "14px 8px 0", fontSize: 11, color: "var(--ink-400)", lineHeight: 1.7, borderTop: "1px solid var(--ink-100)", marginTop: 10 }}>
          落地时映射：Vant 4 主题变量接 qc-theme tokens；Tabbar 抽成共享组件（现生产代码复制了 5 份）；Login 深青旧体系废弃。
        </div>
      </aside>

      <div className="m-center">
        <div className="phone">
          <div className="m-status">
            <span>9:41</span>
            <span className="sig">
              <svg viewBox="0 0 18 12"><path d="M1 9h2v2H1zM5 7h2v4H5zM9 5h2v6H9zM13 3h2v8h-2z" fill="currentColor" stroke="none" /></svg>
              <svg viewBox="0 0 22 12"><rect x="1" y="1.5" width="17" height="9" rx="2.5" /><rect x="3" y="3.5" width="11" height="5" rx="1" fill="currentColor" stroke="none" /><path d="M20 4.5v3" strokeWidth="2" /></svg>
            </span>
          </div>
          {scr.render(setCur)}
        </div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
