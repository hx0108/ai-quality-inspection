<template>
  <div class="analysis-page">
    <!-- 顶部操作栏 -->
    <div class="top-bar">
      <h2 class="page-title">综合分析</h2>
      <el-button text @click="showHistory = true">
        <el-icon><Clock /></el-icon>
        <span>历史记录</span>
      </el-button>
    </div>

    <!-- 模式选择 + 参数 -->
    <el-card class="config-card" shadow="never">
      <el-tabs v-model="mode" class="mode-tabs">
        <el-tab-pane label="跨项目对比" name="cross_project" />
        <el-tab-pane label="同项目-跨时段" name="cross_time" />
        <el-tab-pane label="全项目概览" name="all_projects" />
      </el-tabs>

      <!-- 跨项目对比 -->
      <div v-if="mode === 'cross_project'" class="param-row">
        <div class="param-block">
          <label>报告 A</label>
          <el-select v-model="form.report_a_id" placeholder="选择报告A" filterable style="width:340px">
            <el-option v-for="r in allReports" :key="'a-' + r.report_id" :label="`${r.project_name} (${r.generated_at?.slice(0,10)}) - ${r.total_score}分`" :value="r.report_id">
              <span>{{ r.project_name }} ({{ r.generated_at?.slice(0,10) }})</span>
              <span class="opt-score">{{ r.total_score }}分</span>
            </el-option>
          </el-select>
        </div>
        <span class="vs-text">VS</span>
        <div class="param-block">
          <label>报告 B</label>
          <el-select v-model="form.report_b_id" placeholder="选择报告B" filterable style="width:340px">
            <el-option v-for="r in allReports" :key="'b-' + r.report_id" :label="`${r.project_name} (${r.generated_at?.slice(0,10)}) - ${r.total_score}分`" :value="r.report_id">
              <span>{{ r.project_name }} ({{ r.generated_at?.slice(0,10) }})</span>
              <span class="opt-score">{{ r.total_score }}分</span>
            </el-option>
          </el-select>
        </div>
      </div>

      <!-- 跨时段对比 -->
      <div v-if="mode === 'cross_time'" class="param-row">
        <div class="param-block">
          <label>选择项目</label>
          <el-select v-model="form.project_a_id" placeholder="选择项目" filterable style="width:260px">
            <el-option v-for="p in projectsList" :key="p.project_id" :label="p.project_name" :value="p.project_id">
              <span>{{ p.project_name }}</span>
              <span class="opt-score">{{ p.latest_score }}分 ({{ p.report_count }}份报告)</span>
            </el-option>
          </el-select>
        </div>
        <div class="param-block" v-if="selectedProjectReports.length > 0">
          <label>报告 T1（较早）</label>
          <el-select v-model="form.report_a_id" placeholder="选择报告A" style="width:320px">
            <el-option v-for="r in selectedProjectReports" :key="r.report_id" :label="`${r.generated_at?.slice(0,10)} (${r.total_score}分)`" :value="r.report_id" />
          </el-select>
        </div>
        <div class="param-block" v-if="selectedProjectReports.length > 0">
          <label>报告 T2（较晚）</label>
          <el-select v-model="form.report_b_id" placeholder="选择报告B" style="width:320px">
            <el-option v-for="r in selectedProjectReports" :key="r.report_id" :label="`${r.generated_at?.slice(0,10)} (${r.total_score}分)`" :value="r.report_id" />
          </el-select>
        </div>
      </div>

      <!-- 全项目概览 -->
      <div v-if="mode === 'all_projects'" class="param-row">
        <div class="param-block">
          <label>开始日期</label>
          <el-date-picker v-model="form.time_range_start" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" style="width:180px" />
        </div>
        <span class="range-sep">~</span>
        <div class="param-block">
          <label>结束日期</label>
          <el-date-picker v-model="form.time_range_end" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" style="width:180px" />
        </div>
      </div>

      <!-- 开始按钮 -->
      <div class="action-row">
        <el-button type="primary" size="large" :loading="analyzing" @click="startAnalysis" :disabled="!canStart">
          <el-icon v-if="!analyzing"><TrendCharts /></el-icon>
          {{ analyzing ? '分析中...' : '开始综合分析' }}
        </el-button>
        <div v-if="analyzing" class="progress-area">
          <el-progress :percentage="progressData.progress_pct" :stroke-width="8" :color="progressColor" style="width:300px" />
          <span class="step-text">{{ stepLabel }}</span>
        </div>
      </div>
    </el-card>

    <!-- 分析结果 -->
    <div v-if="result" class="result-area">
      <!-- 执行摘要 -->
      <el-card class="summary-card" shadow="never">
        <div class="summary-header">
          <el-icon size="20" color="#2563eb"><DataAnalysis /></el-icon>
          <h3>执行摘要</h3>
        </div>
        <p class="summary-text">{{ result.executive_summary }}</p>
        <div v-if="result.mode !== 'all_projects'" class="score-compare">
          <div class="score-block">
            <span class="score-label">{{ result.label_a }}</span>
            <span class="score-value" :class="winnerClass('a')">{{ result.score_analysis.total_score_a?.toFixed(2) }}</span>
            <span class="score-grade">{{ result.score_analysis.grade_a }}</span>
          </div>
          <span class="vs-badge">VS</span>
          <div class="score-block">
            <span class="score-label">{{ result.label_b }}</span>
            <span class="score-value" :class="winnerClass('b')">{{ result.score_analysis.total_score_b?.toFixed(2) }}</span>
            <span class="score-grade">{{ result.score_analysis.grade_b }}</span>
          </div>
        </div>
        <!-- 模式三排行榜 -->
        <div v-if="result.mode === 'all_projects' && result.score_analysis.ranking" class="ranking-summary">
          <span>共 {{ result.score_analysis.statistics?.count }} 个项目</span>
          <span>均值 {{ result.score_analysis.statistics?.mean }}分</span>
          <span>最高 {{ result.score_analysis.statistics?.max }}分</span>
          <span>最低 {{ result.score_analysis.statistics?.min }}分</span>
        </div>
      </el-card>

      <!-- 图表区域 -->
      <el-card v-if="result.chart_data" class="chart-card" shadow="never">
        <div ref="chartContainer" class="chart-container"></div>
        <div ref="chartContainer2" v-if="result.chart_data.radar || result.chart_data.ranking_bar" class="chart-container"></div>
      </el-card>

      <!-- 模块对比表格 -->
      <el-card v-if="result.comparison_matrix?.length" class="table-card" shadow="never">
        <h3>模块得分对比</h3>
        <el-table :data="result.comparison_matrix" stripe style="width:100%">
          <el-table-column prop="module_name" label="模块名称" width="160" />
          <el-table-column label="权重" width="80">
            <template #default="{ row }">{{ (row.weight * 100).toFixed(0) }}%</template>
          </el-table-column>
          <el-table-column v-if="result.mode !== 'all_projects'" label="A得分" width="100">
            <template #default="{ row }">{{ row.score_a?.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column v-if="result.mode !== 'all_projects'" label="B得分" width="100">
            <template #default="{ row }">{{ row.score_b?.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column v-if="result.mode !== 'all_projects'" label="差值" width="100">
            <template #default="{ row }">
              <span :class="diffClass(row.diff)">{{ row.diff > 0 ? '+' : '' }}{{ row.diff?.toFixed(2) }}</span>
            </template>
          </el-table-column>
          <el-table-column v-if="result.mode !== 'all_projects'" label="判定" width="100">
            <template #default="{ row }">
              <el-tag :type="winnerTagType(row.winner)" size="small">{{ row.winner }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 模式三排行榜 -->
      <el-card v-if="result.mode === 'all_projects' && result.score_analysis.ranking" class="table-card" shadow="never">
        <h3>项目排行</h3>
        <el-table :data="result.score_analysis.ranking" stripe style="width:100%">
          <el-table-column label="排名" width="80">
            <template #default="{ $index }">{{ $index + 1 }}</template>
          </el-table-column>
          <el-table-column prop="project_name" label="项目名称" />
          <el-table-column label="总分" width="120">
            <template #default="{ row }">{{ row.total_score?.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="评级" width="100">
            <template #default="{ row }">
              <el-tag :type="gradeTagType(row.grade)" size="small">{{ row.grade }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- AI 洞察与行动建议 -->
      <el-card v-if="result.ai_result" class="insight-card" shadow="never">
        <h3>AI 智能洞察</h3>
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

        <!-- 行动建议 -->
        <div v-if="result.ai_result.action_items?.length" class="insight-section">
          <h4>行动建议</h4>
          <el-table :data="result.ai_result.action_items" stripe size="small">
            <el-table-column label="具体动作" prop="action" />
            <el-table-column label="建议负责人" prop="responsible" width="120" />
            <el-table-column label="建议时限" prop="deadline" width="120" />
          </el-table>
        </div>

        <div v-if="result.ai_result.final_conclusion" class="conclusion">
          <strong>结论：</strong>{{ result.ai_result.final_conclusion }}
        </div>
      </el-card>

      <!-- 导出按钮 -->
      <div v-if="result.export_paths?.word || result.export_paths?.pdf" class="export-row">
        <el-button v-if="result.export_paths?.word" type="primary" @click="handleDownload('word')">
          <el-icon><Download /></el-icon> 下载 Word 报告
        </el-button>
        <el-button v-if="result.export_paths?.pdf" type="success" @click="handleDownload('pdf')">
          <el-icon><Download /></el-icon> 下载 PDF 报告
        </el-button>
      </div>
    </div>

    <!-- 历史记录抽屉 -->
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
  report_b_id: null
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
  const p = projectsList.value.find(p => p.project_id === form.value.project_a_id)
  return p?.reports || []
})

