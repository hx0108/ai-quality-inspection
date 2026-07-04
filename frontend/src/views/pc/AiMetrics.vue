<template>
  <div class="ai-metrics-page">
    <el-skeleton v-if="loading" :rows="8" animated class="loading-wrap" />

    <template v-else>
      <!-- 页面头部 -->
      <div class="phdr">
        <div>
          <h1>AI效果评估看板</h1>
          <div class="phdr-sub">AI评分准确性、可靠性、公平性实时监控</div>
        </div>
      </div>

      <!-- 筛选栏 -->
      <div class="filters">
        <div class="radio-group">
          <button
            v-for="d in [7, 30, 90]"
            :key="d"
            class="radio-btn"
            :class="{ on: daysRange === d }"
            @click="daysRange = d; onDaysChange()"
          >近{{ d }}天</button>
        </div>
      </div>

      <!-- 6个KPI卡片 -->
      <div class="kpi-row cols-6">
        <div class="kpi">
          <div class="kpi-lbl">评分一致性率（%）</div>
          <div class="kpi-num">{{ overview.consistency_rate ?? 100 }}<span class="kpi-unit">%</span></div>
          <div class="kpi-tags">
            <span class="kt" :class="overview.consistency_trend >= 0 ? 'kt-ok' : 'kt-err'">
              {{ overview.consistency_trend >= 0 ? '↑' : '↓' }}{{ Math.abs(overview.consistency_trend || 0) }}%
            </span>
          </div>
        </div>

        <div class="kpi">
          <div class="kpi-lbl">降级率（%）</div>
          <div class="kpi-num">{{ overview.fallback_rate ?? 0 }}<span class="kpi-unit">%</span></div>
          <div class="kpi-tags">
            <span class="kt" :class="overview.fallback_trend <= 0 ? 'kt-ok' : 'kt-err'">
              {{ overview.fallback_trend <= 0 ? '↓' : '↑' }}{{ Math.abs(overview.fallback_trend || 0) }}%
            </span>
          </div>
        </div>

        <div class="kpi">
          <div class="kpi-lbl">超时率（%）</div>
          <div class="kpi-num">{{ overview.timeout_rate ?? 0 }}<span class="kpi-unit">%</span></div>
          <div class="kpi-tags">
            <span class="kt" :class="overview.timeout_trend <= 0 ? 'kt-ok' : 'kt-err'">
              {{ overview.timeout_trend <= 0 ? '↓' : '↑' }}{{ Math.abs(overview.timeout_trend || 0) }}%
            </span>
          </div>
        </div>

        <div class="kpi">
          <div class="kpi-lbl">人工复核积压（件）</div>
          <div class="kpi-num">{{ overview.human_review_backlog ?? 0 }}</div>
          <div class="kpi-tags">
            <span class="kt" :class="(overview.human_review_trend || 0) <= 0 ? 'kt-ok' : 'kt-err'">
              {{ (overview.human_review_trend || 0) <= 0 ? '↓' : '↑' }}{{ Math.abs(overview.human_review_trend || 0) }}
            </span>
          </div>
        </div>

        <div class="kpi">
          <div class="kpi-lbl">边缘案例数</div>
          <div class="kpi-num">{{ overview.edge_case_count ?? 0 }}</div>
          <div class="kpi-tags" v-if="overview.edge_case_trend > 0">
            <span class="kt kt-ok">↑{{ overview.edge_case_trend }}</span>
          </div>
        </div>

        <div class="kpi">
          <div class="kpi-lbl">效率提升（倍）</div>
          <div class="kpi-num">{{ overview.efficiency_multiplier ?? 0 }}<span class="kpi-unit">x</span></div>
        </div>
      </div>

      <!-- 智能诊断与改进建议 -->
      <div class="card diagnosis-card">
        <div class="card-h">
          <span class="card-t">🩺 智能诊断与改进建议</span>
          <span class="card-d" v-if="diagnosisPeriod">周期 {{ diagnosisPeriod }} · {{ diagnosisItems.length }} 条</span>
          <button class="dx-run-btn" :disabled="diagnosisRunning" @click="runDiagnosis">
            {{ diagnosisRunning ? '诊断中...' : '刷新诊断' }}
          </button>
        </div>
        <div v-if="diagnosisItems.length === 0 && !diagnosisRunning" class="dx-empty">
          暂无异常诊断 — 当前各模块指标正常
        </div>
        <div v-else>
          <div v-for="d in diagnosisItems" :key="d.diagnosis_id" class="dx-item" :class="'dx-' + d.severity">
            <div class="dx-head">
              <span class="dx-sev" :class="'sev-' + d.severity">{{ d.severity }}</span>
              <span class="dx-module">{{ d.module_name }}</span>
              <span class="dx-pattern">{{ d.pattern }}</span>
            </div>
            <div class="dx-problem">{{ d.problem }}</div>
            <div class="dx-rootcause"><b>根因：</b>{{ d.llm_root_cause || d.root_cause }}</div>
            <div v-if="d.suggestion && d.suggestion.suggestion" class="dx-suggestion">
              <span class="dx-action" :class="'act-' + (d.suggestion.action_type || 'add_rule')">{{ actionLabel(d.suggestion.action_type) }}</span>
              <b>建议：</b>{{ d.suggestion.suggestion }}
              <div v-if="d.suggestion.expected_impact" class="dx-impact">预期：{{ d.suggestion.expected_impact }}</div>
            </div>
            <div v-if="d.evidence && d.evidence.hotspots && d.evidence.hotspots.length" class="dx-evidence">
              <span class="dx-evi-label">修改热点：</span>
              <span v-for="h in d.evidence.hotspots.slice(0,3)" :key="h.item_id" class="dx-chip">
                {{ h.item_name || h.item_id }} ({{ h.edit_count }}次)
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 各模块一致性率 + 置信度分布 -->
      <div class="charts">
        <div class="card">
          <div class="card-h"><span class="card-t">各模块一致性率</span></div>
          <div ref="moduleBarRef" class="chart-box" style="height:280px"></div>
        </div>
        <div class="card">
          <div class="card-h"><span class="card-t">置信度分布</span></div>
          <div ref="confidencePieRef" class="chart-box" style="height:280px"></div>
        </div>
      </div>

      <!-- 一致性率趋势图（全宽） -->
      <div class="card">
        <div class="card-h"><span class="card-t">一致性率趋势</span></div>
        <div ref="trendChartRef" class="chart-box" style="height:320px"></div>
      </div>

      <!-- 偏差检测 + 置信度校准 -->
      <div class="charts">
        <div class="card">
          <div class="card-h"><span class="card-t">偏差检测</span></div>
          <div ref="radarChartRef" class="chart-box" style="height:280px"></div>
        </div>
        <div class="card">
          <div class="card-h"><span class="card-t">置信度校准</span></div>
          <div ref="calibrationBarRef" class="chart-box" style="height:280px"></div>
        </div>
      </div>

      <!-- 模块评分明细表 -->
      <div class="card">
        <div class="card-h"><span class="card-t">模块评分明细</span></div>
        <table class="tbl">
          <thead>
            <tr>
              <th>模块</th>
              <th>评分数</th>
              <th>一致性率</th>
              <th>平均分</th>
              <th>平均置信度</th>
              <th>修改率</th>
              <th>降级率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in moduleStats" :key="row.module_name">
              <td style="text-align:left;font-family:var(--sans);font-weight:600;color:var(--ink-900)">{{ row.module_name }}</td>
              <td style="font-family:var(--mono)">{{ row.total_scored }}</td>
              <td>
                <span class="sp" :class="row.consistency_rate >= 95 ? 'sp-hi' : row.consistency_rate >= 85 ? 'sp-mid' : 'sp-lo'">
                  {{ row.consistency_rate }}%
                </span>
              </td>
              <td style="font-family:var(--mono)">{{ row.avg_score }}</td>
              <td style="font-family:var(--mono)">{{ row.avg_confidence }}</td>
              <td style="font-family:var(--mono)">{{ row.edit_rate }}%</td>
              <td style="font-family:var(--mono)">{{ row.fallback_rate }}%</td>
            </tr>
            <tr v-if="moduleStats.length === 0">
              <td colspan="7" style="color:var(--ink-400);padding:32px 0">暂无数据</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 边缘案例追踪表 -->
      <div class="card">
        <div class="card-h"><span class="card-t">边缘案例追踪</span></div>
        <table class="tbl">
          <thead>
            <tr>
              <th>ID</th>
              <th>问题描述</th>
              <th>模块</th>
              <th>出现数</th>
              <th>命中数</th>
              <th>命中率</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in edgeCases" :key="row.case_id">
              <td>{{ row.case_id }}</td>
              <td style="text-align:left;font-family:var(--sans)">{{ row.title }}</td>
              <td style="text-align:left;font-family:var(--sans)">{{ row.module_name }}</td>
              <td style="font-family:var(--mono)">{{ row.occurrence_count }}</td>
              <td style="font-family:var(--mono)">{{ row.hit_count }}</td>
              <td>
                <span class="sp" :class="row.hit_rate >= 80 ? 'sp-hi' : 'sp-mid'">
                  {{ row.hit_rate }}%
                </span>
              </td>
              <td>
                <span class="st" :class="row.review_status === 'approved' ? 'st-done' : row.review_status === 'rejected' ? 'st-progress' : 'st-review'">
                  {{ row.review_status === 'approved' ? '已审核' : row.review_status === 'rejected' ? '已驳回' : '待审核' }}
                </span>
              </td>
            </tr>
            <tr v-if="edgeCases.length === 0">
              <td colspan="7" style="color:var(--ink-400);padding:32px 0">暂无边缘案例数据</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleCheck, Warning, Timer, User, Search, TrendCharts } from '@element-plus/icons-vue'
