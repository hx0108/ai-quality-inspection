/**
 * chartTheme.js —— ECharts 统一主题（设计系统 v2 · 青绿品牌色）
 * 令牌与 App.vue :root / designs/qc-ui-redesign/qc-theme.css 对齐。
 * 用法：
 *   import { CHART, applyChartTheme } from '@/utils/chartTheme'
 *   // 新图表：option.color = CHART.series; 手写系列色用 CHART.*
 *   // 后端返回的 option（分析看板）：applyChartTheme(option) 后再 setOption
 */

/* 品牌单色系（量级深→浅） */
export const RAMP = ['#0a6b62', '#0f8a80', '#35a398', '#6fbcb2', '#a5d8d0']

/* 多系列色板（品牌系 + 少量功能性延伸，无彩虹） */
export const SERIES = ['#0f8a80', '#35a398', '#6fbcb2', '#0a6b62', '#a5d8d0', '#8e8e9a']

/* 语义色（好=绿 警示=琥珀 严重=红 中性=灰） */
export const SEMANTIC = {
  ok: '#27945b',
  warn: '#b07a12',
  err: '#e5484d',
  neutral: '#c9c9d1',
  okSoft: '#e5f4ec',
  warnSoft: '#faf1dd',
  errSoft: '#fdecec',
}

/* 轴 / 提示 / 网格 */
export const AXIS = {
  splitLine: '#ececf0',
  axisLine: '#e4e4e9',
  axisLabel: '#a4a4af',
  nameGapLabel: '#84848f',
}

export const TOOLTIP = {
  backgroundColor: '#ffffff',
  borderColor: '#e4e4e9',
  borderWidth: 1,
  padding: [8, 12],
  textStyle: { color: '#2c2c38', fontSize: 12 },
  extraCssText: 'box-shadow: 0 4px 16px rgba(22,22,28,.10); border-radius: 8px;',
}

/* 5 分制分数 → 语义色（评分图通用） */
export function scoreColor(v) {
  if (v == null) return SEMANTIC.neutral
  if (v < 3.5) return SEMANTIC.err
  if (v < 4.5) return '#0f8a80'
  return SEMANTIC.ok
}

/**
 * 对 option 注入主题默认值（不覆盖已显式设置的项）。
 * 支持 option 或 option 数组；grid 轴、tooltip、图例、色板。
 */
export function applyChartTheme(option) {
  const list = Array.isArray(option) ? option : [option]
  for (const opt of list) {
    if (!opt || typeof opt !== 'object') continue
    if (!opt.color) opt.color = SERIES
    if (opt.tooltip) {
      opt.tooltip.backgroundColor = opt.tooltip.backgroundColor || TOOLTIP.backgroundColor
      opt.tooltip.borderColor = opt.tooltip.borderColor || TOOLTIP.borderColor
      opt.tooltip.textStyle = opt.tooltip.textStyle || TOOLTIP.textStyle
      opt.tooltip.extraCssText = opt.tooltip.extraCssText || TOOLTIP.extraCssText
    }
    const axes = [...(opt.xAxis || []), ...(opt.yAxis || []), ...(opt.radar && opt.radar.axisLine ? [] : [])]
    const axisList = Array.isArray(axes) ? axes : [axes]
    for (const ax of axisList) {
      if (!ax || typeof ax !== 'object') continue
      if (ax.splitLine && ax.splitLine.lineStyle && !ax.splitLine.lineStyle.color) ax.splitLine.lineStyle.color = AXIS.splitLine
      if (ax.axisLine && ax.axisLine.lineStyle && !ax.axisLine.lineStyle.color) ax.axisLine.lineStyle.color = AXIS.axisLine
      if (ax.axisLabel && !ax.axisLabel.color) ax.axisLabel.color = AXIS.axisLabel
    }
    if (opt.radar) {
      opt.radar.splitLine = opt.radar.splitLine || { lineStyle: { color: AXIS.splitLine } }
      opt.radar.splitArea = opt.radar.splitArea || { show: false }
      opt.radar.axisName = opt.radar.axisName || { color: AXIS.axisLabel, fontSize: 11 }
      opt.radar.axisLine = opt.radar.axisLine || { lineStyle: { color: AXIS.axisLine } }
    }
  }
  return option
}
