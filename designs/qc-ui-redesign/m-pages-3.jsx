// m-pages-3.jsx —— 报告 / 整改列表 / 整改提交
const { useState } = React;

// ============ 08 报告 ============
function MReport({ go }) {
  return (
    <React.Fragment>
      <MNavBar title="检查报告" />
      <div className="m-body">
        <div className="m-pad">
          <div className="m-card" style={{ padding: "14px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 15.5, fontWeight: 800, color: "var(--ink-900)" }}>云鹭湾 9 月品质检查报告</span>
              <span className="kt kt-ok">已生成</span>
            </div>
            <div style={{ fontSize: 12, color: "var(--ink-500)", marginTop: 4 }}>生成耗时 96s · 2026-09-10 09:30</div>
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button className="m-btn" style={{ flex: 1, height: 36, fontSize: 13 }}>导出 Word</button>
              <button className="m-btn" style={{ flex: 1, height: 36, fontSize: 13 }}>导出 PDF</button>
            </div>
          </div>

          <div className="m-card">
            <div className="m-card-h" style={{ paddingBottom: 10, borderBottom: "1px solid var(--ink-100)" }}>
              <span className="m-card-t">模块分析</span><span className="card-d">AI 生成</span>
            </div>
            <details open style={{ borderBottom: "1px solid var(--ink-100)" }}>
              <summary style={{ padding: "12px 14px", fontSize: 14, fontWeight: 600, color: "var(--ink-900)", cursor: "pointer", display: "flex", alignItems: "center", gap: 8, listStyle: "none" }}>
                <span className={"sp sp-lo"} style={{ minWidth: 34 }}>3.4</span>机电运维<span style={{ marginLeft: "auto", color: "var(--err-strong)", fontSize: 11.5, fontWeight: 700 }}>严重 1 · 一般 4</span>
              </summary>
              <div style={{ padding: "0 14px 13px", fontSize: 13, color: "var(--ink-600)", lineHeight: 1.75 }}>
                电梯机房维保记录缺失 2 处（3 号、5 号楼），设备标识不完整；配电井未见巡查记录。建议本月专项补齐台账并复查。
              </div>
            </details>
            <details style={{ borderBottom: "1px solid var(--ink-100)" }}>
              <summary style={{ padding: "12px 14px", fontSize: 14, fontWeight: 600, color: "var(--ink-900)", cursor: "pointer", display: "flex", alignItems: "center", gap: 8, listStyle: "none" }}>
                <span className="sp sp-mid" style={{ minWidth: 34 }}>3.9</span>环境管理<span style={{ marginLeft: "auto", color: "var(--ink-400)", fontSize: 11.5, fontWeight: 700 }}>一般 3</span>
              </summary>
              <div style={{ padding: "0 14px 13px", fontSize: 13, color: "var(--ink-600)", lineHeight: 1.75 }}>
                垃圾清运整体及时，3 号楼桶盖破损已现场记录；大堂雨幕有明显积尘，已提醒保洁加频。
              </div>
            </details>
            <details>
              <summary style={{ padding: "12px 14px", fontSize: 14, fontWeight: 600, color: "var(--ink-900)", cursor: "pointer", display: "flex", alignItems: "center", gap: 8, listStyle: "none" }}>
                <span className="sp sp-hi" style={{ minWidth: 34 }}>4.8</span>安全管理<span style={{ marginLeft: "auto", color: "var(--ink-400)", fontSize: 11.5, fontWeight: 700 }}>无问题</span>
              </summary>
              <div style={{ padding: "0 14px 13px", fontSize: 13, color: "var(--ink-600)", lineHeight: 1.75 }}>
                消防通道畅通，监控中心值班记录完整，门禁巡检正常。
              </div>
            </details>
          </div>

          <div className="m-card" style={{ padding: "14px" }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: "var(--ink-900)", marginBottom: 8 }}>综合评价</div>
            <div style={{ fontSize: 13, color: "var(--ink-600)", lineHeight: 1.8 }}>
              本次检查总分 4.3，较上月提升 0.2。客户服务、财务管理持续领先；机电运维为主要短板，已生成 5 张整改单并派发至责任人。
            </div>
          </div>
        </div>
      </div>
      <MTabbar active="reports" go={go} />
    </React.Fragment>
  );
}

// ============ 09 整改列表 ============
function MRects({ go }) {
  const [filter, setFilter] = useState("all");
  const rows = [
    ["RC-1024", "梧桐郡 · 电梯机房维保记录", "overdue", "09-12"],
    ["RC-1021", "云鹭湾 · 垃圾清运不及时", "approved", "09-09"],
    ["RC-1023", "蝶城·虹桥 · 消防通道堆物", "submitted", "09-10"],
  ].filter(r => filter === "all" || r[2] === filter);
  return (
    <React.Fragment>
      <MNavBar title="整改跟踪" />
      <div className="m-body">
        <div style={{ padding: "10px 14px 0" }}>
          <div className="seg">
            {[["all", "全部"], ["submitted", "待核查"], ["approved", "已通过"], ["overdue", "逾期"]].map(([k, l]) =>
              <button key={k} className={filter === k ? "on" : ""} onClick={() => setFilter(k)}>{l}</button>)}
          </div>
        </div>
        <div className="m-pad">
          {rows.map(([id, desc, st, due]) => (
            <div key={id} className="m-card" style={{ padding: "13px 14px", cursor: "pointer" }} onClick={() => go("rectsubmit")}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--ink-400)" }}>{id}</span>
                <span className={"kt " + D.rectMeta[st].cls}>{D.rectMeta[st].label}</span>
              </div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "var(--ink-900)", marginTop: 6, lineHeight: 1.5 }}>{desc}</div>
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 9, fontSize: 12, color: st === "overdue" ? "var(--err-strong)" : "var(--ink-500)" }}>
                <span>期限 {due}</span>
                <span style={{ color: "var(--brand)", fontWeight: 600 }}>{st === "approved" ? "查看核查结果" : "去整改"}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
      <MTabbar active="rects" go={go} />
    </React.Fragment>
  );
}