import echarts from '../../utils/echarts'
import {
  getAiMetricsOverview,
  getAiMetricsTrend,
  getModuleStats,
  getConfidenceCalibration,
  getBiasAndEdges,
  getDiagnosis,
  runDiagnosis as apiRunDiagnosis,
} from '../../api/ai_metrics'

const loading = ref(true)
const daysRange = ref(30)
const overview = ref({})
const trendData = ref([])
const moduleStats = ref([])
const calibrationData = ref({})
const biasData = ref({})
const diagnosisItems = ref([])
const diagnosisPeriod = ref('')
const diagnosisRunning = ref(false)
const edgeCases = ref([])

let trendChart = null
let confidencePieChart = null
let moduleBarChart = null
let radarChart = null
let calibrationBarChart = null

const trendChartRef = ref(null)
const confidencePieRef = ref(null)
const moduleBarRef = ref(null)
const radarChartRef = ref(null)
const calibrationBarRef = ref(null)

async function fetchOverview() {
  const res = await getAiMetricsOverview()
  overview.value = res.data || res
}

async function fetchTrend() {
  const res = await getAiMetricsTrend(daysRange.value)
  const data = res.data || res
  trendData.value = data.trend || []
}

async function fetchModuleStats() {
  const res = await getModuleStats()
  const data = res.data || res
  moduleStats.value = data.modules || []
}

