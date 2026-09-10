<template>
  <div class="analysis-page">
    <!-- Page header -->
    <div class="phdr">
      <div>
        <h1>综合分析</h1>
      </div>
      <div class="phdr-acts">
        <button class="btn" @click="showHistory = true">
          <svg viewBox="0 0 16 16"><path d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1zm0 12.5a5.5 5.5 0 1 1 0-11 5.5 5.5 0 0 1 0 11zm.5-7H7v4l3.5 2 .5-.83-3-1.77V6.5z" fill="currentColor" stroke="none"/></svg>
          历史记录
        </button>
      </div>
    </div>

    <!-- Mode tabs -->
    <div class="mode-tabs">
      <button class="mode-tab" :class="{ on: mode === 'cross_project' }" @click="mode = 'cross_project'">跨项目对比</button>
      <button class="mode-tab" :class="{ on: mode === 'cross_time' }" @click="mode = 'cross_time'">同项目-跨时段</button>
      <button class="mode-tab" :class="{ on: mode === 'all_projects' }" @click="mode = 'all_projects'">全项目概览</button>
    </div>

    <!-- Cross-project mode -->
    <div class="mode-panel" :class="{ on: mode === 'cross_project' }">
      <div class="filters">
        <span class="f-label">报告 A</span>
        <el-select v-model="form.report_a_id" placeholder="选择报告A" filterable class="f-sel">
          <el-option v-for="r in allReports" :key="'a-' + r.report_id" :label="`${r.project_name} (${r.generated_at?.slice(0,10)}) - ${r.total_score}分`" :value="r.report_id">
            <span>{{ r.project_name }} ({{ r.generated_at?.slice(0,10) }})</span>
            <span class="opt-score">{{ r.total_score }}分</span>
          </el-option>
        </el-select>
        <span class="vs-badge">VS</span>
        <span class="f-label">报告 B</span>
        <el-select v-model="form.report_b_id" placeholder="选择报告B" filterable class="f-sel">
          <el-option v-for="r in allReports" :key="'b-' + r.report_id" :label="`${r.project_name} (${r.generated_at?.slice(0,10)}) - ${r.total_score}分`" :value="r.report_id">
            <span>{{ r.project_name }} ({{ r.generated_at?.slice(0,10) }})</span>
            <span class="opt-score">{{ r.total_score }}分</span>
          </el-option>
        </el-select>
        <div class="f-sep"></div>
        <button class="btn btn-primary" :disabled="!canStart" @click="startAnalysis">
          <svg viewBox="0 0 16 16"><path d="M2 14l4-5 3 3 5-7" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>
          {{ analyzing ? '分析中...' : '开始综合分析' }}
        </button>
      </div>
    </div>

    <!-- Cross-time mode -->
    <div class="mode-panel" :class="{ on: mode === 'cross_time' }">
      <div class="filters">
        <span class="f-label">选择项目</span>
        <el-select v-model="form.project_a_id" placeholder="选择项目" filterable class="f-sel">
          <el-option v-for="p in projectsList" :key="p.project_id" :label="p.project_name" :value="p.project_id">
            <span>{{ p.project_name }}</span>
            <span class="opt-score">{{ p.latest_score }}分 ({{ p.report_count }}份报告)</span>
          </el-option>
        </el-select>
        <template v-if="selectedProjectReports.length > 0">
          <span class="f-label">报告 T1（较早）</span>
          <el-select v-model="form.report_a_id" placeholder="选择报告A" class="f-sel">
            <el-option v-for="r in selectedProjectReports" :key="r.report_id" :label="`${r.generated_at?.slice(0,10)} (${r.total_score}分)`" :value="r.report_id" />
          </el-select>
          <span class="f-label">报告 T2（较晚）</span>
          <el-select v-model="form.report_b_id" placeholder="选择报告B" class="f-sel">
            <el-option v-for="r in selectedProjectReports" :key="r.report_id" :label="`${r.generated_at?.slice(0,10)} (${r.total_score}分)`" :value="r.report_id" />
          </el-select>
        </template>
        <div class="f-sep"></div>
        <button class="btn btn-primary" :disabled="!canStart" @click="startAnalysis">
          <svg viewBox="0 0 16 16"><path d="M2 14l4-5 3 3 5-7" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>
          {{ analyzing ? '分析中...' : '开始综合分析' }}
        </button>
      </div>
    </div>

    <!-- All-projects overview mode -->
    <div class="mode-panel" :class="{ on: mode === 'all_projects' }">
      <div class="filters">
        <span class="f-label">选择项目（可多选）</span>
        <el-select v-model="form.project_ids" multiple filterable collapse-tags collapse-tags-tooltip placeholder="选择要对比的项目" class="f-sel">
          <el-option v-for="p in projectsList" :key="p.project_id" :label="p.project_name" :value="p.project_id">
            <span>{{ p.project_name }}</span>
            <span class="opt-score">{{ p.latest_score }}分 ({{ p.report_count }}份报告)</span>
          </el-option>
        </el-select>
        <div class="f-sep"></div>
        <button class="btn btn-primary" :disabled="!canStart" @click="startAnalysis">
          <svg viewBox="0 0 16 16"><path d="M2 14l4-5 3 3 5-7" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>
          {{ analyzing ? '分析中...' : '开始综合分析' }}
        </button>
      </div>
    </div>

    <!-- Progress card -->
    <div v-if="analyzing" class="card progress-card">
      <div class="card-h">
        <span class="card-t">分析进度</span>
        <span class="card-d">{{ stepLabel }}</span>
      </div>
      <div class="progress-body">
        <div class="prog-bar-lg">
          <div class="prog-fill-lg" :style="{ width: progressData.progress_pct + '%' }"></div>
        </div>
        <span class="prog-pct">{{ progressData.progress_pct }}%</span>
      </div>
    </div>

    <!-- Placeholder when no result -->
    <div v-if="!result && !analyzing" class="card placeholder-card">
      <div class="placeholder-inner">
        <div class="placeholder-title">选择报告后点击"开始综合分析"</div>
        <div class="placeholder-sub">系统将生成品质对比分析报告</div>
      </div>
    </div>

    <!-- Analysis results -->
    <div v-if="result" class="result-area">
      <!-- Executive summary card -->
      <div class="card">
        <div class="card-h">
          <div class="card-h-left">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="var(--blue)" stroke-width="1.8"><path d="M2 14l4-5 3 3 5-7"/><rect x="1" y="1" width="14" height="14" rx="2" stroke="var(--blue)" stroke-width="1.4"/></svg>
            <span class="card-t">执行摘要</span>
          </div>
        </div>
        <div class="card-body">
          <p class="summary-text">{{ result.executive_summary }}</p>

          <!-- Score comparison (modes 1 & 2) -->
          <div v-if="result.mode !== 'all_projects'" class="score-compare">
            <div class="score-block" :class="{ 'score-winner': winnerClass('a') === 'winner' }">
              <span class="score-label">{{ result.label_a }}</span>
              <span class="score-value" :class="{ winner: winnerClass('a') === 'winner' }">{{ result.score_analysis.total_score_a?.toFixed(2) }}</span>
              <span class="score-grade">{{ result.score_analysis.grade_a }}</span>
            </div>
            <span class="vs-center">VS</span>
            <div class="score-block" :class="{ 'score-winner': winnerClass('b') === 'winner' }">
              <span class="score-label">{{ result.label_b }}</span>
              <span class="score-value" :class="{ winner: winnerClass('b') === 'winner' }">{{ result.score_analysis.total_score_b?.toFixed(2) }}</span>
              <span class="score-grade">{{ result.score_analysis.grade_b }}</span>
            </div>
          </div>

          <!-- Statistics summary (mode 3) -->
          <div v-if="result.mode === 'all_projects' && result.score_analysis.ranking" class="ranking-summary">
            <span class="kt kt-blue">共 {{ result.score_analysis.statistics?.count }} 个项目</span>
            <span class="kt kt-muted">均值 {{ result.score_analysis.statistics?.mean }}分</span>
            <span class="kt kt-ok">最高 {{ result.score_analysis.statistics?.max }}分</span>
            <span class="kt kt-err">最低 {{ result.score_analysis.statistics?.min }}分</span>
          </div>
        </div>
      </div>

      <!-- Charts card -->
      <div v-if="result.chart_data" class="card">
        <div class="card-h">
          <span class="card-t">数据图表</span>
        </div>
        <div :class="result.chart_data.radar || result.chart_data.ranking_bar ? 'charts' : ''">
          <div class="chart-box">
            <div ref="chartContainer" class="chart-container"></div>
          </div>
          <div v-if="result.chart_data.radar || result.chart_data.ranking_bar" class="chart-box">
            <div ref="chartContainer2" class="chart-container"></div>
          </div>
        </div>
      </div>

      <!-- Module comparison table (modes 1 & 2) -->
      <div v-if="result.comparison_matrix?.length" class="card">
        <div class="card-h">
          <span class="card-t">模块得分对比</span>
        </div>
        <table class="tbl">
          <thead>
            <tr>
              <th>模块名称</th>
              <th>权重</th>
              <th v-if="result.mode !== 'all_projects'">A 得分</th>
              <th v-if="result.mode !== 'all_projects'">B 得分</th>
              <th v-if="result.mode !== 'all_projects'">差值</th>
              <th v-if="result.mode !== 'all_projects'">判定</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in result.comparison_matrix" :key="row.module_name">
              <td class="cell-name">{{ row.module_name }}</td>
              <td>{{ (row.weight * 100).toFixed(0) }}%</td>
              <td v-if="result.mode !== 'all_projects'" class="cell-mono">{{ row.score_a?.toFixed(2) }}</td>
              <td v-if="result.mode !== 'all_projects'" class="cell-mono">{{ row.score_b?.toFixed(2) }}</td>
              <td v-if="result.mode !== 'all_projects'" class="cell-mono">
                <span :class="diffClass(row.diff)">{{ row.diff > 0 ? '+' : '' }}{{ row.diff?.toFixed(2) }}</span>
              </td>
              <td v-if="result.mode !== 'all_projects'">
                <span class="st" :class="winnerStyleClass(row.winner)">{{ row.winner }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Project ranking table (mode 3) -->
      <div v-if="result.mode === 'all_projects' && result.score_analysis.ranking" class="card">
        <div class="card-h">
          <span class="card-t">项目排行</span>
        </div>
        <table class="tbl">
          <thead>
            <tr>
              <th>排名</th>
              <th>项目名称</th>
              <th>总分</th>
              <th>评级</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in result.score_analysis.ranking" :key="row.project_name">
              <td class="cell-mono">{{ idx + 1 }}</td>
              <td class="cell-name">{{ row.project_name }}</td>
              <td class="cell-mono">{{ row.total_score?.toFixed(2) }}</td>
              <td><span class="st" :class="gradeStyleClass(row.grade)">{{ row.grade }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- AI Insight card -->
      <div v-if="result.ai_result" class="card">
        <div class="card-h">
          <span class="card-t">AI 智能洞察</span>
        </div>
        <div class="card-body">
          <div v-if="result.ai_result.overall_verdict" class="verdict">{{ result.ai_result.overall_verdict }}</div>

          <div v-if="result.ai_result.strengths_a?.length" class="insight-section">
            <h4>{{ result.label_a }} 优势</h4>
            <ul><li v-for="(s, i) in result.ai_result.strengths_a" :key="i">{{ s }}</li></ul>
          </div>
          <div v-if="result.ai_result.strengths_b?.length" class="insight-section">
            <h4>{{ result.label_b }} 优势</h4>
            <ul><li v-for="(s, i) in result.ai_result.strengths_b" :key="i">{{ s }}</li></ul>
          </div>
          <div v-if="result.ai_result.weaknesses_a?.length" class="insight-section">
            <h4>{{ result.label_a }} 薄弱环节</h4>
            <ul><li v-for="(w, i) in result.ai_result.weaknesses_a" :key="i">{{ w }}</li></ul>
          </div>
          <div v-if="result.ai_result.weaknesses_b?.length" class="insight-section">
            <h4>{{ result.label_b }} 薄弱环节</h4>
            <ul><li v-for="(w, i) in result.ai_result.weaknesses_b" :key="i">{{ w }}</li></ul>
          </div>

          <!-- Action items table -->
          <div v-if="result.ai_result.action_items?.length" class="insight-section">
            <h4>行动建议</h4>
            <table class="tbl">
              <thead>
                <tr>
                  <th>具体动作</th>
                  <th>建议负责人</th>
                  <th>建议时限</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in result.ai_result.action_items" :key="item.action">
                  <td class="cell-action">{{ item.action }}</td>
                  <td>{{ item.responsible }}</td>
                  <td>{{ item.deadline }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="result.ai_result.final_conclusion" class="conclusion">
            <strong>结论：</strong>{{ result.ai_result.final_conclusion }}
          </div>
        </div>
      </div>

      <!-- Export buttons -->
      <div v-if="result.export_paths?.word || result.export_paths?.pdf" class="export-row">
        <button v-if="result.export_paths?.word" class="btn" @click="handleDownload('word')">
          <svg viewBox="0 0 16 16"><path d="M3 3h10v10H3z" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M8 6v5M6 8h4" stroke="currentColor" stroke-width="1.4"/></svg>
          下载 Word 报告
        </button>
        <button v-if="result.export_paths?.pdf" class="btn btn-primary" @click="handleDownload('pdf')">
          <svg viewBox="0 0 16 16"><path d="M3 3h10v10H3z" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M8 6v5M6 8h4" stroke="currentColor" stroke-width="1.4"/></svg>
          下载 PDF 报告
        </button>
      </div>
    </div>

    <!-- History drawer -->
    <el-drawer v-model="showHistory" title="历史分析记录" size="50%">
      <el-table :data="historyList" stripe v-loading="historyLoading">
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ row.created_at?.slice(0, 16).replace('T', ' ') }}</template>
        </el-table-column>
        <el-table-column prop="summary" label="描述" />
        <el-table-column label="模式" width="120">
          <template #default="{ row }">{{ modeLabel(row.mode) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : (row.status === 'failed' ? 'danger' : 'warning')" size="small">
              {{ row.status === 'completed' ? '完成' : (row.status === 'failed' ? '失败' : '进行中') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewHistoryItem(row)" :disabled="row.status !== 'completed'">查看</el-button>
            <el-button link type="danger" @click="handleDeleteAnalysis(row)" v-if="authStore.isAdmin">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination v-model:current-page="historyPage" :page-size="20" :total="historyTotal" layout="prev, pager, next" @current-change="loadHistory" />
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { TrendCharts, Clock, Download, DataAnalysis } from '@element-plus/icons-vue'
import * as echarts from 'echarts/core'
import { BarChart, RadarChart, HeatmapChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, LegendComponent,
  GridComponent, VisualMapComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { applyChartTheme } from '../../utils/chartTheme'

echarts.use([
  BarChart, RadarChart, HeatmapChart,
  TitleComponent, TooltipComponent, LegendComponent,
  GridComponent, VisualMapComponent,
  CanvasRenderer
])
import {
  startAnalysis as apiStart,
  getAnalysisProgress,
  getAnalysisResult,
  getAnalysisHistory,
  getProjectsWithReports,
  downloadAnalysisFile,
  deleteAnalysis
} from '../../api/analysis'
import { useAuthStore } from '../../stores/auth'
import { ElMessageBox } from 'element-plus'

const authStore = useAuthStore()

// === 状态 ===
const mode = ref('cross_project')
const form = ref({
  project_a_id: null,
  project_b_id: null,
  time_range_start: null,
  time_range_end: null,
  report_a_id: null,
  report_b_id: null,
  project_ids: []
})
const projectsList = ref([])
const analyzing = ref(false)
const progressData = ref({ progress_pct: 0, current_step: '' })
// 每个模式保留各自的结果和 analysisId
const resultsByMode = ref({
  cross_project: { result: null, analysisId: null },
  cross_time: { result: null, analysisId: null },
  all_projects: { result: null, analysisId: null }
})
const result = computed(() => resultsByMode.value[mode.value]?.result)
const currentAnalysisId = computed(() => resultsByMode.value[mode.value]?.analysisId)
const chartContainer = ref(null)
const chartContainer2 = ref(null)
let chartInstances = []

// 历史记录
const showHistory = ref(false)
const historyList = ref([])
const historyLoading = ref(false)
const historyPage = ref(1)
const historyTotal = ref(0)

// === 计算属性 ===
const allReports = computed(() => {
  const list = []
  for (const p of projectsList.value) {
    for (const r of (p.reports || [])) {
      list.push({ ...r, project_name: p.project_name, project_id: p.project_id })
    }
  }
  return list
})

const selectedProjectReports = computed(() => {
  if (mode.value !== 'cross_time' || !form.value.project_a_id) return []
  const p = projectsList.value.find(p => p.project_id === p.project_id)
  return p?.reports || []
})

const canStart = computed(() => {
  if (mode.value === 'cross_project') {
    return form.value.report_a_id && form.value.report_b_id && form.value.report_a_id !== form.value.report_b_id
  } else if (mode.value === 'cross_time') {
    return form.value.project_a_id && (form.value.report_a_id || selectedProjectReports.value.length >= 2)
  } else {
    return form.value.project_ids?.length >= 2
  }
})

const stepLabel = computed(() => {
  const map = {
    validate_input: '验证参数',
    collect_reports: '收集报告数据',
    analyze_score: '分析综合得分',
    analyze_issue: '分析问题分布',
    analyze_module: '分析8大模块',
    generate_insight: '生成AI洞察',
    render_charts: '生成图表',
    assemble_report: '组装报告',
    export_files: '导出文件',
    save_result: '保存结果',
    completed: '分析完成'
  }
  return map[progressData.value.current_step] || progressData.value.current_step
})

const progressColor = computed(() => {
  const pct = progressData.value.progress_pct
  if (pct < 30) return '#0f8a80'
  if (pct < 70) return '#b07a12'
  return '#27945b'
})

// === 方法 ===
function modeLabel(m) {
  const map = { cross_project: '跨项目对比', cross_time: '跨时段对比', all_projects: '全项目概览' }
  return map[m] || m
}

function winnerClass(side) {
  if (!result.value?.score_analysis) return ''
  const { total_score_a, total_score_b } = result.value.score_analysis
  if (side === 'a' && total_score_a > total_score_b) return 'winner'
  if (side === 'b' && total_score_b > total_score_a) return 'winner'
  return ''
}

function diffClass(diff) {
  if (diff > 0.2) return 'diff-positive'
  if (diff < -0.2) return 'diff-negative'
  return 'diff-neutral'
}

function winnerTagType(winner) {
  if (winner === 'A') return 'primary'
  if (winner === 'B') return 'warning'
  return 'info'
}

function gradeTagType(grade) {
  if (grade?.startsWith('A')) return 'success'
  if (grade?.startsWith('B+') || grade === 'B') return 'warning'
  return 'danger'
}

function winnerStyleClass(winner) {
  if (winner === 'A') return 'st-ai-pass'
  if (winner === 'B') return 'st-review'
  return 'st-pending'
}

function gradeStyleClass(grade) {
  if (grade?.startsWith('A')) return 'st-done'
  if (grade?.startsWith('B+') || grade === 'B') return 'st-progress'
  return 'st-pending'
}

async function loadProjects() {
  try {
    const res = await getProjectsWithReports()
    projectsList.value = res.projects || []
  } catch (e) {
    console.error('加载项目列表失败', e)
    ElMessage.error('加载项目列表失败，请检查后端服务')
  }
}

async function startAnalysis() {
  if (!canStart.value) return
  analyzing.value = true
  resultsByMode.value[mode.value] = { result: null, analysisId: null }
  progressData.value = { progress_pct: 0, current_step: 'validate_input' }

  try {
    const payload = {
      mode: mode.value,
      project_a_id: form.value.project_a_id,
      project_b_id: null,
      time_range_start: form.value.time_range_start,
      time_range_end: form.value.time_range_end,
      report_a_id: mode.value === 'cross_project' ? form.value.report_a_id : (mode.value === 'cross_time' ? form.value.report_a_id : null),
      report_b_id: mode.value === 'cross_project' ? form.value.report_b_id : (mode.value === 'cross_time' ? form.value.report_b_id : null),
      project_ids: mode.value === 'all_projects' ? form.value.project_ids : null
    }

    const res = await apiStart(payload)
    resultsByMode.value[mode.value] = { result: null, analysisId: res.analysis_id }

    // 轮询进度
    await pollProgress(res.analysis_id)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '启动分析失败')
    analyzing.value = false
  }
}

async function pollProgress(analysisId) {
  const poll = async () => {
    try {
      const p = await getAnalysisProgress(analysisId)
      progressData.value = p

      if (p.status === 'completed') {
        analyzing.value = false
        await loadResult(analysisId)
        return
      }
      if (p.status === 'failed') {
        analyzing.value = false
        ElMessage.error(p.error || '分析失败')
        return
      }
      // 继续轮询
      setTimeout(poll, 2000)
    } catch (e) {
      setTimeout(poll, 3000)
    }
  }
  setTimeout(poll, 1500)
}

async function loadResult(analysisId) {
  try {
    const res = await getAnalysisResult(analysisId)
    resultsByMode.value[mode.value] = { result: res, analysisId }
    await nextTick()
    renderCharts()
  } catch (e) {
    ElMessage.error('加载结果失败')
  }
}

function renderCharts() {
  // 清除旧图表
  chartInstances.forEach(c => c?.dispose())
  chartInstances = []

  if (!result.value?.chart_data) return

  const charts = result.value.chart_data

  // 图表1: 柱状图 / 热力图（后端 option，setOption 前注入统一主题）
  if (charts.bar && chartContainer.value) {
    const c1 = echarts.init(chartContainer.value)
    c1.setOption(applyChartTheme(charts.bar))
    chartInstances.push(c1)
  } else if (charts.heatmap && chartContainer.value) {
    const c1 = echarts.init(chartContainer.value)
    c1.setOption(applyChartTheme(charts.heatmap))
    chartInstances.push(c1)
  } else if (charts.ranking_bar && chartContainer.value) {
    const c1 = echarts.init(chartContainer.value)
    c1.setOption(applyChartTheme(charts.ranking_bar))
    chartInstances.push(c1)
  }

  // 图表2: 雷达图
  if (charts.radar && chartContainer2.value) {
    const c2 = echarts.init(chartContainer2.value)
    c2.setOption(applyChartTheme(charts.radar))
    chartInstances.push(c2)
  }

  // 响应窗口变化
  window.addEventListener('resize', () => {
    chartInstances.forEach(c => c?.resize())
  })
}

async function handleDownload(fileType = 'word') {
  const aid = currentAnalysisId.value
  if (!aid) return
  try {
    const blob = await downloadAnalysisFile(aid, fileType)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const ext = fileType === 'pdf' ? 'pdf' : 'docx'
    a.download = `综合分析报告_${aid}.${ext}`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('下载失败')
  }
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const res = await getAnalysisHistory({ page: historyPage.value, size: 20 })
    historyList.value = res.records || []
    historyTotal.value = res.total || 0
  } catch (e) {
    console.error(e)
  } finally {
    historyLoading.value = false
  }
}

async function handleDeleteAnalysis(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除分析记录"${row.summary || row.analysis_id}"吗？删除后不可恢复。`,
      '确认删除',
      { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteAnalysis(row.analysis_id)
    ElMessage.success('删除成功')
    loadHistory()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e?.response?.data?.detail || '删除失败')
    }
  }
}

async function viewHistoryItem(row) {
  showHistory.value = false
  // 切换到对应模式
  if (row.mode && row.mode !== mode.value) {
    mode.value = row.mode
  }
  resultsByMode.value[mode.value] = { result: null, analysisId: row.analysis_id }
  await loadResult(row.analysis_id)
}

// 模式切换时只重置表单，不清除已缓存的结果
watch(mode, async () => {
  form.value = {
    project_a_id: null,
    project_b_id: null,
    time_range_start: null,
    time_range_end: null,
    report_a_id: null,
    report_b_id: null,
    project_ids: []
  }
  // 如果新模式有缓存结果，重新渲染图表
  if (resultsByMode.value[mode.value]?.result) {
    await nextTick()
    renderCharts()
  }
})

watch(showHistory, (v) => {
  if (v) loadHistory()
})

async function loadLatestAnalysis() {
  try {
    const res = await getAnalysisHistory({ page: 1, size: 10 })
    const records = res.records || []
    // 为每种模式加载最新结果
    for (const rec of records) {
      if (rec.status === 'completed' && rec.mode) {
        const cached = resultsByMode.value[rec.mode]
        if (!cached.result) {
          resultsByMode.value[rec.mode] = { result: null, analysisId: rec.analysis_id }
          await loadResult(rec.analysis_id)
        }
      }
    }
  } catch (e) {
    // 静默失败，不影响用户操作
  }
}

onMounted(() => {
  loadProjects()
  loadLatestAnalysis()
})
</script>

<style scoped>
/* === Page layout === */
.analysis-page {
  max-width: 1200px;
  margin: 0 auto;
}

/* === Page header === */

/* === Mode tabs（原型 .seg 分段形态） === */
.mode-tabs {
  display: inline-flex;
  gap: 2px;
  margin-bottom: 18px;
  padding: 2px;
  background: var(--bg-muted);
  border: 1px solid var(--ink-200);
  border-radius: var(--r);
}
.mode-tab {
  padding: 0 14px;
  height: 28px;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--ink-600);
  cursor: pointer;
  border: none;
  background: transparent;
  border-radius: var(--r-sm);
  font-family: var(--sans);
  transition: all 0.12s;
}
.mode-tab:hover { color: var(--ink-900); }
.mode-tab.on {
  background: var(--bg-card);
  color: var(--ink-900);
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(22, 22, 28, 0.08);
}

/* === Mode panels === */
.mode-panel { display: none; }
.mode-panel.on { display: block; }

/* === Filters === */
.filters {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.f-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-600);
}
.f-sel {
  min-width: 180px;
}
.f-sel :deep(.el-input__wrapper) {
  padding: 5px 12px;
  border-radius: var(--r);
  font-size: 13px;
  font-weight: 500;
  color: var(--ink-600);
  border: 1px solid var(--ink-100);
  background: var(--bg-card);
  box-shadow: none;
  transition: all 0.12s;
}
.f-sel :deep(.el-input__wrapper:hover) {
  border-color: var(--ink-200);
}
.f-sel :deep(.el-input__wrapper.is-focus) {
  border-color: var(--blue);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}
.f-sep {
  width: 1px;
  height: 24px;
  background: var(--ink-100);
}
.vs-badge {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink-300);
}
.opt-score {
  float: right;
  color: var(--ink-400);
  font-size: 12px;
}

/* === Buttons (shared) === */

/* === Cards (prototype style) === */
.card {
  background: var(--bg-card);
  border: 1px solid var(--ink-100);
  border-radius: var(--r-lg);
  overflow: hidden;
  margin-bottom: 14px;
  animation: kpiIn 0.3s cubic-bezier(0.25, 0.1, 0.25, 1) 0.05s both;
}
.card-h {
  padding: 14px 20px;
  border-bottom: 1px solid var(--ink-100);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-h-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.card-t {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink-900);
}
.card-d {
  font-size: 12px;
  color: var(--ink-400);
  margin-left: 8px;
}
.card-body {
  padding: 16px 20px;
}

/* === Tables (prototype style) === */
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
.tbl tbody tr {
  cursor: pointer;
  transition: background 0.08s;
}
.tbl tbody tr:hover {
  background: var(--bg);
}
.cell-name {
  text-align: left;
  font-family: var(--sans);
  font-weight: 600;
  color: var(--ink-900);
  padding-left: 20px;
}
.cell-mono {
  font-family: var(--mono);
}
.cell-action {
  text-align: left;
  font-family: var(--sans);
  font-weight: 500;
  color: var(--ink-800);
  padding-left: 20px;
}

/* === Status tags (prototype style) === */
.st {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}
.st-pending { background: var(--bg-muted); color: var(--ink-400); }
.st-progress { background: var(--warn-bg); color: var(--warn); }
.st-done { background: var(--ok-bg); color: var(--ok); }
.st-checking { background: var(--blue-bg); color: var(--blue); }
.st-ai-pass { background: var(--ok-bg); color: var(--ok); }
.st-review { background: var(--warn-bg); color: var(--warn); }

/* === KPI tags === */
.kt {
  font-size: 11px;
  font-family: var(--mono);
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 3px;
}
.kt-ok { background: var(--ok-bg); color: var(--ok); }
.kt-warn { background: var(--warn-bg); color: var(--warn); }
.kt-err { background: var(--err-bg); color: var(--err); }
.kt-teal { background: var(--teal-50); color: var(--teal-700); }
.kt-muted { background: var(--bg-muted); color: var(--ink-600); }
.kt-blue { background: var(--blue-bg); color: var(--blue); }

/* === Placeholder card === */
.placeholder-card .placeholder-inner {
  padding: 32px;
  text-align: center;
  color: var(--ink-400);
}
.placeholder-title {
  font-size: 14px;
  font-weight: 600;
}
.placeholder-sub {
  font-size: 12px;
  margin-top: 4px;
}

/* === Progress card === */
.progress-card .progress-body {
  padding: 12px 20px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.prog-bar-lg {
  flex: 1;
  height: 8px;
  background: var(--ink-100);
  border-radius: 4px;
  overflow: hidden;
}
.prog-fill-lg {
  height: 100%;
  border-radius: 4px;
  background: var(--teal-600);
  transition: width 0.4s cubic-bezier(0.25, 0.1, 0.25, 1);
}
.prog-pct {
  font-family: var(--mono);
  font-size: 14px;
  font-weight: 700;
  color: var(--ink-600);
  min-width: 40px;
  text-align: right;
}

/* === Result area === */
.result-area {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* === Summary card === */
.summary-text {
  font-size: 14px;
  color: var(--ink-800);
  line-height: 1.8;
  margin: 0 0 16px;
}
.score-compare {
  display: flex;
  align-items: center;
  gap: 24px;
  justify-content: center;
  padding: 16px 0;
}
.score-block {
  text-align: center;
  padding: 12px 32px;
  border-radius: var(--r-lg);
  background: var(--bg-muted);
  min-width: 180px;
  transition: all 0.15s;
}
.score-block.score-winner {
  background: var(--blue-bg);
  border: 1px solid var(--blue);
}
.score-block .score-label {
  display: block;
  font-size: 12px;
  color: var(--ink-600);
  margin-bottom: 4px;
}
.score-block .score-value {
  display: block;
  font-size: 32px;
  font-weight: 800;
  color: var(--ink-900);
  font-family: var(--mono);
  letter-spacing: -1px;
}
.score-block .score-value.winner {
  color: var(--blue);
}
.score-block .score-grade {
  display: block;
  font-size: 14px;
  color: var(--ink-600);
  margin-top: 2px;
}
.vs-center {
  font-size: 16px;
  font-weight: 800;
  color: var(--ink-300);
}
.ranking-summary {
  display: flex;
  gap: 24px;
  justify-content: center;
  flex-wrap: wrap;
}

/* === Charts (prototype style) === */
.charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
}
.chart-box {
  padding: 16px 20px;
}
.chart-container {
  width: 100%;
  height: 400px;
}

/* === Diff colors === */
.diff-positive { color: var(--ok); font-weight: 600; }
.diff-negative { color: var(--err); font-weight: 600; }
.diff-neutral { color: var(--ink-400); }

/* === AI Insight card === */
.insight-section {
  margin-bottom: 8px;
}
.insight-section h4 {
  font-size: 14px;
  color: var(--ink-800);
  margin: 16px 0 8px;
}
.insight-section ul {
  margin: 0;
  padding-left: 20px;
}
.insight-section li {
  font-size: 13px;
  color: var(--ink-800);
  line-height: 1.8;
}
.verdict {
  font-size: 14px;
  color: var(--ink-800);
  padding: 12px 16px;
  background: var(--blue-bg);
  border-radius: 8px;
  margin-bottom: 8px;
}
.conclusion {
  font-size: 14px;
  color: var(--ink-800);
  padding: 12px 16px;
  background: var(--ok-bg);
  border-radius: 8px;
  margin-top: 12px;
}

/* === Export row === */
.export-row {
  display: flex;
  gap: 8px;
  padding: 4px 0;
  justify-content: flex-end;
}

/* === Pagination === */
.pagination-wrap {
  padding: 16px 0;
  display: flex;
  justify-content: center;
}

/* === Animation === */
@keyframes kpiIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

/* === Responsive === */
@media (max-width: 1200px) {
  .charts {
    grid-template-columns: 1fr;
  }
}
</style>
