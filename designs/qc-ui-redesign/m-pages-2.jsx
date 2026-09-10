// m-pages-2.jsx —— 巡检(列表式) / 巡检(卡片式) / AI 评分
const { useState } = React;

// ============ 05 巡检 · 列表式 ============
function MInspect({ go }) {
  const [ans, setAns] = useState({ "5.1": "pass", "5.2": "fail" });
  const items = [
    { id: "5.1", name: "垃圾清运及时性", std: "日产日清，无堆积", ai: null },
    { id: "5.2", name: "垃圾桶完好无渗漏", std: "桶身完好、无破损渗漏、标识清晰", ai: "历史 3 次检查中此项目 2 次发现问题，建议拍照留证" },
    { id: "5.3", name: "大堂/电梯轿厢卫生", std: "地面干净、轿厢无异味、无乱贴乱画", ai: null },
  ];
  const set = (id, v) => setAns(a => ({ ...a, [id]: a[id] === v ? undefined : v }));
  return (
    <React.Fragment>
      <MNavBar title="环境管理 · 检查中" />
      <div className="m-body">
        <div style={{ padding: "12px 14px 0" }}>
          <div className="m-note">{I.spark}<span>AI 提示：本模块上月发现 2 个问题，重点核查垃圾清运与桶身完好</span></div>
        </div>
        <div className="m-pad">
          {items.map(it => (
            <div key={it.id} className="m-card" style={{ padding: "13px 14px" }}>
              <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                <span style={{ flexShrink: 0, fontSize: 11, fontWeight: 700, fontFamily: "var(--mono)", color: "var(--brand-ink)", background: "var(--brand-soft)", borderRadius: 5, padding: "2px 6px", marginTop: 1 }}>{it.id}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14.5, fontWeight: 700, color: "var(--ink-900)" }}>{it.name}</div>
                  <div style={{ fontSize: 12, color: "var(--ink-500)", marginTop: 3, lineHeight: 1.6 }}>{it.std}</div>
                </div>
              </div>
              {it.ai && <div className="m-note" style={{ marginTop: 9 }}>{I.spark}<span>{it.ai}</span></div>}
              {ans[it.id] === "fail" && (
                <div style={{ marginTop: 10, display: "grid", gap: 8 }}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 86px", gap: 8 }}>
                    <div className="m-upload">{I.cam}<span>问题照片</span></div>
                    <div className="m-upload">{I.cam}<span>问题照片</span></div>
                    <input className="m-ipt" style={{ height: 86, textAlign: "center", fontSize: 12 }} placeholder="位置" />
                  </div>
                  <textarea className="m-ipt" style={{ height: 54, paddingTop: 10, resize: "none", fontSize: 13 }} placeholder="问题描述" defaultValue="3 号楼垃圾桶桶盖破损" />
                </div>
              )}
              <div className="m-check-row" style={{ marginTop: 11 }}>
                <button className={"m-check-btn pass" + (ans[it.id] === "pass" ? " on" : "")} onClick={() => set(it.id, "pass")}>{I.check}合格</button>
                <button className={"m-check-btn fail" + (ans[it.id] === "fail" ? " on" : "")} onClick={() => set(it.id, "fail")}>{I.alert}有问题</button>
              </div>
            </div>
          ))}
          <div style={{ height: 56 }} />
        </div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, padding: "10px 14px 14px", background: "var(--bg-card)", borderTop: "1px solid var(--ink-200)", display: "flex", gap: 10, alignItems: "center" }}>
        <div style={{ fontSize: 12, color: "var(--ink-500)", lineHeight: 1.5 }}>
          进度 <b style={{ color: "var(--ink-900)", fontVariantNumeric: "tabular-nums" }}>2/3</b><br />
          <span style={{ color: "var(--err-strong)" }}>问题 1 个</span>
        </div>
        <button className="m-btn m-btn-primary" style={{ flex: 1 }}>提交本模块</button>
      </div>
    </React.Fragment>
  );
}