async function fetchCalibration() {
  const res = await getConfidenceCalibration()
  calibrationData.value = res.data || res
}

async function fetchBiasAndEdges() {
  const res = await getBiasAndEdges()
  const data = res.data || res
  biasData.value = data.bias || {}
  edgeCases.value = data.edge_cases || []
}

async function fetchDiagnosis() {
  const res = await getDiagnosis()
  const data = res.data || res
  diagnosisItems.value = data.items || []
  diagnosisPeriod.value = data.period || ''
}

async function runDiagnosis() {
  diagnosisRunning.value = true
  try {
    const res = await apiRunDiagnosis(daysRange.value)
    const data = res.data || res
    diagnosisItems.value = data.items || []
    diagnosisPeriod.value = `近${daysRange.value}天`
    ElMessage.success(`诊断完成，发现 ${data.total || 0} 条异常`)
  } catch (e) {
    ElMessage.error('诊断失败')
  } finally {
    diagnosisRunning.value = false
  }
}

function actionLabel(type) {
  const map = { add_rule: '补规则', adjust_threshold: '调阈值', refine_prompt: '改Prompt', add_edge_case: '补案例' }
  return map[type] || '改进'
}

// ==================== 图表渲染 ====================

function renderTrendChart() {
  if (!trendChartRef.value || trendData.value.length === 0) return
  trendChart = echarts.init(trendChartRef.value)
  const dates = trendData.value.map(d => d.date)
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['一致性率', '降级率', '平均置信度'], top: 0 },
    grid: { top: 40, bottom: 30, left: 50, right: 50 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 11 } },
    yAxis: [
      { type: 'value', name: '%', min: 0, max: 100, axisLabel: { fontSize: 11 } },
      { type: 'value', name: '置信度', min: 0, max: 1, axisLabel: { fontSize: 11 } },
    ],
    series: [
      {
        name: '一致性率', type: 'line', smooth: true,
        data: trendData.value.map(d => d.consistency_rate),
        itemStyle: { color: '#2563eb' },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(37,99,235,0.15)' }, { offset: 1, color: 'rgba(37,99,235,0.01)' }] } },
      },
      {
        name: '降级率', type: 'line', smooth: true,
        data: trendData.value.map(d => d.fallback_rate),
        itemStyle: { color: '#ca8a04' },
        lineStyle: { type: 'dashed' },
      },
      {
        name: '平均置信度', type: 'line', smooth: true, yAxisIndex: 1,
        data: trendData.value.map(d => d.avg_confidence),
        itemStyle: { color: '#16a34a' },
      },
    ],
  })
}

