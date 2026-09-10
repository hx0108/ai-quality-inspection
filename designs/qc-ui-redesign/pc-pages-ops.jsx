// pc-pages-ops.jsx —— 模型监控 + 效果评估 + 系统设置
const { useState } = React;

// ============ 模型监控 ============
function PageLlm() {
  const d = D.llm;
  const maxTrend = Math.max(...d.trend);
  return (
    <div className="page">
      <div className="phdr">
        <div>
          <h1>模型监控</h1>
          <div className="phdr-sub">5 个 Agent 的 LLM 调用 · 成本与稳定性</div>
        </div>
        <div className="phdr-acts"><button className="btn">{I.down}导出日志</button></div>
      </div>

      <div className="kpi-row cols-5">
        <div className="kpi"><div className="kpi-lbl">24h 调用量</div><div className="kpi-num">{d.kpi.calls_24h.toLocaleString()}</div><div className="kpi-tags"><span className="ktag ktag-muted">峰值 22 时</span></div></div>
        <div className="kpi"><div className="kpi-lbl">成功率</div><div className="kpi-num">{d.kpi.success_rate}<span className="kpi-unit">%</span></div><div className="kpi-tags"><span className="ktag ktag-ok">健康</span></div></div>
        <div className="kpi"><div className="kpi-lbl">平均延迟</div><div className="kpi-num">{d.kpi.avg_latency}<span className="kpi-unit">s</span></div><div className="kpi-tags"><span className="ktag ktag-muted">P95 8.4s</span></div></div>
        <div className="kpi"><div className="kpi-lbl">24h Token</div><div className="kpi-num" style={{ fontSize: 24 }}>{d.kpi.tokens_24h}</div><div className="kpi-tags"><span className="ktag ktag-muted">≈ ¥86</span></div></div>
        <div className="kpi"><div className="kpi-lbl">24h 失败</div><div className="kpi-num kpi-err">{d.kpi.failed_24h}</div><div className="kpi-tags"><span className="ktag ktag-warn">2 次自动重试恢复</span></div></div>
      </div>

      <div className="charts2">
        <div className="card">
          <div className="card-h"><span className="card-t">24h 调用量曲线</span><span className="card-d">每小时</span></div>
          <div style={{ padding: "12px 18px 16px" }}>
            {d.trend.map((v, i) => (
              <div key={i} className="hbar-row" style={{ gridTemplateColumns: "28px 1fr 34px", padding: "2px 0" }}>
                <span className="hbar-lbl" style={{ fontVariantNumeric: "tabular-nums" }}>{d.trendLabels[i]}</span>
                <span className="hbar-track" style={{ height: 10 }}>
                  <span className="hbar-fill" style={{ width: (v / maxTrend) * 100 + "%", background: i >= 8 ? "var(--chart-1)" : "var(--chart-3)" }} />
                </span>
                <span className="hbar-val">{v}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-h"><span className="card-t">按 Agent 分布</span><span className="card-d">24h 调用占比</span></div>
          <div style={{ padding: "14px 18px" }}>
            {d.byAgent.map((g, i) => (
              <div key={g.name} style={{ marginBottom: 14 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 5 }}>
                  <span style={{ color: "var(--ink-800)", fontWeight: 500 }}>{g.name}</span>
                  <span style={{ color: "var(--ink-500)", fontVariantNumeric: "tabular-nums" }}>{g.share}% · 均 {g.latency}s</span>
                </div>
                <div className="hbar-track" style={{ height: 8 }}>
                  <div className="hbar-fill" style={{ width: g.share + "%", background: `var(--chart-${i + 1})` }} />
                </div>
              </div>
            ))}
            <div style={{ marginTop: 6, padding: "10px 12px", background: "var(--bg-muted)", borderRadius: "var(--r)", fontSize: 12.5, color: "var(--ink-600)", lineHeight: 1.7 }}>
              报告与分析 Agent 走 DeepSeek（长文本推理强），评分与核查走 Qwen 系列（结构化任务性价比高）——按任务特点分模型，成本比全用旗舰模型低约 70%。
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-h"><span className="card-t">最近调用日志</span><span className="card-d">实时</span></div>
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr><th className="num">时间</th><th className="ctr">Agent</th><th>模型</th><th className="num">Tokens</th><th className="num">延迟</th><th className="ctr">状态</th></tr></thead>
            <tbody>
              {d.logs.map((l, i) => (
                <tr key={i}>
                  <td className="num" style={{ color: "var(--ink-500)", fontSize: 12 }}>{l.time}</td>
                  <td className="ctr"><span className="kt kt-brand">{l.agent}</span></td>
                  <td style={{ fontFamily: "var(--mono)", fontSize: 12 }}>{l.model}</td>
                  <td className="num">{l.tokens.toLocaleString()}</td>
                  <td className="num" style={{ color: l.latency > 15 ? "var(--warn-strong)" : "var(--ink-600)" }}>{l.latency ? l.latency.toFixed(1) + "s" : "—"}</td>
                  <td className="ctr"><span className={"kt " + D.llmLogMeta[l.status].cls}>{D.llmLogMeta[l.status].label}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ============ 效果评估 ============
function PageAiMetrics() {
  const a = D.ai;
  const maxC = Math.max(...a.calibration.map(c => Math.max(c.ai, c.human)));
  return (
    <div className="page">
      <div className="phdr">
        <div>
          <h1>效果评估</h1>
          <div className="phdr-sub">AI 评分 vs 人工复核 · 持续校准</div>
        </div>
        <div className="phdr-acts"><button className="btn">{I.down}导出评估报告</button></div>
      </div>

      <div className="kpi-row cols-6">
        {a.kpi.map(k => (
          <div key={k.lbl} className="kpi">
            <div className="kpi-lbl">{k.lbl}</div>
            <div className="kpi-num" style={{ fontSize: 26 }}>{k.val}</div>
            <div className="kpi-tags">
              <span className={"kpi-trend " + k.trend}>{k.trend === "up" ? I.trendUp : k.trend === "down" ? I.trendDown : I.trendFlat}{k.delta}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="charts2">
        <div className="card">
          <div className="card-h"><span className="card-t">评分分布校准</span><span className="card-d">AI vs 人工 · 样本数</span></div>
          <div style={{ padding: "14px 18px 16px" }}>
            {a.calibration.map(c => (
              <div key={c.band} style={{ marginBottom: 13 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--ink-600)", marginBottom: 4 }}>
                  <span>{c.band} 分段</span>
                  <span style={{ fontVariantNumeric: "tabular-nums" }}>AI {c.ai} · 人工 {c.human}</span>
                </div>
                <div style={{ display: "grid", gap: 3 }}>
                  <div className="hbar-track" style={{ height: 7 }}><div className="hbar-fill" style={{ width: (c.ai / maxC) * 100 + "%", background: "var(--chart-1)" }} /></div>
                  <div className="hbar-track" style={{ height: 7 }}><div className="hbar-fill" style={{ width: (c.human / maxC) * 100 + "%", background: "var(--ink-300)" }} /></div>
                </div>
              </div>
            ))}
            <div className="legend"><span><i style={{ background: "var(--chart-1)" }} />AI 评分</span><span><i style={{ background: "var(--ink-300)" }} />人工复核</span></div>
          </div>
        </div>

        <div className="card">
          <div className="card-h"><span className="card-t">分模块人机一致率</span><span className="card-d">近 30 天</span></div>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>模块</th><th className="ctr">一致率</th><th className="num">样本</th></tr></thead>
              <tbody>
                {a.consistency.map(c => (
                  <tr key={c.module}>
                    <td style={{ fontWeight: 500 }}>{c.module}</td>
                    <td className="ctr">
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                        <span className="hbar-track" style={{ width: 90, height: 7 }}>
                          <span className="hbar-fill" style={{ width: c.agree + "%", background: c.agree < 90 ? "var(--warn)" : "var(--chart-1)" }} />
                        </span>
                        <b style={{ fontSize: 12.5, color: c.agree < 90 ? "var(--warn-strong)" : "var(--ink-800)", fontVariantNumeric: "tabular-nums" }}>{c.agree}%</b>
                      </span>
                    </td>
                    <td className="num" style={{ color: "var(--ink-500)" }}>{c.samples}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-h"><span className="card-t">评估说明</span></div>
        <div className="card-b" style={{ fontSize: 12.5, color: "var(--ink-500)", lineHeight: 1.8 }}>
          一致率 = 人工复核与 AI 评分分差 ≤ 0.3 的比例。机电运维一致率偏低（88%），主因是现场照片质量影响 Qwen-VL 判断，已列入下轮 Prompt 优化。样本来源为开启强制复核的项目（复核覆盖率 38%）。
        </div>
      </div>
    </div>
  );
}

// ============ 系统设置 ============
function PageSettings() {
  const [tab, setTab] = useState("users");
  return (
    <div className="page">
      <div className="phdr">
        <div>
          <h1>系统设置</h1>
          <div className="phdr-sub">用户、项目与检查标准配置</div>
        </div>
        <div className="phdr-acts">
          {tab === "users" && <button className="btn btn-primary">{I.plus}新建用户</button>}
          {tab === "projects" && <button className="btn btn-primary">{I.plus}新建项目</button>}
        </div>
      </div>

      <div className="filters">
        <div className="seg">
          {[["users", "用户管理"], ["projects", "项目管理"], ["standard", "检查标准"], ["notify", "通知设置"]].map(([k, l]) =>
            <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>)}
        </div>
      </div>

      {tab === "users" && (
        <div className="card">
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>姓名</th><th>账号</th><th>角色</th><th>负责项目</th><th className="ctr">状态</th><th className="ctr">操作</th></tr></thead>
              <tbody>
                {D.users.map(u => (
                  <tr key={u.id}>
                    <td style={{ fontWeight: 600 }}>{u.name}</td>
                    <td style={{ fontFamily: "var(--mono)", fontSize: 12.5 }}>{u.account}</td>
                    <td>{u.role === "系统管理员" ? <span className="kt kt-brand">{u.role}</span> : u.role === "检查员" ? <span className="kt kt-muted">{u.role}</span> : <span className="kt kt-warn">{u.role}</span>}</td>
                    <td style={{ color: "var(--ink-600)" }}>{u.projects}</td>
                    <td className="ctr">{u.active ? <span className="dot dot-ok" title="启用" /> : <span className="dot dot-muted" title="停用" />}</td>
                    <td className="ctr" style={{ whiteSpace: "nowrap" }}><a className="act-link">编辑</a><span style={{ color: "var(--ink-200)", margin: "0 6px" }}>|</span><a className="act-link">重置密码</a></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "projects" && (
        <div className="kpi-row" style={{ gridTemplateColumns: "repeat(3, 1fr)", marginBottom: 0 }}>
          {D.projectsCfg.map(p => (
            <div key={p.name} className="card" style={{ margin: 0, padding: "16px 18px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ display: "inline-flex", alignItems: "center", gap: 7, fontSize: 14.5, fontWeight: 700, color: "var(--ink-900)" }}>{I.shield}{p.name}</span>
                <span className={"switch" + (p.enabled ? " on" : "")}><i /></span>
              </div>
              <dl className="desc" style={{ marginTop: 12 }}>
                <dt>检查项</dt><dd>{p.modules} 模块 / {p.items} 项</dd>
                <dt>对接人</dt><dd>{p.contact}</dd>
              </dl>
            </div>
          ))}
        </div>
      )}

      {tab === "standard" && (
        <div className="card">
          <div className="card-h"><span className="card-t">砺质行动检查标准 · 8 模块</span><span className="card-d">导入了 砺质行动检查标准（8月）.xlsx</span></div>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>模块</th><th className="num">权重</th><th className="num">检查项数</th><th className="ctr">状态</th></tr></thead>
              <tbody>
                {D.modules.map((m, i) => (
                  <tr key={m}>
                    <td style={{ fontWeight: 600 }}>{m}</td>
                    <td className="num">{[0.15, 0.14, 0.13, 0.12, 0.14, 0.12, 0.1, 0.1][i].toFixed(2)}</td>
                    <td className="num">{[12, 12, 10, 12, 14, 12, 12, 12][i]}</td>
                    <td className="ctr"><span className="kt kt-ok">已启用</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "notify" && (
        <div className="card">
          <div className="card-b" style={{ display: "grid", gap: 14, maxWidth: 560 }}>
            {[["评分完成通知", "AI 评分完成后通知项目经理"], ["逾期升级", "整改逾期自动升级通知管理员"], ["报告生成通知", "报告生成完成后通知相关人员"], ["申诉提醒", "整改申诉 2 小时未处理提醒管理员"]].map(([t, d], i) => (
              <div key={t} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
                <div>
                  <div style={{ fontSize: 13.5, fontWeight: 600, color: "var(--ink-900)" }}>{t}</div>
                  <div style={{ fontSize: 12, color: "var(--ink-500)", marginTop: 2 }}>{d}</div>
                </div>
                <span className={"switch on"}><i /></span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

Object.assign(window, { PageLlm, PageAiMetrics, PageSettings });
