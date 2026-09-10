// pc-page-dashboard.jsx —— 数据概览（招牌页）
const { useState } = React;

function spCls(v) {
  if (v == null) return "sp sp-na";
  if (v >= 4.5) return "sp sp-hi";
  if (v >= 3.5) return "sp sp-mid";
  return "sp sp-lo";
}

// —— KPI 卡 ——
function Kpi({ lbl, num, unit, tags, onClick, active, errNum }) {
  return (
    <div className={"kpi kpi-click" + (active ? " kpi-active" : "")} onClick={onClick}>
      <div className="kpi-lbl">{lbl}</div>
      <div className={"kpi-num" + (errNum ? " kpi-err" : "")}>{num}{unit ? <span className="kpi-unit">{unit}</span> : null}</div>
      <div className="kpi-tags">
        {tags.map((t, i) => <span key={i} className={"ktag " + t[0]}>{t[1]}</span>)}
      </div>
      <span className="kpi-go">{I.chevR}</span>
    </div>
  );
}

// —— 模块得分热力表 ——
function ScoreTable({ onRow }) {
  const s = D.projectScores;
  return (
    <div className="tbl-wrap">
      <table className="tbl module-tbl">
        <thead>
          <tr>
            <th>项目名称</th>
            {D.modules.map(m => <th key={m} className="ctr">{m.replace("EHS及风险管理", "EHS")}</th>)}
            <th className="ctr">总分</th>
            <th className="ctr">检查日</th>
          </tr>
        </thead>
        <tbody>
          {s.map(p => (
            <tr key={p.project_name} onClick={() => onRow(p)} style={{ cursor: "pointer", opacity: p.latest_score == null ? 0.62 : 1 }} title={p.latest_score == null ? "本月尚未检查" : "查看项目详情"}>
              <td style={{ fontWeight: 600 }}>{p.project_name}</td>
              {D.modules.map(m => (
                <td key={m} className="ctr heat">
                  <span className={spCls(p.modules ? p.modules[m] : null)}>
                    {p.modules && p.modules[m] != null ? p.modules[m].toFixed(1) : "–"}
                  </span>
                </td>
              ))}
              <td className="ctr"><span className={spCls(p.latest_score)} style={{ fontSize: 13 }}>{p.latest_score != null ? p.latest_score.toFixed(1) : "–"}</span></td>
              <td className="ctr num" style={{ color: "var(--ink-500)", fontSize: 12 }}>{p.checked_at || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// —— 问题按模块分布（单色深浅 + 严重拆分红） ——
function IssueBars({ onBar }) {
  const max = Math.max(...D.issueByModule.map(d => d.total));
  const ramp = ["chart-ramp-1", "chart-ramp-2", "chart-ramp-3", "chart-ramp-4", "chart-ramp-5", "chart-ramp-5", "chart-ramp-5"];
  return (
    <div style={{ padding: "12px 18px 16px" }}>
      {D.issueByModule.map((d, i) => {
        const w = (d.total / max) * 100;
        const wS = d.serious > 0 ? (d.serious / d.total) * 100 : 0;
        return (
          <div key={d.module} className="hbar-row" style={{ cursor: "pointer" }} onClick={() => onBar(d)} title="点击查看该模块问题明细">
            <span className="hbar-lbl">{d.module.replace("EHS及风险管理", "EHS")}</span>
            <span className="hbar-track">
              <span className="hbar-fill" style={{ width: w + "%", background: `var(--${ramp[i]})`, display: "flex" }}>
                {wS > 0 && <span style={{ width: wS + "%", height: "100%", background: "var(--err)", borderRadius: "4px 0 0 4px" }} title={`严重 ${d.serious}`} />}
              </span>
            </span>
            <span className="hbar-val" style={{ display: "flex", gap: 6 }}>
              {d.serious > 0 && <b style={{ color: "var(--err-strong)", fontWeight: 700 }}>{d.serious}</b>}
              {d.total}
            </span>
          </div>
        );
      })}
      <div className="legend" style={{ marginTop: 10 }}>
        <span><i style={{ background: "var(--err)" }} />严重</span>
        <span><i style={{ background: "var(--chart-ramp-2)" }} />一般（按数量深→浅）</span>
      </div>
    </div>
  );
}

// —— 各项目整改完成率（语义堆叠） ——
function RectBars() {
  return (
    <div style={{ padding: "12px 18px 16px" }}>
      {D.rectByProject.map(d => {
        const total = d.ok + d.pending + d.over;
        const rate = Math.round((d.ok / total) * 100);
        return (
          <div key={d.project} className="hbar-row" style={{ gridTemplateColumns: "76px 1fr 44px" }}>
            <span className="hbar-lbl">{d.project}</span>
            <span className="sbar-track" title={`已通过 ${d.ok} · 待整改 ${d.pending} · 逾期 ${d.over}`}>
              {d.ok > 0 && <span className="sbar-ok" style={{ width: (d.ok / total) * 100 + "%" }} />}
              {d.over > 0 && <span className="sbar-over" style={{ width: (d.over / total) * 100 + "%" }} />}
            </span>
            <span className="hbar-val">{rate}%</span>
          </div>
        );
      })}
      <div className="legend" style={{ marginTop: 10 }}>
        <span><i style={{ background: "var(--ok)" }} />已通过</span>
        <span><i style={{ background: "var(--ink-300)" }} />待整改</span>
        <span><i style={{ background: "var(--err)" }} />逾期</span>
      </div>
    </div>
  );
}

// —— 近 8 周平均分趋势（SVG 折线） ——
function TrendLine() {
  const W = 1100, H = 150, P = 10;
  const min = 3.4, max = 4.6;
  const xs = D.trend.map((_, i) => P + (i / (D.trend.length - 1)) * (W - P * 2));
  const ys = D.trend.map(v => H - P - ((v - min) / (max - min)) * (H - P * 2));
  const pts = xs.map((x, i) => `${x.toFixed(1)},${ys[i].toFixed(1)}`).join(" ");
  const last = D.trend[D.trend.length - 1];
  const prev = D.trend[D.trend.length - 2];
  const delta = last - prev;
  return (
    <div style={{ padding: "10px 18px 14px" }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto", display: "block" }}>
        <defs>
          <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" style={{ stopColor: "var(--chart-1)", stopOpacity: 0.16 }} />
            <stop offset="100%" style={{ stopColor: "var(--chart-1)", stopOpacity: 0 }} />
          </linearGradient>
        </defs>
        {[3.5, 4.0, 4.5].map((g) => {
          const y = H - P - ((g - min) / (max - min)) * (H - P * 2);
          return <line key={g} x1={P} x2={W - P} y1={y} y2={y} className="trend-grid" />;
        })}
        <polygon points={`${P},${H - P} ${pts} ${W - P},${H - P}`} fill="url(#trendFill)" />
        <polyline points={pts} className="trend-line" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" style={{ stroke: "var(--chart-1)" }} />
        {xs.map((x, i) => (
          <circle key={i} cx={x} cy={ys[i]} r={i === xs.length - 1 ? 4 : 2.6}
            style={{ fill: i === xs.length - 1 ? "var(--chart-1)" : "#fff", stroke: "var(--chart-1)", strokeWidth: 1.6 }} />
        ))}
      </svg>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--ink-400)", padding: "0 4px", fontVariantNumeric: "tabular-nums" }}>
        {D.trendLabels.map(l => <span key={l}>{l}</span>)}
      </div>
      <div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ fontSize: 22, fontWeight: 700, color: "var(--ink-900)", letterSpacing: "-0.5px" }}>{last.toFixed(1)}</span>
        <span className={"kpi-trend " + (delta >= 0 ? "up" : "down")}>
          {delta >= 0 ? I.trendUp : I.trendDown}{Math.abs(delta).toFixed(1)} 较上周
        </span>
        <span style={{ fontSize: 12, color: "var(--ink-400)", marginLeft: "auto" }}>全项目检查平均分 · 5 分制</span>
      </div>
    </div>
  );
}

// —— 概览页 ——
function PageDashboard() {
  const [drawer, setDrawer] = useState(null);
  const s = D.summary;

  return (
    <div className="page">
      <div className="phdr">
        <div>
          <h1>数据概览</h1>
          <div className="phdr-sub">物业品质检查核心指标 · 更新于 09-10 08:30</div>
        </div>
        <div className="phdr-acts">
          <button className="btn">{I.down}导出全部报表</button>
        </div>
      </div>

      <div className="kpi-row cols-5">
        <Kpi lbl="检查任务" num={s.total_tasks} tags={[["kt-muted", `待处理 ${s.pending_tasks}`], ["kt-brand", `进行中 ${s.in_progress_tasks}`]]} onClick={() => setDrawer("task")} active={drawer === "task"} />
        <Kpi lbl="本月覆盖率" num={s.coverage_rate} unit="%" tags={[["kt-muted", `${s.monthly_checked_projects} / ${s.total_projects} 项目`]]} onClick={() => setDrawer("coverage")} active={drawer === "coverage"} />
        <Kpi lbl="问题总数" num={s.total_issues} tags={[["kt-err", `严重 ${s.serious_issues}`], ["kt-warn", `一般 ${s.general_issues}`]]} onClick={() => setDrawer("issue")} active={drawer === "issue"} />
        <Kpi lbl="待整改" num={s.pending_rectifications} errNum={s.serious_issues > 5} tags={[["kt-muted", `已提交 ${s.submitted_rectifications}`]]} onClick={() => setDrawer("rect")} active={drawer === "rect"} />
        <Kpi lbl="整改完成率" num={s.rectification_rate} unit="%" tags={[["kt-ok", `已通过 ${s.approved_rectifications}`]]} onClick={() => setDrawer("rect")} active={drawer === "rect"} />
      </div>

      <div className="card">
        <div className="card-h">
          <div style={{ display: "flex", alignItems: "baseline" }}>
            <span className="card-t">各项目模块得分对比</span>
            <span className="card-d">最新一次检查 · 点击行查看详情</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span className="legend" style={{ fontSize: 11 }}>
              <span><i style={{ background: "#edf6f0", border: "1px solid var(--ok-border)" }} />≥4.5</span>
              <span><i style={{ background: "#faf5e9", border: "1px solid var(--warn-border)" }} />3.5–4.4</span>
              <span><i style={{ background: "var(--err-soft)", border: "1px solid var(--err-border)" }} />&lt;3.5</span>
            </span>
            <button className="btn btn-sm">{I.down}导出</button>
          </div>
        </div>
        <ScoreTable onRow={(p) => setDrawer({ project: p })} />
      </div>

      <div className="charts2">
        <div className="card">
          <div className="card-h">
            <span className="card-t">问题按模块分布</span>
            <button className="btn btn-sm">{I.down}导出</button>
          </div>
          <IssueBars onBar={() => setDrawer("issue")} />
        </div>
        <div className="card">
          <div className="card-h">
            <span className="card-t">各项目整改完成率</span>
            <button className="btn btn-sm">{I.down}导出</button>
          </div>
          <RectBars />
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <div className="card-h">
          <span className="card-t">平均分趋势</span>
          <span className="card-d">近 8 周</span>
        </div>
        <TrendLine />
      </div>

      {drawer && <DashDrawer kind={drawer} onClose={() => setDrawer(null)} />}
    </div>
  );
}

// —— 抽屉（演示 KPI/行点击下钻） ——
function DashDrawer({ kind, onClose }) {
  const p = kind.project;
  const title = p ? `${p.project_name} · 检查详情`
    : { task: "检查任务明细", coverage: "本月覆盖情况", issue: "问题明细", rect: "整改明细" }[kind] || "明细";
  return (
    <React.Fragment>
      <div className="overlay" onClick={onClose} />
      <div className="drawer">
        <div className="drawer-h">
          <span className="drawer-t">{title}</span>
          <button className="icon-x" onClick={onClose}>{I.x}</button>
        </div>
        <div className="drawer-b">
          {p ? (
            <React.Fragment>
              <dl className="desc" style={{ marginBottom: 16 }}>
                <dt>最新总分</dt><dd><span className={spCls(p.latest_score)}>{p.latest_score?.toFixed(1)}</span></dd>
                <dt>检查日期</dt><dd className="num">{p.checked_at}</dd>
                <dt>模块均分</dt><dd className="num">{p.latest_score?.toFixed(1)} / 5.0</dd>
              </dl>
              <table className="tbl">
                <thead><tr><th>模块</th><th className="ctr">得分</th></tr></thead>
                <tbody>
                  {D.modules.map(m => (
                    <tr key={m}><td>{m}</td><td className="ctr"><span className={spCls(p.modules?.[m])}>{p.modules?.[m] != null ? p.modules[m].toFixed(1) : "–"}</span></td></tr>
                  ))}
                </tbody>
              </table>
            </React.Fragment>
          ) : (
            <table className="tbl">
              <thead><tr><th>项目</th><th>检查项</th><th className="ctr">严重度</th><th>状态</th></tr></thead>
              <tbody>
                {D.tasks.filter(t => t.status !== "pending").slice(0, 8).map(t => (
                  <tr key={t.id}>
                    <td style={{ fontWeight: 600 }}>{t.project}</td>
                    <td style={{ color: "var(--ink-600)" }}>月度品质检查 · {t.items} 项</td>
                    <td className="ctr">
                      {t.serious > 0 ? <span className="kt kt-err">严重 {t.serious}</span> : <span className="kt kt-muted">无严重</span>}
                    </td>
                    <td><span className={"kt " + D.statusMeta[t.status].cls}>{D.statusMeta[t.status].label}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        <div className="drawer-f">
          <button className="btn">{I.down}导出</button>
          <button className="btn btn-primary" onClick={onClose}>关闭</button>
        </div>
      </div>
    </React.Fragment>
  );
}

Object.assign(window, { PageDashboard, spCls });