function renderConfidencePie() {
  if (!confidencePieRef.value) return
  confidencePieChart = echarts.init(confidencePieRef.value)
  const dist = calibrationData.value.distribution || {}
  const data = [
    { value: dist.high || 0, name: '高置信度(≥0.8)', itemStyle: { color: '#2563eb' } },
    { value: dist.medium || 0, name: '中置信度(0.5-0.8)', itemStyle: { color: '#ca8a04' } },
    { value: dist.low || 0, name: '低置信度(<0.5)', itemStyle: { color: '#dc2626' } },
  ]
  const total = data.reduce((s, d) => s + d.value, 0)
  confidencePieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, textStyle: { fontSize: 12 } },
    series: [{
      type: 'pie', radius: ['45%', '72%'], center: ['50%', '45%'],
      label: { show: true, formatter: total > 0 ? '{d}%' : '', fontSize: 12 },
      data,
    }],
  })
}

function renderModuleBar() {
  if (!moduleBarRef.value || moduleStats.value.length === 0) return
  moduleBarChart = echarts.init(moduleBarRef.value)
  const sorted = [...moduleStats.value].sort((a, b) => a.consistency_rate - b.consistency_rate)
  // 每个模块固定分配独立颜色（8色循环），保证各模块颜色都不同，便于区分
  const palette = ['#2563eb', '#16a34a', '#ca8a04', '#dc2626', '#7c3aed', '#0891b2', '#db2777', '#ea580c']
  moduleBarChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { top: 10, bottom: 30, left: 100, right: 40 },
    xAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%', fontSize: 11 } },
    yAxis: { type: 'category', data: sorted.map(m => m.module_name), axisLabel: { fontSize: 12 } },
    series: [{
      type: 'bar', barWidth: 18,
      data: sorted.map((m, idx) => ({
        value: m.consistency_rate,
        itemStyle: {
          color: palette[idx % palette.length],
          borderRadius: [0, 4, 4, 0],
        },
      })),
      label: { show: true, position: 'right', formatter: '{c}%', fontSize: 11, color: '#475569' },
    }],
  })
}