// ============ 06 巡检 · 卡片式（单题翻页） ============
function MInspectCard({ go }) {
  const [ans, setAns] = useState(null);
  return (
    <React.Fragment>
      <MNavBar title="逐项检查" />
      <div className="m-body">
        <div className="m-pad">
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
            <span className="m-track" style={{ flex: 1 }}><span className="m-fill" style={{ width: "38%" }} /></span>
            <span style={{ fontSize: 12.5, color: "var(--ink-500)", fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" }}>3 / 8</span>
          </div>

          <div className="m-card" style={{ padding: 0, overflow: "hidden" }}>
            <div style={{ padding: "18px 16px 14px", background: "var(--bg-card)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <span style={{ fontSize: 11, fontWeight: 700, fontFamily: "var(--mono)", color: "var(--brand-ink)", background: "var(--brand-soft)", borderRadius: 5, padding: "2px 6px" }}>5.2</span>
                <span className="kt kt-muted">环境管理</span>
              </div>
              <div style={{ fontSize: 18, fontWeight: 800, color: "var(--ink-900)", lineHeight: 1.45 }}>垃圾桶完好无渗漏</div>
              <div style={{ fontSize: 13, color: "var(--ink-500)", marginTop: 7, lineHeight: 1.7 }}>桶身完好、无破损渗漏、标识清晰；垃圾不满溢。</div>
            </div>
            <div style={{ height: 190, background: "repeating-linear-gradient(45deg, var(--bg-muted) 0 12px, var(--bg-hover) 12px 24px)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 8, color: "var(--ink-400)", fontSize: 12.5, borderTop: "1px solid var(--ink-100)", borderBottom: "1px solid var(--ink-100)" }}>
              <span style={{ width: 22, height: 22, display: "inline-flex" }}>{I.cam}</span>
              拍照留证（自动加时间地点水印）
            </div>
          </div>

          {ans === "fail" && (
            <div className="m-note" style={{ marginTop: 12, background: "var(--err-soft)", color: "var(--err-strong)" }}>
              {I.alert}<span>记录问题：将自动生成整改单并通知责任人</span>
            </div>
          )}

          <div className="m-check-row" style={{ marginTop: 16, gap: 12 }}>
            <button className={"m-check-btn pass" + (ans === "pass" ? " on" : "")} style={{ height: 56, fontSize: 16 }} onClick={() => setAns("pass")}>{I.check}合格</button>
            <button className={"m-check-btn fail" + (ans === "fail" ? " on" : "")} style={{ height: 56, fontSize: 16 }} onClick={() => setAns("fail")}>{I.alert}有问题</button>
          </div>
          <button className="m-btn m-btn-primary m-btn-block" style={{ marginTop: 12 }} onClick={() => go("scoring")}>下一项</button>
          <div style={{ textAlign: "center", marginTop: 12 }}>
            <a style={{ fontSize: 12.5, color: "var(--ink-500)", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 5 }}>{I.spark}语音备注</a>
          </div>
        </div>
      </div>
    </React.Fragment>
  );
}

// ============ 07 AI 评分 ============
function MScoring({ go }) {
  const mods = [
    ["客户服务", 4.6], ["安全管理", 4.8], ["EHS及风险管理", 4.2], ["环境管理", 3.9],
    ["机电运维", 3.4], ["设施维护", 4.1], ["综合管理", 4.4], ["财务管理", 4.7],
  ];
  return (
    <React.Fragment>
      <MNavBar title="AI 评分结果" />
      <div className="m-body">
        <div className="m-pad">
          <div className="m-card" style={{ padding: "18px 16px 14px", textAlign: "center" }}>
            <div style={{ fontSize: 12.5, color: "var(--ink-500)" }}>云鹭湾 · 本次检查总分</div>
            <div style={{ fontSize: 52, fontWeight: 800, color: "var(--ink-900)", letterSpacing: "-2px", lineHeight: 1.15, fontVariantNumeric: "tabular-nums" }}>
              4.3<span style={{ fontSize: 18, fontWeight: 600, color: "var(--ink-400)", letterSpacing: 0 }}> / 5.0</span>
            </div>
            <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 6 }}>
              <span className="kt kt-err">严重 2</span>
              <span className="kt kt-warn">一般 12</span>
              <span className="kt kt-muted">较上月 +0.2</span>
            </div>
          </div>

          <div className="m-card">
            <div className="m-card-h"><span className="m-card-t">模块得分</span><span className="card-d">点击查看明细</span></div>
            <div style={{ padding: "8px 14px 12px" }}>
              {mods.map(([m, s]) => (
                <div key={m} style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 0" }}>
                  <span style={{ fontSize: 12.5, color: "var(--ink-700)", width: 96, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{m.replace("EHS及风险管理", "EHS")}</span>
                  <span className="m-track" style={{ flex: 1 }}>
                    <span className="m-fill" style={{ width: (s / 5) * 100 + "%", background: s < 3.5 ? "var(--err)" : "var(--chart-1)" }} />
                  </span>
                  <span className={"sp " + (s >= 4.5 ? "sp-hi" : s >= 3.5 ? "sp-mid" : "sp-lo")} style={{ minWidth: 36 }}>{s.toFixed(1)}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="m-note" style={{ marginBottom: 12 }}>
            {I.spark}<span>AI 建议：机电运维（3.4）为主要失分项，电梯机房维保记录缺失 2 处，建议列入本月整改。</span>
          </div>

          <div style={{ display: "flex", gap: 10 }}>
            <button className="m-btn" style={{ flex: 1 }}>对评分有异议</button>
            <button className="m-btn m-btn-primary" style={{ flex: 1.4 }} onClick={() => go("report")}>生成报告</button>
          </div>
        </div>
      </div>
    </React.Fragment>
  );
}

Object.assign(window, { MInspect, MInspectCard, MScoring });
