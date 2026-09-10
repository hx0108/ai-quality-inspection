// pc-pages-data.jsx —— 报告管理 + 整改跟踪 + 分析看板
const { useState } = React;

// ============ 报告管理 ============
function PageReports() {
  const [detail, setDetail] = useState(null);
  return (
    <div className="page">
      <div className="phdr">
        <div>
          <h1>报告管理</h1>
          <div className="phdr-sub">AI 生成品质检查报告 · 支持导出 Word / PDF</div>
        </div>
        <div className="phdr-acts">
          <button className="btn btn-primary">{I.spark}生成报告</button>
        </div>
      </div>

      <div className="filters">
        <select className="sel"><option>全部项目</option>{D.projects.map(p => <option key={p}>{p}</option>)}</select>
        <select className="sel"><option>全部状态</option><option>已生成</option><option>生成中</option></select>
        <input className="ipt" type="date" />
        <span style={{ color: "var(--ink-300)" }}>–</span>
        <input className="ipt" type="date" />
        <button className="btn btn-sm btn-ghost" style={{ marginLeft: "auto" }}>重置</button>
      </div>

      <div className="card">
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr>
              <th>报告名称</th><th>项目</th><th className="num">模块数</th><th className="ctr">总分</th>
              <th className="ctr">状态</th><th className="num">生成耗时</th><th className="num">生成时间</th><th className="ctr">操作</th>
            </tr></thead>
            <tbody>
              {D.reports.map(r => (
                <tr key={r.id}>
                  <td><a className="act-link" onClick={() => setDetail(r)} style={{ fontWeight: 600 }}>{r.title}</a></td>
                  <td>{r.project}</td>
                  <td className="num">{r.modules}</td>
                  <td className="ctr"><span className={spCls(r.score)}>{r.score.toFixed(1)}</span></td>
                  <td className="ctr"><span className={"kt " + D.reportMeta[r.status].cls}>{D.reportMeta[r.status].label}</span></td>
                  <td className="num" style={{ color: "var(--ink-500)" }}>{r.gen_sec ? r.gen_sec + "s" : "—"}</td>
                  <td className="num" style={{ color: "var(--ink-500)", fontSize: 12 }}>{r.created}</td>
                  <td className="ctr" style={{ whiteSpace: "nowrap" }}>
                    <a className="act-link">Word</a>
                    <span style={{ color: "var(--ink-200)", margin: "0 6px" }}>|</span>
                    <a className="act-link">PDF</a>
                    <span style={{ color: "var(--ink-200)", margin: "0 6px" }}>|</span>
                    <a className="act-link" style={{ color: "var(--err)" }} title="删除">删除</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div style={{ padding: "0 16px 12px" }}>
          <div className="pagi"><span>共 {D.reports.length} 条</span><button disabled>‹</button><button className="cur">1</button><button>›</button></div>
        </div>
      </div>

      {detail && <ReportDrawer r={detail} onClose={() => setDetail(null)} />}
    </div>
  );
}

function ReportDrawer({ r, onClose }) {
  return (
    <React.Fragment>
      <div className="overlay" onClick={onClose} />
      <div className="drawer" style={{ width: "min(640px, 94vw)" }}>
        <div className="drawer-h">
          <span className="drawer-t">{r.title}</span>
          <button className="icon-x" onClick={onClose}>{I.x}</button>
        </div>
        <div className="drawer-b">
          <div className="kpi-row cols-3" style={{ marginBottom: 14 }}>
            <div className="kpi" style={{ animation: "none" }}><div className="kpi-lbl">综合得分</div><div className="kpi-num">{r.score.toFixed(1)}</div></div>
            <div className="kpi" style={{ animation: "none" }}><div className="kpi-lbl">检查模块</div><div className="kpi-num">{r.modules}</div></div>
            <div className="kpi" style={{ animation: "none" }}><div className="kpi-lbl">生成耗时</div><div className="kpi-num">{r.gen_sec}<span className="kpi-unit">s</span></div></div>
          </div>
          <table className="tbl" style={{ marginBottom: 14 }}>
            <thead><tr><th>模块</th><th className="ctr">得分</th><th>AI 分析摘要</th></tr></thead>
            <tbody>
              {D.modules.slice(0, 6).map((m, i) => (
                <tr key={m}>
                  <td style={{ fontWeight: 600 }}>{m}</td>
                  <td className="ctr"><span className={spCls(r.score + (i % 3) - 1)}>{(r.score + (i % 3) - 1).toFixed(1)}</span></td>
                  <td style={{ color: "var(--ink-600)", fontSize: 12 }}>{i % 3 === 0 ? "维保记录完整性不足，建议加强台账管理。" : "整体符合标准，个别点位需复查。"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="card" style={{ boxShadow: "none" }}>
            <div className="card-h"><span className="card-t">综合评价（AI 生成）</span></div>
            <div className="card-b" style={{ fontSize: 13, color: "var(--ink-700)", lineHeight: 1.8 }}>
              本月检查整体得分 {r.score.toFixed(1)} 分，较上月提升 0.3 分。客户服务与安全管理表现稳定；机电运维模块问题集中在电梯机房维保记录与设备标识，建议列入下月专项整改。共发现严重问题 {r.id === "R-240905" ? 4 : 2} 项，已全部派发整改责任人。
            </div>
          </div>
        </div>
        <div className="drawer-f">
          <button className="btn">{I.down}导出 Word</button>
          <button className="btn">{I.down}导出 PDF</button>
          <button className="btn btn-primary" onClick={onClose}>关闭</button>
        </div>
      </div>
    </React.Fragment>
  );
}

// ============ 整改跟踪 ============
function PageRects() {
  const [kpi, setKpi] = useState(null);
  const rows = D.rects.filter(r => !kpi || r.status === kpi);
  return (
    <div className="page">
      <div className="phdr">
        <div>
          <h1>整改跟踪</h1>
          <div className="phdr-sub">AI 核查整改质量 · 闭环管理</div>
        </div>
        <div className="phdr-acts"><button className="btn">{I.down}导出</button></div>
      </div>

      <div className="kpi-row cols-5">
        {[["pending", "待整改", "ktag-muted"], ["submitted", "已提交待核查", "ktag-warn"], ["approved", "已通过", "ktag-ok"], ["overdue", "已逾期", "ktag-err"], ["disputed", "申诉中", "ktag-brand"]].map(([k, l, c]) => (
          <div key={k} className={"kpi kpi-click" + (kpi === k ? " kpi-active" : "")} onClick={() => setKpi(kpi === k ? null : k)}>
            <div className="kpi-lbl">{l}</div>
            <div className={"kpi-num" + (k === "overdue" ? " kpi-err" : "")}>{D.rectKpi[k]}</div>
            <span className="kpi-go">{I.chevR}</span>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr>
              <th>编号</th><th>项目 / 模块</th><th>检查项问题</th><th className="ctr">严重度</th>
              <th>责任人</th><th className="ctr">状态</th><th className="num">期限</th><th className="num">照片</th><th className="ctr">操作</th>
            </tr></thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.id}>
                  <td className="num" style={{ color: "var(--ink-600)", fontSize: 12 }}>{r.id}</td>
                  <td><div style={{ fontWeight: 600, fontSize: 13 }}>{r.project}</div><div style={{ fontSize: 12, color: "var(--ink-500)" }}>{r.module}</div></td>
                  <td style={{ maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.item}</td>
                  <td className="ctr">{r.severity === "serious" ? <span className="kt kt-err">严重</span> : <span className="kt kt-muted">一般</span>}</td>
                  <td>{r.assignee}</td>
                  <td className="ctr"><span className={"kt " + D.rectMeta[r.status].cls}>{D.rectMeta[r.status].label}</span></td>
                  <td className="num" style={{ color: r.status === "overdue" ? "var(--err-strong)" : "var(--ink-500)", fontWeight: r.status === "overdue" ? 700 : 500 }}>{r.due}</td>
                  <td className="num" style={{ color: "var(--ink-500)" }}>{r.photos}</td>
                  <td className="ctr"><a className="act-link">核查</a></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!rows.length && <div className="empty">{I.empty}该状态下暂无整改单</div>}
      </div>

      <div className="card">
        <div className="card-h"><span className="card-t">AI 核查演示 · 照片比对</span><span className="card-d">整改前 → 整改后</span></div>
        <div className="card-b" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          {[
            ["整改前 · 09-05", "var(--err-soft)", "var(--err-strong)", "消防通道被纸箱占用，宽度不足 1.2m", "RC-1023 · 蝶城·虹桥"],
            ["整改后 · 09-09（AI 置信度 96%）", "var(--ok-soft)", "var(--ok-strong)", "通道已清理，地面标线清晰，判定通过", "已自动通过核查"],
          ].map(([tag, bg, fg, desc, meta]) => (
            <div key={tag} style={{ border: "1px solid var(--ink-200)", borderRadius: "var(--r)", overflow: "hidden" }}>
              <div style={{ height: 120, background: `repeating-linear-gradient(45deg, var(--bg-muted) 0 10px, var(--bg-hover) 10px 20px)`, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--ink-400)", fontSize: 12 }}>
                现场照片占位
              </div>
              <div style={{ padding: "10px 12px" }}>
                <span className="kt" style={{ background: bg, color: fg, border: "1px solid " + bg }}>{tag}</span>
                <div style={{ fontSize: 12.5, color: "var(--ink-700)", marginTop: 7 }}>{desc}</div>
                <div style={{ fontSize: 11.5, color: "var(--ink-400)", marginTop: 3 }}>{meta}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============ 分析看板 ============
function PageAnalysis() {
  const [tab, setTab] = useState("cross");
  const a = D.analysis;
  const maxScore = 5;
  return (
    <div className="page">
      <div className="phdr">
        <div>
          <h1>分析看板</h1>
          <div className="phdr-sub">跨项目 / 跨时段对比 · AI 洞察</div>
        </div>
        <div className="phdr-acts">
          <button className="btn">{I.down}导出图片</button>
          <button className="btn">{I.down}导出 Excel</button>
        </div>
      </div>

      <div className="filters">
        <div className="seg">
          {[["cross", "跨项目对比"], ["period", "跨时段趋势"], ["radar", "模块画像"], ["history", "历史记录"]].map(([k, l]) =>
            <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>)}
        </div>
        <select className="sel" style={{ marginLeft: "auto" }}><option>2026 年 9 月</option><option>2026 年 8 月</option></select>
      </div>

      {tab === "cross" && (
        <React.Fragment>
          <div className="card">
            <div className="card-h"><span className="card-t">项目综合得分排名</span><span className="card-d">5 分制 · 按得分排序</span></div>
            <div style={{ padding: "12px 18px 16px" }}>
              {a.cross.map((p, i) => (
                <div key={p.project} className="hbar-row" style={{ gridTemplateColumns: "90px 1fr 40px" }}>
                  <span className="hbar-lbl">{p.project}</span>
                  <span className="hbar-track">
                    <span className="hbar-fill" style={{ width: (p.score / maxScore) * 100 + "%", background: p.score < 3.5 ? "var(--err)" : `var(--chart-ramp-${Math.min(i + 1, 5)})` }} />
                  </span>
                  <span className="hbar-val">{p.score.toFixed(1)}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="charts2">
            <div className="card">
              <div className="card-h"><span className="card-t">问题数 vs 整改率</span></div>
              <div style={{ padding: "12px 18px 16px" }}>
                {a.cross.map(p => (
                  <div key={p.project} className="hbar-row" style={{ gridTemplateColumns: "90px 1fr 44px" }}>
                    <span className="hbar-lbl">{p.project}</span>
                    <span className="sbar-track">
                      <span className="sbar-ok" style={{ width: p.rect_rate + "%" }} />
                      <span style={{ width: (100 - p.rect_rate) * 0.35 + "%", height: "100%", background: "var(--ink-300)" }} />
                    </span>
                    <span className="hbar-val">{p.rect_rate}%</span>
                  </div>
                ))}
                <div className="legend" style={{ marginTop: 10 }}><span><i style={{ background: "var(--ok)" }} />整改完成率</span><span><i style={{ background: "var(--ink-300)" }} />问题数（相对）</span></div>
              </div>
            </div>
            <div className="card">
              <div className="card-h"><span className="card-t">AI 洞察</span><span className="card-d">由分析 Agent 生成</span></div>
              <div style={{ padding: "14px 18px", display: "grid", gap: 12 }}>
                {a.insights.map((t, i) => (
                  <div key={i} style={{ display: "flex", gap: 10, fontSize: 13, color: "var(--ink-700)", lineHeight: 1.7 }}>
                    <span style={{ flexShrink: 0, width: 20, height: 20, borderRadius: "50%", background: "var(--brand-soft)", color: "var(--brand-ink)", fontSize: 11, fontWeight: 700, display: "inline-flex", alignItems: "center", justifyContent: "center", marginTop: 2 }}>{i + 1}</span>
                    {t}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </React.Fragment>
      )}

      {tab === "period" && (
        <div className="card">
          <div className="card-h"><span className="card-t">月度平均分趋势</span><span className="card-d">全项目 · 5 分制</span></div>
          <div style={{ padding: "16px 18px" }}>
            <div style={{ display: "flex", alignItems: "flex-end", gap: 18, height: 200, padding: "0 8px" }}>
              {a.period.map((m, i) => (
                <div key={m.month} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 13, fontWeight: 700, color: "var(--ink-800)", fontVariantNumeric: "tabular-nums" }}>{m.avg.toFixed(1)}</span>
                  <div style={{ width: "100%", maxWidth: 64, height: (m.avg / 5) * 150, background: i === a.period.length - 1 ? "var(--chart-1)" : "var(--chart-3)", borderRadius: "6px 6px 2px 2px", transition: "height .4s var(--ease)" }} />
                  <span style={{ fontSize: 12, color: "var(--ink-500)" }}>{m.month}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === "radar" && <RadarCard />}

      {tab === "history" && (
        <div className="card">
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>时间</th><th>操作</th><th>范围</th><th className="num">耗时</th><th className="ctr">操作</th></tr></thead>
              <tbody>
                {D.reports.map((r, i) => (
                  <tr key={r.id}>
                    <td className="num" style={{ color: "var(--ink-500)", fontSize: 12 }}>{r.created}</td>
                    <td>{i % 2 ? "跨项目对比报告" : "全项目综合分析"}</td>
                    <td>{i % 2 ? "全部项目" : r.project}</td>
                    <td className="num" style={{ color: "var(--ink-500)" }}>{20 + i * 3}s</td>
                    <td className="ctr"><a className="act-link">查看</a></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// SVG 雷达图（8 轴，双系列）
function RadarCard() {
  const a = D.analysis;
  const S = 320, C = S / 2, R = 110;
  const pt = (i, v, n) => {
    const ang = (Math.PI * 2 * i) / n - Math.PI / 2;
    return [C + Math.cos(ang) * R * (v / 5), C + Math.sin(ang) * R * (v / 5)];
  };
  const poly = vals => vals.map((v, i) => pt(i, v, vals.length).map(x => x.toFixed(1)).join(",")).join(" ");
  return (
    <div className="card">
      <div className="card-h"><span className="card-t">模块画像 · 云鹭湾 vs 项目均值</span><span className="card-d">8 模块 · 5 分制</span></div>
      <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 10, alignItems: "center", padding: "10px 18px 16px" }}>
        <svg viewBox={`0 0 ${S} ${S}`} style={{ width: 320, height: 320 }}>
          {[1, 2, 3, 4, 5].map(g => (
            <polygon key={g} points={poly(D.modules.map(() => g))} fill={g === 5 ? "none" : "var(--bg-muted)"} stroke="var(--ink-200)" strokeWidth="1" opacity={g === 5 ? 1 : 0.7} />
          ))}
          {a.radar.series.map(s => (
            <polygon key={s.name} points={poly(s.values)} fill={s.color} fillOpacity="0.14" stroke={s.color} strokeWidth="1.8" strokeDasharray={s.name.includes("均值") ? "5 4" : "none"} />
          ))}
          {a.radar.axes.map((ax, i) => {
            const [x, y] = pt(i, 5.9, a.radar.axes.length);
            const short = ax.replace("EHS及风险管理", "EHS");
            return <text key={ax} x={x} y={y} textAnchor="middle" dominantBaseline="middle" fontSize="10.5" fill="var(--ink-500)">{short}</text>;
          })}
        </svg>
        <div>
          <div className="legend" style={{ flexDirection: "column", alignItems: "flex-start", gap: 10 }}>
            {a.radar.series.map(s => (
              <span key={s.name} style={{ fontSize: 13, color: "var(--ink-700)", display: "inline-flex", alignItems: "center", gap: 8 }}>
                <i style={{ width: 14, height: 3, borderRadius: 2, background: s.color, display: "inline-block" }} />{s.name}
              </span>
            ))}
          </div>
          <div style={{ marginTop: 14, fontSize: 12.5, color: "var(--ink-500)", lineHeight: 1.8 }}>
            云鹭湾在安全管理（4.8）与财务管理（4.7）领先均值 0.5+；机电运维（3.8）低于均值 0.07，是最短板。
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { PageReports, PageRects, PageAnalysis });