function renderRadarChart() {
  if (!radarChartRef.value) return
  if (radarChart) radarChart.dispose()
  radarChart = echarts.init(radarChartRef.value)
  const moduleDevs = biasData.value.module_deviations || []

  if (moduleDevs.length === 0) {
    radarChart.setOption({
      title: { text: '暂无偏差数据', left: 'center', top: 'center', textStyle: { color: '#a1a1aa', fontSize: 14 } },
    })
    return
  }

  // 偏差用柱状图展示（雷达图在小偏差数据下几乎不可见），按偏差降序
  const sorted = [...moduleDevs].sort((a, b) => b.deviation - a.deviation)
  const palette = ['#dc2626', '#ea580c', '#ca8a04', '#84cc16', '#16a34a', '#0891b2', '#2563eb', '#7c3aed']
  radarChart.setOption({
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: (p) => {
        const m = sorted[p[0].dataIndex]
        return `${m.module_name}<br/>偏差: ${m.deviation}<br/>编辑率: ${m.edit_rate}%`
      },
    },
    grid: { top: 10, bottom: 30, left: 100, right: 40 },
    xAxis: { type: 'value', axisLabel: { fontSize: 11 } },
    yAxis: { type: 'category', data: sorted.map(m => m.module_name), axisLabel: { fontSize: 12 } },
    series: [{
      type: 'bar', barWidth: 18,
      data: sorted.map((m, idx) => ({
        value: m.deviation,
        itemStyle: { color: palette[idx % palette.length], borderRadius: [0, 4, 4, 0] },
      })),
      label: { show: true, position: 'right', formatter: '{c}', fontSize: 11, color: '#475569' },
    }],
  })
}

function renderCalibrationBar() {
  if (!calibrationBarRef.value) return
  calibrationBarChart = echarts.init(calibrationBarRef.value)
  const cal = calibrationData.value.calibration || []
  if (cal.length === 0) return

  calibrationBarChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { top: 20, bottom: 40, left: 50, right: 30 },
    xAxis: {
      type: 'category',
      data: cal.map(c => c.bucket),
      axisLabel: { fontSize: 11, interval: 0 },
    },
    yAxis: { type: 'value', name: '实际一致率%', max: 100, axisLabel: { fontSize: 11 } },
    series: [
      {
        name: '样本数', type: 'bar', yAxisIndex: 0, barWidth: 30,
        data: cal.map(c => ({
          value: c.count,
          itemStyle: { color: 'rgba(148,163,184,0.3)', borderRadius: [4, 4, 0, 0] },
        })),
        label: { show: true, position: 'top', formatter: '{c}条', fontSize: 10, color: '#a1a1aa' },
        z: 1,
      },
      {
        name: '实际一致率', type: 'line', smooth: true,
        data: cal.map(c => c.actual_consistency_rate),
        itemStyle: { color: '#2563eb' },
        lineStyle: { width: 3 },
        symbol: 'circle', symbolSize: 10,
        label: { show: true, position: 'top', formatter: '{c}%', fontSize: 12, color: '#18181b', fontWeight: 600 },
        z: 2,
      },
    ],
  })
}

function handleResize() {
  trendChart?.resize()
  confidencePieChart?.resize()
  moduleBarChart?.resize()
  radarChart?.resize()
  calibrationBarChart?.resize()
}

function renderAllCharts() {
  nextTick(() => {
    renderTrendChart()
    renderConfidencePie()
    renderModuleBar()
    renderRadarChart()
    renderCalibrationBar()
  })
}

async function onDaysChange() {
  await fetchTrend()
  nextTick(() => renderTrendChart())
}

// ==================== 生命周期 ====================

onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([
      fetchOverview(),
      fetchTrend(),
      fetchModuleStats(),
      fetchCalibration(),
      fetchBiasAndEdges(),
      fetchDiagnosis(),
    ])
  } catch (e) {
    console.error('AI效果评估数据加载失败:', e)
  } finally {
    loading.value = false
    renderAllCharts()
    window.addEventListener('resize', handleResize)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  confidencePieChart?.dispose()
  moduleBarChart?.dispose()
  radarChart?.dispose()
  calibrationBarChart?.dispose()
})
</script>

<style scoped>
/* ===== Page wrapper ===== */
.ai-metrics-page {
  max-width: 1400px;
}

.loading-wrap {
  padding: 40px 0;
}

