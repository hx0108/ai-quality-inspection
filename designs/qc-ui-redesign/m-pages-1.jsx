// m-pages-1.jsx —— 登录 / 概览 / 任务列表 / 任务详情
const { useState } = React;

// 共享的移动端小组件（window 级共享）
function MNavBar({ title, onBack }) {
  return (
    <div className="m-nav">
      <button className="back" onClick={onBack}>{I.chevR && <svg viewBox="0 0 16 16" style={{ transform: "rotate(180deg)" }}><path d="M6 3l5 5-5 5" /></svg>}</button>
      <div className="m-title">{title}</div>
      <div className="r-act" />
    </div>
  );
}

function MTabbar({ active, go }) {
  const tabs = [
    ["概览", "grid", "dash"], ["任务", "list", "tasks"], ["报告", "doc", "reports"],
    ["整改", "loop", "rects"], ["分析", "chart", "analysis"],
  ];
  return (
    <div className="m-tabbar">
      {tabs.map(([l, ic, k]) => (
        <button key={k} className={"m-tab" + (active === k ? " on" : "")} onClick={() => go(k)}>
          {I[ic]}<span>{l}</span>
        </button>
      ))}
    </div>
  );
}

// ============ 01 登录 ============
function MLogin() {
  const [mode, setMode] = useState("login");
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", background: "var(--bg)", overflow: "hidden" }}>
      <div style={{ background: "linear-gradient(150deg, #14a094 0%, #0c7168 78%)", padding: "26px 22px 30px", color: "#fff" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
          <span style={{ width: 38, height: 38, borderRadius: 11, background: "rgba(255,255,255,0.16)", display: "inline-flex", alignItems: "center", justifyContent: "center", boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.22)" }}>
            <span style={{ width: 20, height: 20, display: "inline-flex" }}>{I.logo}</span>
          </span>
          <div>
            <div style={{ fontSize: 17, fontWeight: 800, letterSpacing: "0.2px" }}>AI 品质检查</div>
            <div style={{ fontSize: 10.5, opacity: 0.75, letterSpacing: "0.6px" }}>QUALITY INSPECTION</div>
          </div>
        </div>
        <div style={{ marginTop: 22, fontSize: 21, fontWeight: 800, letterSpacing: "-0.3px" }}>现场检查，AI 评分</div>
        <div style={{ marginTop: 5, fontSize: 12.5, opacity: 0.78, lineHeight: 1.6 }}>拍照留证 · 离线可用 · 自动生成报告与整改闭环</div>
      </div>

      <div style={{ flex: 1, padding: "20px 18px", overflowY: "auto" }}>
        <div style={{ display: "flex", gap: 20, padding: "0 4px 12px" }}>
          {[["login", "登录"], ["reg", "注册"]].map(([k, l]) => (
            <button key={k} onClick={() => setMode(k)} style={{ border: "none", background: "none", padding: "0 2px 8px", fontSize: 16, fontWeight: mode === k ? 800 : 500, color: mode === k ? "var(--ink-900)" : "var(--ink-400)", cursor: "pointer", borderBottom: mode === k ? "2.5px solid var(--brand)" : "2.5px solid transparent", fontFamily: "var(--sans)" }}>{l}</button>
          ))}
        </div>
        <div style={{ display: "grid", gap: 11 }}>
          {mode === "reg" && <input className="m-ipt" placeholder="姓名" />}
          <input className="m-ipt" placeholder="手机号 / 账号" defaultValue="13800000001" />
          <input className="m-ipt" type="password" placeholder="密码" defaultValue="········" />
          {mode === "reg" && (
            <div className="m-note" style={{ background: "var(--bg-muted)", color: "var(--ink-500)" }}>
              {I.spark}<span>注册需选择所属项目，由管理员审核后启用</span>
            </div>
          )}
          <button className="m-btn m-btn-primary m-btn-block" style={{ marginTop: 4 }}>{mode === "login" ? "登录" : "提交注册"}</button>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12.5, color: "var(--ink-500)", padding: "2px 2px 0" }}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
              <span style={{ width: 15, height: 15, borderRadius: 4, background: "var(--brand)", display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
                <span style={{ width: 9, height: 9, display: "inline-flex", color: "#fff" }}>{I.check}</span>
              </span>
              保持登录
            </span>
            <a style={{ color: "var(--brand)", fontWeight: 600, cursor: "pointer" }}>忘记密码</a>
          </div>
        </div>
      </div>
      <div style={{ padding: "10px 0 14px", textAlign: "center", fontSize: 11, color: "var(--ink-400)" }}>登录即代表同意《服务协议》与《隐私政策》</div>
    </div>
  );
}

// ============ 02 概览 ============
function MDash({ go }) {
  return (
    <React.Fragment>
      <MNavBar title="概览" />
      <div className="m-body">
        <div className="m-pad">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <div>
              <div style={{ fontSize: 17, fontWeight: 800, color: "var(--ink-900)" }}>早上好，李国栋</div>
              <div style={{ fontSize: 12, color: "var(--ink-500)", marginTop: 2 }}>今天有 2 个检查任务待执行</div>
            </div>
            <span className="avatar" style={{ width: 36, height: 36, fontSize: 13, background: "var(--brand-soft)", color: "var(--brand-ink)" }}>李</span>
          </div>

          <div className="m-kpi-grid" style={{ marginBottom: 12 }}>
            <div className="m-kpi"><div className="l">我的任务</div><div className="v">2<small> 待执行</small></div></div>
            <div className="m-kpi"><div className="l">本月已完成</div><div className="v">6<small> 次</small></div></div>
            <div className="m-kpi"><div className="l">待整改</div><div className="v" style={{ color: "var(--warn-strong)" }}>5</div></div>
            <div className="m-kpi"><div className="l">整改逾期</div><div className="v" style={{ color: "var(--err-strong)" }}>1</div></div>
          </div>

          <div className="m-card">
            <div className="m-card-h"><span className="m-card-t">我负责的项目</span></div>
            <div style={{ padding: "4px 0 6px" }}>
              {[["云鹭湾", 4.4, "09-08 已检查"], ["澜山府", 4.0, "09-03 已检查"]].map(([p, s, d]) => (
                <div key={p} className="m-cell" style={{ cursor: "pointer" }} onClick={() => go("tasks")}>
                  <span style={{ width: 30, height: 30, borderRadius: 8, background: "var(--brand-soft)", color: "var(--brand-ink)", display: "inline-flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{I.shield}</span>
                  <div className="gr">
                    <div className="t">{p}</div>
                    <div className="d">{d}</div>
                  </div>
                  <span className="sp sp-hi">{s.toFixed(1)}</span>
                  <span style={{ width: 14, height: 14, color: "var(--ink-300)", display: "inline-flex" }}>{I.chevR}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="m-card">
            <div className="m-card-h"><span className="m-card-t">问题集中模块</span><span className="card-d">全项目 · 本月</span></div>
            <div style={{ padding: "10px 14px 14px" }}>
              {[["机电运维", 26], ["安全管理", 21], ["环境管理", 18]].map(([m, n], i) => (
                <div key={m} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 9 }}>
                  <span style={{ fontSize: 12.5, color: "var(--ink-700)", width: 56 }}>{m}</span>
                  <span className="m-track" style={{ flex: 1 }}><span className="m-fill" style={{ width: (n / 26) * 100 + "%", background: `var(--chart-${i + 1})` }} /></span>
                  <span style={{ fontSize: 12, fontWeight: 600, color: "var(--ink-600)", width: 20, textAlign: "right" }}>{n}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      <MTabbar active="dash" go={go} />
    </React.Fragment>
  );
}

// ============ 03 任务列表 ============
function MTasks({ go }) {
  const [seg, setSeg] = useState("all");
  return (
    <React.Fragment>
      <MNavBar title="检查任务" />
      <div className="m-body">
        <div style={{ padding: "10px 14px 0" }}>
          <input className="m-ipt" style={{ height: 38, fontSize: 13.5 }} placeholder="搜索项目 / 任务" />
          <div style={{ marginTop: 10 }}>
            <div className="seg">
              {[["all", "全部 7"], ["todo", "待执行 2"], ["done", "已完成 5"]].map(([k, l]) =>
                <button key={k} className={seg === k ? "on" : ""} onClick={() => setSeg(k)}>{l}</button>)}
            </div>
          </div>
        </div>
        <div className="m-pad">
          {[
            ["云鹭湾", "8 模块 / 96 项", "scored", "09-08", 4.4],
            ["澜山府", "6 模块 / 72 项", "rectifying", "09-03", 4.0],
            ["云鹭湾", "8 模块 / 96 项", "pending", "今天 14:00", null],
          ].map(([p, range, st, date, score], i) => (
            <div key={i} className="m-card" style={{ cursor: "pointer", padding: "13px 14px" }} onClick={() => go("taskdetail")}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ fontSize: 15, fontWeight: 700, color: "var(--ink-900)" }}>{p} · 月度品质检查</span>
                <span className={"kt " + D.statusMeta[st].cls}>{D.statusMeta[st].label}</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 8, fontSize: 12.5, color: "var(--ink-500)" }}>
                <span>{range}</span>
                <span>·</span>
                <span>{date}</span>
                {score && <span style={{ marginLeft: "auto" }}><span className={"sp " + (score >= 4.5 ? "sp-hi" : "sp-mid")}>{score.toFixed(1)}</span></span>}
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 11 }}>
                {st === "pending"
                  ? <button className="m-btn m-btn-primary" style={{ flex: 1, height: 36, fontSize: 13.5 }}>开始检查</button>
                  : <React.Fragment>
                      <button className="m-btn" style={{ flex: 1, height: 36, fontSize: 13.5 }}>查看评分</button>
                      <button className="m-btn" style={{ flex: 1, height: 36, fontSize: 13.5 }}>检查记录</button>
                    </React.Fragment>}
              </div>
            </div>
          ))}
        </div>
      </div>
      <MTabbar active="tasks" go={go} />
    </React.Fragment>
  );
}

// ============ 04 任务详情 ============
function MTaskDetail({ go }) {
  return (
    <React.Fragment>
      <MNavBar title="任务详情" />
      <div className="m-body">
        <div className="m-pad">
          <div className="m-card" style={{ padding: "14px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 16, fontWeight: 800, color: "var(--ink-900)" }}>云鹭湾 · 月度品质检查</span>
              <span className="kt kt-brand">进行中</span>
            </div>
            <dl className="desc" style={{ marginTop: 12, gridTemplateColumns: "76px 1fr" }}>
              <dt>检查范围</dt><dd>8 模块 / 96 项</dd>
              <dt>检查员</dt><dd>李国栋</dd>
              <dt>计划日期</dt><dd>2026-09-10</dd>
              <dt>任务编号</dt><dd style={{ fontFamily: "var(--mono)", fontSize: 12.5 }}>T-240910-01</dd>
            </dl>
          </div>

          <div className="m-card">
            <div className="m-card-h"><span className="m-card-t">模块进度</span><span className="card-d">3 / 8 已完成</span></div>
            <div style={{ padding: "6px 0" }}>
              {[["客户服务", 5, 5], ["安全管理", 5, 5], ["EHS及风险管理", 5, 5], ["环境管理", 3, 5], ["机电运维", 0, 5]].map(([m, done, total]) => (
                <div key={m} className="m-cell">
                  <div className="gr">
                    <div className="t" style={{ fontSize: 13.5 }}>{m}</div>
                    <div className="d">{done} / {total} 项</div>
                  </div>
                  {done === total
                    ? <span className="kt kt-ok">已完成</span>
                    : done > 0 ? <span className="kt kt-brand">进行中</span> : <span className="kt kt-muted">未开始</span>}
                </div>
              ))}
            </div>
          </div>

          <button className="m-btn m-btn-primary m-btn-block" onClick={() => go("inspect")}>继续检查 · 环境管理</button>
        </div>
      </div>
      <MTabbar active="tasks" go={go} />
    </React.Fragment>
  );
}

Object.assign(window, { MNavBar, MTabbar, MLogin, MDash, MTasks, MTaskDetail });
