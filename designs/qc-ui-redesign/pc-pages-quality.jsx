// pc-pages-quality.jsx —— 任务中心 + 评分复核
const { useState } = React;

// ============ 任务中心 ============
function PageTasks() {
  const [seg, setSeg] = useState("all");
  const [q, setQ] = useState("");
  const [detail, setDetail] = useState(null);
  const rows = D.tasks.filter(t =>
    (seg === "all" || t.status === seg) &&
    (!q || (t.project + t.id + t.inspector).includes(q))
  );
  return (
    <div className="page">
      <div className="phdr">
        <div>
          <h1>任务中心</h1>
          <div className="phdr-sub">创建、分配与跟踪品质检查任务</div>
        </div>
        <div className="phdr-acts">
          <button className="btn btn-ghost btn-sm">批量导出</button>
          <button className="btn btn-ghost btn-sm">批量创建</button>
          <button className="btn btn-primary">{I.plus}创建任务</button>
        </div>
      </div>

      <div className="filters">
        <span style={{ position: "relative", display: "inline-flex", alignItems: "center" }}>
          <span style={{ position: "absolute", left: 9, width: 13, height: 13, color: "var(--ink-400)", display: "inline-flex" }}>{I.search}</span>
          <input className="ipt" style={{ paddingLeft: 28 }} placeholder="搜索项目 / 任务编号" value={q} onChange={e => setQ(e.target.value)} />
        </span>
        <select className="sel"><option>全部项目</option>{D.projects.map(p => <option key={p}>{p}</option>)}</select>
        <div className="seg">
          {[["all", "全部"], ["pending", "待处理"], ["scored", "已评分"], ["rectifying", "整改中"], ["done", "已归档"]].map(([k, l]) =>
            <button key={k} className={seg === k ? "on" : ""} onClick={() => setSeg(k)}>{l}</button>)}
        </div>
        <button className="btn btn-sm btn-ghost" style={{ marginLeft: "auto" }}>重置</button>
      </div>

      <div className="card">
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr>
              <th>任务编号</th><th>项目</th><th>检查员</th><th className="num">检查项</th>
              <th className="ctr">严重 / 一般</th><th className="ctr">得分</th><th className="ctr">状态</th>
              <th className="num">创建日期</th><th className="ctr">操作</th>
            </tr></thead>
            <tbody>
              {rows.map(t => (
                <tr key={t.id} onClick={() => setDetail(t)} style={{ cursor: "pointer" }}>
                  <td className="num" style={{ color: "var(--ink-600)", fontSize: 12 }}>{t.id}</td>
                  <td style={{ fontWeight: 600 }}>{t.project}</td>
                  <td>{t.inspector}</td>
                  <td className="num">{t.items || "—"}</td>
                  <td className="ctr">
                    {t.status === "pending" ? <span style={{ color: "var(--ink-300)" }}>—</span> :
                      <span style={{ display: "inline-flex", gap: 4, alignItems: "center" }}>
                        {t.serious > 0 && <b style={{ color: "var(--err-strong)", fontSize: 12 }}>{t.serious}</b>}
                        <span style={{ color: "var(--ink-400)", fontSize: 12 }}>/</span>
                        <span style={{ fontSize: 12 }}>{t.general}</span>
                      </span>}
                  </td>
                  <td className="ctr"><span className={spCls(t.score)}>{t.score != null ? t.score.toFixed(1) : "–"}</span></td>
                  <td className="ctr"><span className={"kt " + D.statusMeta[t.status].cls}>{D.statusMeta[t.status].label}</span></td>
                  <td className="num" style={{ color: "var(--ink-500)" }}>{t.created}</td>
                  <td className="ctr" onClick={e => e.stopPropagation()}>
                    <a className="act-link" onClick={() => setDetail(t)}>详情</a>
                    <span style={{ color: "var(--ink-200)", margin: "0 6px" }}>|</span>
                    <a className="act-link">导出</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!rows.length && <div className="empty">{I.empty}没有符合筛选条件的任务</div>}
        <div style={{ padding: "0 16px 12px" }}>
          <div className="pagi">
            <span>共 {rows.length} 条</span>
            <button disabled>‹</button><button className="cur">1</button><button>2</button><button>›</button>
          </div>
        </div>
      </div>

      {detail && <TaskDetailDlg task={detail} onClose={() => setDetail(null)} />}
    </div>
  );
}

function TaskDetailDlg({ task: t, onClose }) {
  return (
    <React.Fragment>
      <div className="overlay" onClick={onClose} />
      <div className="drawer">
        <div className="drawer-h">
          <span className="drawer-t">{t.project} · {t.id}</span>
          <button className="icon-x" onClick={onClose}>{I.x}</button>
        </div>
        <div className="drawer-b">
          <dl className="desc" style={{ marginBottom: 16 }}>
            <dt>状态</dt><dd><span className={"kt " + D.statusMeta[t.status].cls}>{D.statusMeta[t.status].label}</span></dd>
            <dt>检查员</dt><dd>{t.inspector}</dd>
            <dt>检查范围</dt><dd>{t.modules} 个模块 / {t.items} 个检查项</dd>
            <dt>最新得分</dt><dd><span className={spCls(t.score)}>{t.score != null ? t.score.toFixed(1) : "未评分"}</span></dd>
          </dl>
          <div className="card" style={{ boxShadow: "none" }}>
            <div className="card-h"><span className="card-t">AI 评分 · 模块明细</span><span className="card-d">可展开查看检查项</span></div>
            {D.modules.slice(0, 5).map((m, i) => (
              <div key={m} style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 18px", borderBottom: "1px solid var(--ink-100)" }}>
                <span style={{ fontSize: 13, fontWeight: 600, width: 110 }}>{m}</span>
                <span className="hbar-track" style={{ flex: 1, height: 8 }}>
                  <span className="hbar-fill" style={{ width: (t.score != null ? t.score : 0) / 5 * 100 + "%", background: "var(--chart-" + ((i % 4) + 1) + ")" }} />
                </span>
                <span className={spCls(t.score)}>{t.score != null ? t.score.toFixed(1) : "–"}</span>
              </div>
            ))}
          </div>
          <div className="card" style={{ boxShadow: "none" }}>
            <div className="card-h"><span className="card-t">检查流程</span></div>
            <div style={{ padding: "14px 18px", display: "flex", gap: 0, alignItems: "center" }}>
              {[["检查执行", "done"], ["AI 评分", t.score != null ? "done" : "todo"], ["报告生成", t.status === "reported" || t.status === "done" ? "done" : "todo"], ["整改闭环", t.status === "done" ? "done" : "todo"]].map(([l, s], i, arr) => (
                <React.Fragment key={l}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 5, minWidth: 64 }}>
                    <span style={{
                      width: 22, height: 22, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
                      background: s === "done" ? "var(--brand-soft)" : "var(--bg-muted)",
                      color: s === "done" ? "var(--brand-ink)" : "var(--ink-400)",
                      border: s === "done" ? "1px solid var(--brand-border)" : "1px solid var(--ink-200)",
                    }}>{s === "done" ? I.check : i + 1}</span>
                    <span style={{ fontSize: 11, color: s === "done" ? "var(--ink-700)" : "var(--ink-400)", fontWeight: 500 }}>{l}</span>
                  </div>
                  {i < arr.length - 1 && <span style={{ flex: 1, height: 1, background: "var(--ink-200)", margin: "0 4px 18px" }} />}
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>
        <div className="drawer-f">
          <button className="btn">{I.down}导出评分</button>
          <button className="btn btn-primary" onClick={onClose}>关闭</button>
        </div>
      </div>
    </React.Fragment>
  );
}

// ============ 评分复核 ============
function PageScoring() {
  const [seg, setSeg] = useState("all");
  const rows = D.scoring.filter(r => seg === "all" || r.status === seg);
  return (
    <div className="page">
      <div className="phdr">
        <div>
          <h1>评分复核</h1>
          <div className="phdr-sub">人工复核 AI 评分 · 复核结果回流训练</div>
        </div>
        <div className="phdr-acts">
          <button className="btn">{I.down}导出复核记录</button>
        </div>
      </div>

      <div className="kpi-row cols-4">
        <div className="kpi"><div className="kpi-lbl">待复核</div><div className="kpi-num">14</div><div className="kpi-tags"><span className="ktag ktag-warn">今日新增 3</span></div></div>
        <div className="kpi"><div className="kpi-lbl">本周已复核</div><div className="kpi-num">23</div><div className="kpi-tags"><span className="ktag ktag-ok">一致 21</span><span className="ktag ktag-err">改分 2</span></div></div>
        <div className="kpi"><div className="kpi-lbl">人机一致率</div><div className="kpi-num">92.4<span className="kpi-unit">%</span></div><div className="kpi-tags"><span className="ktag ktag-ok">↑ 1.2pp 较上月</span></div></div>
        <div className="kpi"><div className="kpi-lbl">平均改分幅度</div><div className="kpi-num">0.2</div><div className="kpi-tags"><span className="ktag ktag-muted">5 分制</span></div></div>
      </div>

      <div className="filters">
        <div className="seg">
          {[["all", "全部"], ["pending_review", "待复核"], ["reviewed", "已复核"], ["disputed", "有争议"]].map(([k, l]) =>
            <button key={k} className={seg === k ? "on" : ""} onClick={() => setSeg(k)}>{l}</button>)}
        </div>
        <select className="sel" style={{ marginLeft: "auto" }}><option>全部项目</option>{D.projects.map(p => <option key={p}>{p}</option>)}</select>
      </div>

      <div className="card">
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr>
              <th>记录编号</th><th>项目</th><th>检查员</th><th className="ctr">AI 评分</th>
              <th className="ctr">人工评分</th><th className="num">分差</th><th className="ctr">状态</th>
              <th className="num">时间</th><th className="ctr">操作</th>
            </tr></thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.id}>
                  <td className="num" style={{ color: "var(--ink-600)", fontSize: 12 }}>{r.id}</td>
                  <td style={{ fontWeight: 600 }}>{r.project}</td>
                  <td>{r.inspector}</td>
                  <td className="ctr"><span className={spCls(r.ai_score)}>{r.ai_score.toFixed(1)}</span></td>
                  <td className="ctr">{r.human_score != null ? <span className={spCls(r.human_score)}>{r.human_score.toFixed(1)}</span> : <span style={{ color: "var(--ink-300)" }}>待复核</span>}</td>
                  <td className="num" style={{ fontWeight: r.diff >= 0.3 ? 700 : 500, color: r.diff == null ? "var(--ink-300)" : r.diff >= 0.3 ? "var(--err-strong)" : "var(--ink-600)" }}>{r.diff != null ? (r.diff > 0 ? "+" + r.diff.toFixed(1) : r.diff.toFixed(1)) : "—"}</td>
                  <td className="ctr"><span className={"kt " + D.scoringMeta[r.status].cls}>{D.scoringMeta[r.status].label}</span></td>
                  <td className="num" style={{ color: "var(--ink-500)", fontSize: 12 }}>{r.time}</td>
                  <td className="ctr"><a className="act-link">{r.status === "pending_review" ? "复核" : "查看"}</a></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div style={{ padding: "0 16px 12px" }}>
          <div className="pagi"><span>共 {rows.length} 条</span><button disabled>‹</button><button className="cur">1</button><button>›</button></div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { PageTasks, PageScoring });