// ============ 10 整改提交 ============
function MRectSubmit({ go }) {
  const [photos, setPhotos] = useState(1);
  return (
    <React.Fragment>
      <MNavBar title="提交整改" />
      <div className="m-body">
        <div className="m-pad">
          <div className="m-card" style={{ padding: "13px 14px", borderLeft: "3px solid var(--err)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span className="kt kt-err">原始问题</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--ink-400)" }}>RC-1024</span>
            </div>
            <div style={{ fontSize: 14, fontWeight: 600, color: "var(--ink-900)", marginTop: 8 }}>梧桐郡 · 3.2 电梯机房维保记录缺失</div>
            <div style={{ fontSize: 12.5, color: "var(--ink-500)", marginTop: 4, lineHeight: 1.7 }}>3 号楼电梯机房 8 月维保记录缺失，5 号楼设备标识不完整。</div>
          </div>

          <div className="m-card" style={{ padding: "13px 14px" }}>
            <div style={{ fontSize: 13.5, fontWeight: 700, color: "var(--ink-900)", marginBottom: 10 }}>整改后照片 <span style={{ color: "var(--ink-400)", fontWeight: 500, fontSize: 11.5 }}>（自动加水印，至少 1 张）</span></div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
              <div className="m-upload" style={{ borderColor: "var(--ok-border)", color: "var(--ok-strong)", background: "var(--ok-soft)" }}>{I.check}<span>已拍 1 张</span></div>
              <div className="m-upload" onClick={() => setPhotos(p => p + 1)}>{I.cam}<span>继续拍照</span></div>
              <div className="m-upload">{I.doc}<span>从相册选</span></div>
            </div>
            <div style={{ marginTop: 9, fontSize: 11.5, color: "var(--ink-400)", display: "flex", alignItems: "center", gap: 5 }}>
              {I.spark}AI 核查：提交后将自动比对问题照片判断整改质量
            </div>
          </div>

          <div className="m-card" style={{ padding: "13px 14px" }}>
            <div style={{ fontSize: 13.5, fontWeight: 700, color: "var(--ink-900)", marginBottom: 9 }}>整改说明</div>
            <textarea className="m-ipt" style={{ height: 84, paddingTop: 11, resize: "none", fontSize: 13.5 }} defaultValue="已完成 3 号楼 8 月维保记录补录，5 号楼设备标识已更换为标准标识牌。" />
          </div>

          <button className="m-btn m-btn-primary m-btn-block">提交整改</button>
          <div style={{ textAlign: "center", marginTop: 10 }}>
            <a style={{ fontSize: 12.5, color: "var(--ink-500)", cursor: "pointer" }} onClick={() => go("rects")}>对核查结果有异议？发起申诉</a>
          </div>
        </div>
      </div>
    </React.Fragment>
  );
}

Object.assign(window, { MReport, MRects, MRectSubmit });