/* ===== Page header — prototype .phdr ===== */
.phdr {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 20px;
}
.phdr h1 {
  font-size: 22px;
  font-weight: 800;
  color: var(--ink-900);
  letter-spacing: -0.4px;
  margin: 0;
}
.phdr-sub {
  font-size: 13px;
  color: var(--ink-400);
  margin-top: 3px;
}

/* ===== Filter bar — prototype .filters ===== */
.filters {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

/* ===== Radio group — prototype ===== */
.radio-group {
  display: flex;
  gap: 2px;
  background: var(--bg-muted);
  border-radius: var(--r);
  padding: 3px;
}
.radio-btn {
  padding: 5px 12px;
  border-radius: var(--r-sm);
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-400);
  cursor: pointer;
  border: none;
  background: none;
  font-family: var(--sans);
  transition: all 0.12s;
}
.radio-btn:hover {
  color: var(--ink-600);
}
.radio-btn.on {
  background: var(--bg-card);
  color: var(--blue);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

/* ===== KPI row — prototype ===== */
.kpi-row {
  display: grid;
  gap: 12px;
  margin-bottom: 20px;
}
.kpi-row.cols-6 {
  grid-template-columns: repeat(6, 1fr);
}
.kpi {
  background: var(--bg-card);
  border: 1px solid var(--ink-100);
  border-radius: var(--r-lg);
  padding: 18px 20px;
  cursor: default;
  transition: all 0.15s var(--ease);
  animation: kpiIn 0.3s var(--ease) both;
}
.kpi:nth-child(2) { animation-delay: 30ms; }
.kpi:nth-child(3) { animation-delay: 60ms; }
.kpi:nth-child(4) { animation-delay: 90ms; }
.kpi:nth-child(5) { animation-delay: 120ms; }
.kpi:nth-child(6) { animation-delay: 150ms; }
.kpi:hover {
  border-color: var(--ink-200);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
.kpi-lbl {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-400);
  margin-bottom: 6px;
}
.kpi-num {
  font-family: var(--mono);
  font-size: 32px;
  font-weight: 700;
  color: var(--ink-900);
  line-height: 1;
  margin-bottom: 6px;
  letter-spacing: -1.5px;
}
.kpi-unit {
  font-size: 16px;
  font-weight: 500;
  color: var(--ink-400);
  letter-spacing: 0;
}
.kpi-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

/* ===== KPI tags — prototype .kt ===== */
.kt {
  font-size: 11px;
  font-family: var(--mono);
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 3px;
}
.kt-ok {
  background: var(--ok-bg);
  color: var(--ok);
}
.kt-warn {
  background: var(--warn-bg);
  color: var(--warn);
}
.kt-err {
  background: var(--err-bg);
  color: var(--err);
}

/* ===== Card — prototype ===== */
.card {
  background: var(--bg-card);
  border: 1px solid var(--ink-100);
  border-radius: var(--r-lg);
  overflow: hidden;
  margin-bottom: 14px;
  animation: kpiIn 0.3s var(--ease) 0.05s both;
}
.card-h {
  padding: 14px 20px;
  border-bottom: 1px solid var(--ink-100);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-t {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink-900);
}

/* ===== Charts grid — prototype .charts ===== */
.charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.charts .card {
  animation-delay: 0.12s;
}

/* ===== Chart box — prototype ===== */
.chart-box {
  width: 100%;
  padding: 16px 20px;
}

/* ===== Table — prototype .tbl ===== */
.tbl {
  width: 100%;
  border-collapse: collapse;
}
.tbl th {
  font-size: 12px;
  font-weight: 700;
  color: var(--ink-400);
  letter-spacing: 0.3px;
  text-align: center;
  padding: 10px 10px;
  background: var(--bg-muted);
  border-bottom: 1px solid var(--ink-100);
}
.tbl th:first-child {
  text-align: left;
  padding-left: 20px;
}
.tbl td {
  font-size: 14px;
  font-weight: 500;
  text-align: center;
  padding: 12px 10px;
  border-bottom: 1px solid var(--ink-100);
  color: var(--ink-600);
}
.tbl td:first-child {
  text-align: left;
  padding-left: 20px;
  font-family: var(--mono);
  font-size: 12px;
  color: var(--ink-400);
}
.tbl tbody tr {
  cursor: pointer;
  transition: background 0.08s;
}
.tbl tbody tr:hover {
  background: var(--bg);
}

/* ===== Score pills — prototype .sp ===== */
.sp {
  display: inline-block;
  min-width: 32px;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: var(--mono);
  font-size: 13px;
  font-weight: 700;
  text-align: center;
}
.sp-hi {
  background: var(--ok-bg);
  color: var(--ok);
}
.sp-mid {
  background: var(--warn-bg);
  color: var(--warn);
}
.sp-lo {
  background: var(--err-bg);
  color: var(--err);
}

/* ===== Status badges — prototype .st ===== */
.st {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}
.st-pending {
  background: var(--bg-muted);
  color: var(--ink-400);
}
.st-progress {
  background: var(--warn-bg);
  color: var(--warn);
}
.st-done {
  background: var(--ok-bg);
  color: var(--ok);
}
.st-review {
  background: var(--warn-bg);
  color: var(--warn);
}

/* ===== Animations — prototype ===== */
@keyframes kpiIn {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ===== Responsive ===== */
@media (max-width: 1200px) {
  .kpi-row.cols-6 {
    grid-template-columns: repeat(3, 1fr);
  }
  .charts {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .kpi-row.cols-6 {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* ===== 智能诊断区 ===== */
.diagnosis-card { margin-bottom: 20px; }
.dx-run-btn {
  margin-left: auto;
  background: var(--blue, #2563eb); color: #fff; border: none;
  padding: 6px 14px; border-radius: 6px; font-size: 12px; cursor: pointer;
}
.dx-run-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.dx-empty { padding: 28px 0; text-align: center; color: var(--ink-400, #a1a1aa); font-size: 13px; }
.dx-item {
  border-left: 3px solid var(--ink-200, #e2e8f0);
  padding: 12px 14px; margin-top: 12px; background: var(--bg-muted, #f8fafc);
  border-radius: 0 8px 8px 0;
}
.dx-item.dx-高 { border-left-color: #dc2626; background: #fef2f2; }
.dx-item.dx-中 { border-left-color: #ca8a04; background: #fffbeb; }
.dx-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.dx-sev {
  font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px;
}
.dx-sev.sev-高 { background: #fee2e2; color: #dc2626; }
.dx-sev.sev-中 { background: #fef3c7; color: #ca8a04; }
.dx-sev.sev-低 { background: #f1f5f9; color: #64748b; }
.dx-module { font-size: 14px; font-weight: 700; color: var(--ink-900, #18181b); }
.dx-pattern {
  font-size: 11px; color: #64748b; background: #fff; padding: 2px 8px;
  border-radius: 10px; border: 1px solid var(--ink-100, #f1f5f9);
}
.dx-problem { font-size: 13px; color: var(--ink-900, #18181b); margin-bottom: 4px; }
.dx-rootcause { font-size: 12px; color: #475569; line-height: 1.5; margin-bottom: 6px; }
.dx-suggestion {
  font-size: 12px; color: #18181b; line-height: 1.5; margin-bottom: 6px;
  background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 6px 10px;
}
.dx-action {
  font-size: 10px; font-weight: 700; padding: 1px 7px; border-radius: 4px;
  margin-right: 6px; background: #2563eb; color: #fff;
}
.dx-action.act-adjust_threshold { background: #0891b2; }
.dx-action.act-refine_prompt { background: #7c3aed; }
.dx-action.act-add_edge_case { background: #16a34a; }
.dx-impact { font-size: 11px; color: #16a34a; margin-top: 4px; }
.dx-evidence { font-size: 11px; color: #64748b; display: flex; align-items: center; flex-wrap: wrap; gap: 4px; }
.dx-evi-label { color: #94a3b8; }
.dx-chip {
  background: #fff; border: 1px solid var(--ink-100, #e2e8f0);
  padding: 1px 7px; border-radius: 4px; color: #475569;
}
</style>