const canStart = computed(() => {
  if (mode.value === 'cross_project') {
    return form.value.report_a_id && form.value.report_b_id && form.value.report_a_id !== form.value.report_b_id
  } else if (mode.value === 'cross_time') {
    return form.value.project_a_id && (form.value.report_a_id || selectedProjectReports.value.length >= 2)
  } else {
    return form.value.time_range_start && form.value.time_range_end
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
  if (pct < 30) return '#409eff'
  if (pct < 70) return '#e6a23c'
  return '#67c23a'
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
      project_b_id: mode.value === 'cross_project' ? null : null,
      time_range_start: form.value.time_range_start,
      time_range_end: form.value.time_range_end,
      report_a_id: mode.value === 'cross_project' ? form.value.report_a_id : (mode.value === 'cross_time' ? form.value.report_a_id : null),
      report_b_id: mode.value === 'cross_project' ? form.value.report_b_id : (mode.value === 'cross_time' ? form.value.report_b_id : null)
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

  // 图表1: 柱状图 / 热力图
  if (charts.bar && chartContainer.value) {
    const c1 = echarts.init(chartContainer.value)
    c1.setOption(charts.bar)
    chartInstances.push(c1)
  } else if (charts.heatmap && chartContainer.value) {
    const c1 = echarts.init(chartContainer.value)
    c1.setOption(charts.heatmap)
    chartInstances.push(c1)
  } else if (charts.ranking_bar && chartContainer.value) {
    const c1 = echarts.init(chartContainer.value)
    c1.setOption(charts.ranking_bar)
    chartInstances.push(c1)
  }

  // 图表2: 雷达图
  if (charts.radar && chartContainer2.value) {
    const c2 = echarts.init(chartContainer2.value)
    c2.setOption(charts.radar)
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
    report_b_id: null
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
.analysis-page {
  max-width: 1200px;
  margin: 0 auto;
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: #1a1d26;
  margin: 0;
}

.config-card {
  margin-bottom: 20px;
}

.mode-tabs :deep(.el-tabs__item) {
  font-size: 15px;
  font-weight: 500;
}

.param-row {
  display: flex;
  align-items: flex-end;
  gap: 20px;
  padding: 16px 0;
  flex-wrap: wrap;
}

.param-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.param-block label {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.vs-text {
  font-size: 18px;
  font-weight: 800;
  color: #9ca3af;
  align-self: center;
  padding-bottom: 8px;
}

.range-sep {
  font-size: 18px;
  color: #9ca3af;
  align-self: center;
  padding-bottom: 8px;
}

.opt-score {
  float: right;
  color: #9ca3af;
  font-size: 12px;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 24px;
  padding-top: 8px;
}

.progress-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.step-text {
  font-size: 13px;
  color: #6b7280;
  white-space: nowrap;
}

/* === 结果区域 === */
.result-area {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.summary-card, .chart-card, .table-card, .insight-card {
  margin-bottom: 0;
}

.summary-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.summary-header h3 {
  margin: 0;
  font-size: 16px;
  color: #1a1d26;
}

.summary-text {
  font-size: 14px;
  color: #4b5563;
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
  border-radius: 12px;
  background: #f9fafb;
  min-width: 180px;
}

.score-block .score-label {
  display: block;
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 4px;
}

.score-block .score-value {
  display: block;
  font-size: 32px;
  font-weight: 800;
  color: #1a1d26;
}

.score-block .score-value.winner {
  color: #2563eb;
}

.score-block .score-grade {
  display: block;
  font-size: 14px;
  color: #6b7280;
  margin-top: 2px;
}

.vs-badge {
  font-size: 16px;
  font-weight: 800;
  color: #d1d5db;
}

.ranking-summary {
  display: flex;
  gap: 24px;
  justify-content: center;
  font-size: 13px;
  color: #6b7280;
}

.chart-container {
  width: 100%;
  height: 400px;
}

h3 {
  font-size: 15px;
  color: #1a1d26;
  margin: 0 0 12px;
}

.diff-positive { color: #22c55e; font-weight: 600; }
.diff-negative { color: #ef4444; font-weight: 600; }
.diff-neutral { color: #9ca3af; }

.insight-card h4 {
  font-size: 14px;
  color: #374151;
  margin: 16px 0 8px;
}

.insight-card ul {
  margin: 0;
  padding-left: 20px;
}

.insight-card li {
  font-size: 13px;
  color: #4b5563;
  line-height: 1.8;
}

.verdict {
  font-size: 14px;
  color: #374151;
  padding: 12px 16px;
  background: #f0f9ff;
  border-radius: 8px;
  margin-bottom: 8px;
}

.conclusion {
  font-size: 14px;
  color: #374151;
  padding: 12px 16px;
  background: #f0fdf4;
  border-radius: 8px;
  margin-top: 12px;
}

.export-row {
  display: flex;
  gap: 12px;
  padding: 8px 0;
}

.pagination-wrap {
  padding: 16px 0;
  display: flex;
  justify-content: center;
}

.insight-section {
  margin-bottom: 4px;
}
</style>
