// pc-icons.jsx —— 统一的 16px 线性图标语言（stroke: currentColor, 1.7）
// 落地时替换为前端现有内联 SVG 风格，保持同一套视觉
const I = {
  logo: <svg viewBox="0 0 16 16"><path d="M2 13.5l3.2-4 2.4 2.3L14 4.5" /><path d="M10.5 4.5H14V8" /></svg>,
  grid: <svg viewBox="0 0 16 16"><rect x="2" y="2" width="5" height="5" rx="1" /><rect x="9" y="2" width="5" height="5" rx="1" /><rect x="2" y="9" width="5" height="5" rx="1" /><rect x="9" y="9" width="5" height="5" rx="1" /></svg>,
  list: <svg viewBox="0 0 16 16"><path d="M2 4h12M2 8h12M2 12h8" /></svg>,
  play: <svg viewBox="0 0 16 16"><path d="M3 2l10 6-10 6V2z" /></svg>,
  doc: <svg viewBox="0 0 16 16"><rect x="2.5" y="1.5" width="11" height="13" rx="1.5" /><path d="M5.5 5h5M5.5 8h5M5.5 11h3" /></svg>,
  loop: <svg viewBox="0 0 16 16"><path d="M13.5 8a5.5 5.5 0 11-1.6-3.9" /><path d="M13.5 2.5V5H11" /></svg>,
  chart: <svg viewBox="0 0 16 16"><path d="M2 14V9M6.3 14V4M10.6 14v-7M15 14V2" /></svg>,
  pulse: <svg viewBox="0 0 16 16"><path d="M1.5 8h3l1.7-4.5 3 9L11 8h3.5" /></svg>,
  star: <svg viewBox="0 0 16 16"><path d="M8 1.8l1.9 3.9 4.3.6-3.1 3 .7 4.3L8 11.6l-3.8 2-.7-4.3-3.1-3 4.3-.6z" /></svg>,
  gear: <svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="2.2" /><path d="M8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M3.4 12.6l1.4-1.4M11.2 4.8l1.4-1.4" /></svg>,
  bell: <svg viewBox="0 0 16 16"><path d="M3.5 11.5h9c-1-1-1.5-2.2-1.5-4a3 3 0 10-6 0c0 1.8-.5 3-1.5 4z" /><path d="M6.8 13.5a1.3 1.3 0 002.4 0" /></svg>,
  shield: <svg viewBox="0 0 16 16"><path d="M2 4l6-2 6 2v5c0 3.2-6 5-6 5s-6-1.8-6-5V4z" /></svg>,
  chevR: <svg viewBox="0 0 16 16"><path d="M6 3l5 5-5 5" /></svg>,
  chevD: <svg viewBox="0 0 16 16"><path d="M4 6l4 4 4-4" /></svg>,
  x: <svg viewBox="0 0 16 16"><path d="M4 4l8 8M12 4l-8 8" /></svg>,
  down: <svg viewBox="0 0 16 16"><path d="M2 3v10h12M8 7v6M5 10l3 3 3-3" /></svg>,
  up: <svg viewBox="0 0 16 16"><path d="M8 3l3.5 3.5M8 3v10M8 13H4.5" /></svg>,
  trendUp: <svg viewBox="0 0 16 16"><path d="M2 12l4-5 3 3 5-7" /><path d="M10.5 3H14v3.5" /></svg>,
  trendDown: <svg viewBox="0 0 16 16"><path d="M2 4l4 5 3-3 5 7" /><path d="M10.5 13H14V9.5" /></svg>,
  trendFlat: <svg viewBox="0 0 16 16"><path d="M2 8h12" /></svg>,
  search: <svg viewBox="0 0 16 16"><circle cx="7" cy="7" r="4.5" /><path d="M10.5 10.5L14 14" /></svg>,
  filter: <svg viewBox="0 0 16 16"><path d="M2 3h12l-4.5 5.5V13L6.5 11V8.5z" /></svg>,
  plus: <svg viewBox="0 0 16 16"><path d="M8 3v10M3 8h10" /></svg>,
  check: <svg viewBox="0 0 16 16"><path d="M3 8.5l3.5 3.5L13 5" /></svg>,
  clock: <svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" /><path d="M8 4.5V8l2.5 1.5" /></svg>,
  alert: <svg viewBox="0 0 16 16"><path d="M8 1.8l6.5 11.7H1.5z" /><path d="M8 6.5v3M8 11.8v.2" /></svg>,
  cam: <svg viewBox="0 0 16 16"><rect x="1.5" y="4" width="13" height="9.5" rx="1.5" /><circle cx="8" cy="8.7" r="2.6" /><path d="M5.5 4l1-2h3l1 2" /></svg>,
  user: <svg viewBox="0 0 16 16"><circle cx="8" cy="5" r="3.2" /><path d="M1.8 15c0-3.4 2.8-6.2 6.2-6.2s6.2 2.8 6.2 6.2" /></svg>,
  spark: <svg viewBox="0 0 16 16"><path d="M8 2l1.2 3.3L12.5 6.5 9.2 7.7 8 11l-1.2-3.3L3.5 6.5l3.3-1.2z" /><path d="M12.8 10.5l.5 1.4 1.4.5-1.4.5-.5 1.4-.5-1.4-1.4-.5 1.4-.5z" /></svg>,
  empty: <svg viewBox="0 0 16 16"><rect x="2" y="3" width="12" height="9" rx="1.5" /><path d="M5 1.5v3M11 1.5v3M2 6.5h12" /></svg>,
};

// 共享小组件
function Icon({ d, size }) {
  const el = I[d];
  if (!el) return null;
  return <span style={{ display: "inline-flex", width: size || 16, height: size || 16 }}>{el}</span>;
}

Object.assign(window, { I, Icon });
