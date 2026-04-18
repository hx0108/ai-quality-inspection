<template>
  <div class="dashboard-page">
    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="5" animated />
    </div>

    <template v-else>
      <!-- 页面标题 -->
      <div class="page-header">
        <div class="page-header-left">
          <h2 class="page-title">数据概览</h2>
          <p class="page-desc">物业品质检查核心指标一览</p>
        </div>
        <el-button type="primary" plain @click="exportAllData" :loading="exportingAll">
          <el-icon style="margin-right:6px"><Download /></el-icon>导出全部报表
        </el-button>
      </div>

      <!-- 核心指标卡片 -->
      <StatsCards :summary="summary" @open-task="openTaskDrawer()" @open-coverage="openCoverageDrawer()" @open-issue="openIssueDrawer()" @open-rect="openRectDrawer()" />

      <!-- 各项目模块得分对比（全宽） -->
      <div class="dash-card">
        <div class="dash-card-header">
          <div class="dash-card-header-left">
            <span class="dash-card-title">各项目模块得分对比</span>
            <span class="dash-card-sub">最新一次检查 · 点击行查看详情</span>
          </div>
          <div class="dash-card-actions">
            <el-button size="small" text @click="exportScoreTable('excel')">
              <el-icon style="margin-right:4px"><Document /></el-icon>导出Excel
            </el-button>
            <el-button size="small" text @click="exportScoreTable('csv')">
              <el-icon style="margin-right:4px"><DocumentCopy /></el-icon>导出CSV
            </el-button>
          </div>
        </div>
        <div class="module-table-wrap">
          <el-table :data="projectScores" stripe size="small" class="module-score-table" :header-cell-style="{ background: '#F8FAFC', color: '#334155', fontWeight: 600, fontSize: '12px' }" @row-click="openProjectDrawer">
            <el-table-column prop="project_name" label="项目名称" fixed="left" width="130" show-overflow-tooltip />
            <el-table-column v-for="m in moduleNames" :key="m.key" :label="m.label" width="95" align="center">
              <template #default="{ row }">
                <span v-if="row.modules && row.modules[m.key] != null" class="cell-score" :class="getScoreCellClass(row.modules[m.key])">{{ row.modules[m.key] }}</span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="latest_score" label="总分" fixed="right" width="80" align="center" sortable>
              <template #default="{ row }">
                <span class="cell-score cell-total" :class="getScoreCellClass(row.latest_score)">{{ row.latest_score }}</span>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!projectScores.length" description="暂无数据" :image-size="60" />
        </div>
      </div>

      <!-- 底部双栏：问题分布 + 整改统计 -->
      <div class="charts-grid">
        <div class="dash-card">
          <div class="dash-card-header">
            <div class="dash-card-header-left">
              <span class="dash-card-title">问题按模块分布</span>
              <span class="dash-card-sub">点击查看详情</span>
            </div>
            <div class="dash-card-actions">
              <el-button size="small" text @click="exportChart('module', 'png')">
                <el-icon style="margin-right:4px"><Picture /></el-icon>导出图片
              </el-button>
              <el-button size="small" text @click="exportChart('module', 'excel')">
                <el-icon style="margin-right:4px"><Document /></el-icon>导出Excel
              </el-button>
            </div>
          </div>
          <div ref="moduleChartRef" class="chart-area"></div>
        </div>
        <div class="dash-card">
          <div class="dash-card-header">
            <div class="dash-card-header-left">
              <span class="dash-card-title">各项目整改完成率</span>
              <span class="dash-card-sub">已整改 vs 未整改</span>
            </div>
            <div class="dash-card-actions">
              <el-button size="small" text @click="exportChart('rect', 'png')">
                <el-icon style="margin-right:4px"><Picture /></el-icon>导出图片
              </el-button>
              <el-button size="small" text @click="exportChart('rect', 'excel')">
                <el-icon style="margin-right:4px"><Document /></el-icon>导出Excel
              </el-button>
            </div>
          </div>
          <div ref="rectChartRef" class="chart-area"></div>
        </div>
      </div>
    </template>

    <!-- ==================== 抽屉组件 ==================== -->
    <TaskDrawer v-model:visible="taskDrawer.visible" :all-projects="allProjects" @go-to-task="goToTask" @export="exportDrawerData('task')" ref="taskDrawerRef" />
    <CoverageDrawer v-model:visible="coverageDrawer.visible" :checked-projects="coverageDrawer.checkedProjects" :unchecked-projects="coverageDrawer.uncheckedProjects" :checked-count="coverageDrawer.checkedCount" :total-projects="summary.total_projects || 0" :coverage-rate="summary.coverage_rate || 0" @go-to-project="goToProjectTasks" @export="exportDrawerData('coverage')" />
    <IssueDrawer v-model:visible="issueDrawer.visible" @export="exportDrawerData('issue')" ref="issueDrawerRef" />
    <RectDrawer v-model:visible="rectDrawer.visible" @export="exportDrawerData('rect')" ref="rectDrawerRef" />

    <!-- ==================== 弹窗：模块问题列表（柱状图点击） ==================== -->
    <el-dialog v-model="moduleDialog.visible" :title="moduleDialog.title" width="700px" :destroy-on-close="true">
      <el-table :data="moduleDialog.list" stripe size="small" v-loading="moduleDialog.loading" row-key="rectification_id">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="issue-expand">
              <div class="expand-row"><span class="expand-label">完整描述：</span>{{ row.description }}</div>
              <div class="expand-row" v-if="row.location"><span class="expand-label">问题位置：</span>{{ row.location }}</div>
              <div class="expand-row" v-if="row.issue_photos && row.issue_photos.length">
                <span class="expand-label">问题照片：</span>
                <div class="expand-photos">
                  <el-image v-for="photo in row.issue_photos" :key="photo.photo_id || photo" :src="getPhotoUrl(photo)" :preview-src-list="row.issue_photos.map(p => getPhotoUrl(p))" fit="cover" style="width: 72px; height: 72px; border-radius: 4px; margin-right: 6px" />
                </div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="project_name" label="项目" width="120" />
        <el-table-column prop="item_name" label="检查项" width="130" />
        <el-table-column prop="description" label="问题描述" show-overflow-tooltip />
        <el-table-column prop="severity" label="严重程度" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.severity === '严重' ? 'danger' : row.severity === '轻微' ? 'info' : 'warning'" size="small">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="整改状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="getRectStatusType(row.status)" size="small">{{ getRectStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- ==================== 抽屉：项目得分详情 ==================== -->
    <ProjectDrawer v-model:visible="projectDrawer.visible" :title="projectDrawer.title" :modules="projectDrawer.modules" :loading="projectDrawer.loading" ref="projectDrawerRef" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { getDashboardStats } from '../../api/stats'
import { getTasks, getProjects } from '../../api/tasks'
import { getAllRectifications } from '../../api/rectification'
import { getScoringSummary } from '../../api/scoring'
import echarts from '../../utils/echarts'
import * as XLSX from 'xlsx'
import { saveAs } from 'file-saver'
import StatsCards from './dashboard/StatsCards.vue'
import TaskDrawer from './dashboard/TaskDrawer.vue'
import CoverageDrawer from './dashboard/CoverageDrawer.vue'
import IssueDrawer from './dashboard/IssueDrawer.vue'
import RectDrawer from './dashboard/RectDrawer.vue'
import ProjectDrawer from './dashboard/ProjectDrawer.vue'

const router = useRouter()

// ==================== 主页数据 ====================
const loading = ref(true)
const summary = ref({})
const projectScores = ref([])
const issueByModule = ref([])
const allProjects = ref([])
const exportingAll = ref(false)
const coverageDetail = ref({ checked_projects: [], unchecked_projects: [] })

// 8大模块名称（与后端 config.py MODULE_WEIGHTS 对应）
const moduleNames = [
  { key: '客户服务', label: '客户服务' },
  { key: '安全管理', label: '安全管理' },
  { key: 'EHS及风险管理', label: 'EHS' },
  { key: '环境管理', label: '环境管理' },
  { key: '机电运维', label: '机电运维' },
  { key: '设施维护', label: '设施维护' },
  { key: '综合管理', label: '综合管理' },
  { key: '财务管理', label: '财务管理' },
]

const moduleChartRef = ref(null)
let moduleChart = null

const rectChartRef = ref(null)
let rectChart = null
const projectRectStats = ref([])

// ==================== 抽屉/弹窗状态 ====================
const taskDrawer = ref({ visible: false, list: [], total: 0, page: 1, pageSize: 20, statusFilter: '', projectFilter: '', loading: false })
const coverageDrawer = ref({ visible: false, checkedProjects: [], uncheckedProjects: [], checkedCount: 0 })
const issueDrawer = ref({ visible: false, list: [], loading: false, severityFilter: '', moduleFilter: '', projectFilter: '', modules: [], projects: [] })
const rectDrawer = ref({ visible: false, list: [], loading: false, statusFilter: '', keyword: '' })
const moduleDialog = ref({ visible: false, title: '', list: [], loading: false })
const projectDrawer = ref({ visible: false, title: '', modules: [], loading: false, projectId: null })
const miniChartRef = ref(null)
let miniChart = null

// ==================== 导出工具函数 ====================
function buildSheet(headers, rows) {
  return [headers, ...rows]
}

function saveExcel(sheetData, fileName, sheetName = 'Sheet1') {
  const ws = XLSX.utils.aoa_to_sheet(sheetData)
  // 设置列宽
  ws['!cols'] = sheetData[0].map((h, i) => {
    const maxLen = Math.max(h.length, ...sheetData.slice(1).map(r => String(r[i] || '').length))
    return { wch: Math.min(maxLen + 4, 30) }
  })
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, sheetName)
  const buf = XLSX.write(wb, { bookType: 'xlsx', type: 'array' })
  saveAs(new Blob([buf], { type: 'application/octet-stream' }), fileName)
}

function saveCSV(sheetData, fileName) {
  const csv = sheetData.map(r => r.map(c => `"${String(c ?? '').replace(/"/g, '""')}"`).join(',')).join('\n')
  const bom = '\uFEFF'
  saveAs(new Blob([bom + csv], { type: 'text/csv;charset=utf-8' }), fileName)
}

function downloadChartImage(chartInstance, fileName) {
  if (!chartInstance) return
  const url = chartInstance.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' })
  const a = document.createElement('a')
  a.href = url
  a.download = fileName
  a.click()
}

// ==================== 导出：模块得分对比表 ====================
const exportScoreTable = (format) => {
  const headers = ['项目名称', ...moduleNames.map(m => m.label), '总分']
  const rows = projectScores.value.map(p => {
    return [
      p.project_name,
      ...moduleNames.map(m => p.modules?.[m.key] ?? '-'),
      p.latest_score ?? '-'
    ]
  })
  const data = buildSheet(headers, rows)
  const ts = new Date().toISOString().slice(0, 10)
  if (format === 'csv') {
    saveCSV(data, `项目模块得分对比_${ts}.csv`)
  } else {
    saveExcel(data, `项目模块得分对比_${ts}.xlsx`, '模块得分对比')
  }
}

// ==================== 导出：图表 ====================
const exportChart = (chartType, format) => {
  const ts = new Date().toISOString().slice(0, 10)
  if (format === 'png') {
    const chartInst = chartType === 'module' ? moduleChart : rectChart
    const name = chartType === 'module' ? `问题按模块分布_${ts}.png` : `各项目整改完成率_${ts}.png`
    downloadChartImage(chartInst, name)
  } else {
    let headers, rows, fileName, sheetName
    if (chartType === 'module') {
      headers = ['模块名称', '问题数量']
      rows = issueByModule.value.map(i => [i.module_name, i.count])
      fileName = `问题按模块分布_${ts}.xlsx`
      sheetName = '问题分布'
    } else {
      headers = ['项目名称', '已整改', '未整改', '合计', '完成率(%)']
      rows = projectRectStats.value.map(i => [i.project_name, i.approved, i.pending, i.total, i.rate])
      fileName = `各项目整改完成率_${ts}.xlsx`
      sheetName = '整改完成率'
    }
    saveExcel(buildSheet(headers, rows), fileName, sheetName)
  }
}

// ==================== 导出：抽屉数据 ====================
const exportDrawerData = (type) => {
  const ts = new Date().toISOString().slice(0, 10)
  let headers, rows, fileName, sheetName

  if (type === 'task') {
    headers = ['任务编号', '项目名称', '检查日期', '状态', '总分']
    rows = taskDrawer.value.list.map(r => [
      r.task_id?.substring(0, 8), r.project_name, r.check_date, getStatusText(r.status), r.total_score ?? '-'
    ])
    fileName = `检查任务列表_${ts}.xlsx`
    sheetName = '任务列表'
  } else if (type === 'coverage') {
    const checkedHeaders = ['项目名称', '最近检查日期', '状态']
    const checkedRows = coverageDrawer.value.checkedProjects.map(p => [p.project_name, p.latest_report_date || p.check_date, '已检查'])
    const uncheckedRows = coverageDrawer.value.uncheckedProjects.map(p => [p.name, '-', '未检查'])
    headers = checkedHeaders
    rows = [...checkedRows, ...uncheckedRows]
    fileName = `本月检查覆盖率_${ts}.xlsx`
    sheetName = '覆盖率'
  } else if (type === 'issue') {
    headers = ['项目', '模块', '检查项', '问题描述', '严重程度', '整改状态']
    rows = issueDrawer.value.list.map(r => [
      r.project_name, r.module_name, r.item_name, r.description, r.severity, getRectStatusText(r.status)
    ])
    fileName = `问题列表_${ts}.xlsx`
    sheetName = '问题列表'
  } else if (type === 'rect') {
    headers = ['项目', '模块', '检查项', '问题描述', '严重程度', '整改状态', '整改说明']
    rows = rectDrawer.value.list.map(r => [
      r.project_name, r.module_name, r.item_name, r.description, r.severity, getRectStatusText(r.status), r.rectification_note || ''
    ])
    fileName = `整改记录_${ts}.xlsx`
    sheetName = '整改记录'
  }

  if (headers && rows) {
    saveExcel(buildSheet(headers, rows), fileName, sheetName)
  }
}

// ==================== 导出全部报表 ====================
const exportAllData = async () => {
  exportingAll.value = true
  try {
    const ts = new Date().toISOString().slice(0, 10)
    const wb = XLSX.utils.book_new()

    // Sheet 1: 概览指标
    const summaryHeaders = ['指标', '数值']
    const summaryRows = [
      ['总项目数', summary.value.total_projects],
      ['检查任务数', summary.value.total_tasks],
      ['待处理任务', summary.value.pending_tasks],
      ['进行中任务', summary.value.in_progress_tasks],
      ['已完成任务', summary.value.completed_tasks],
      ['总问题数', summary.value.total_issues],
      ['严重问题', summary.value.serious_issues],
      ['一般问题', summary.value.general_issues],
      ['轻微问题', summary.value.minor_issues],
      ['总整改数', summary.value.total_rectifications],
      ['待整改', summary.value.pending_rectifications],
      ['已提交待审', summary.value.submitted_rectifications],
      ['已通过', summary.value.approved_rectifications],
      ['已驳回', summary.value.rejected_rectifications],
      ['整改完成率(%)', summary.value.rectification_rate],
      ['本月覆盖率(%)', summary.value.coverage_rate],
      ['本月已检查项目', summary.value.monthly_checked_projects],
    ]
    const ws1 = XLSX.utils.aoa_to_sheet(buildSheet(summaryHeaders, summaryRows))
    ws1['!cols'] = [{ wch: 20 }, { wch: 15 }]
    XLSX.utils.book_append_sheet(wb, ws1, '概览指标')

    // Sheet 2: 项目模块得分对比
    if (projectScores.value.length) {
      const scoreHeaders = ['项目名称', ...moduleNames.map(m => m.label), '总分']
      const scoreRows = projectScores.value.map(p => [
        p.project_name, ...moduleNames.map(m => p.modules?.[m.key] ?? '-'), p.latest_score ?? '-'
      ])
      const ws2 = XLSX.utils.aoa_to_sheet(buildSheet(scoreHeaders, scoreRows))
      ws2['!cols'] = scoreHeaders.map(() => ({ wch: 14 }))
      XLSX.utils.book_append_sheet(wb, ws2, '模块得分对比')
    }

    // Sheet 3: 问题按模块分布
    if (issueByModule.value.length) {
      const ws3 = XLSX.utils.aoa_to_sheet(buildSheet(
        ['模块名称', '问题数量'],
        issueByModule.value.map(i => [i.module_name, i.count])
      ))
      ws3['!cols'] = [{ wch: 18 }, { wch: 12 }]
      XLSX.utils.book_append_sheet(wb, ws3, '问题分布')
    }

    // Sheet 4: 整改统计
    if (projectRectStats.value.length) {
      const ws4 = XLSX.utils.aoa_to_sheet(buildSheet(
        ['项目名称', '已整改', '未整改', '合计', '完成率(%)'],
        projectRectStats.value.map(i => [i.project_name, i.approved, i.pending, i.total, i.rate])
      ))
      ws4['!cols'] = [{ wch: 18 }, { wch: 10 }, { wch: 10 }, { wch: 10 }, { wch: 12 }]
      XLSX.utils.book_append_sheet(wb, ws4, '整改统计')
    }

    const buf = XLSX.write(wb, { bookType: 'xlsx', type: 'array' })
    saveAs(new Blob([buf], { type: 'application/octet-stream' }), `品质检查报表_${ts}.xlsx`)

    // 同时导出图表图片
    if (moduleChart) downloadChartImage(moduleChart, `问题按模块分布_${ts}.png`)
    if (rectChart) downloadChartImage(rectChart, `各项目整改完成率_${ts}.png`)
  } catch (e) {
    console.error('导出失败:', e)
  } finally {
    exportingAll.value = false
  }
}

// ==================== 主页数据加载 ====================
const fetchStats = async () => {
  loading.value = true
  try {
    const res = await getDashboardStats()
    summary.value = res.summary || {}
    projectScores.value = res.project_latest_scores || []
    issueByModule.value = res.issue_by_module || []
    projectRectStats.value = res.project_rectification_stats || []
    coverageDetail.value = res.coverage_detail || { checked_projects: [], unchecked_projects: [] }

    // 预加载项目列表（供筛选器使用）
    try {
      const projRes = await getProjects()
      allProjects.value = projRes.items || []
    } catch (e) { /* ignore */ }
  } catch (e) {
    console.error('获取仪表盘数据失败:', e)
  } finally {
    loading.value = false
  }
  await nextTick()
  renderModuleChart()
  renderRectChart()
}

const renderModuleChart = () => {
  if (!moduleChartRef.value || !issueByModule.value.length) return
  if (!moduleChart) {
    moduleChart = echarts.init(moduleChartRef.value)
    moduleChart.on('click', (params) => {
      if (params.componentType === 'series') {
        const moduleName = issueByModule.value[issueByModule.value.length - 1 - params.dataIndex]?.module_name
        if (moduleName) openModuleDialog(moduleName)
      }
    })
  }
  const colors = ['#6366F1', '#8B5CF6', '#EC4899', '#F43F5E', '#F97316', '#EAB308', '#22C55E', '#06B6D4']
  const reversed = [...issueByModule.value].reverse()
  moduleChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(255, 255, 255, 0.96)',
      borderColor: '#E2E8F0',
      borderWidth: 1,
      textStyle: { color: '#334155', fontSize: 13 },
      extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-radius: 8px;'
    },
    grid: { left: 110, right: 20, top: 10, bottom: 20 },
    xAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#F1F5F9', type: 'dashed' } },
      axisLabel: { color: '#94A3B8' }
    },
    yAxis: {
      type: 'category',
      data: reversed.map(i => i.module_name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { fontSize: 12, color: '#64748B', width: 90, overflow: 'truncate' }
    },
    series: [{
      type: 'bar',
      data: reversed.map((i, idx) => ({
        value: i.count,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: colors[idx % colors.length] },
            { offset: 1, color: colors[idx % colors.length] + 'B3' }
          ]),
          borderRadius: [0, 6, 6, 0]
        }
      })),
      barWidth: 20,
      emphasis: {
        itemStyle: { shadowBlur: 6, shadowColor: 'rgba(0,0,0,0.1)' }
      }
    }]
  })
}

const renderRectChart = () => {
  if (!rectChartRef.value || !projectRectStats.value.length) return
  if (!rectChart) {
    rectChart = echarts.init(rectChartRef.value)
  }
  const data = [...projectRectStats.value].reverse()
  rectChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(255, 255, 255, 0.96)',
      borderColor: '#E2E8F0',
      borderWidth: 1,
      textStyle: { color: '#334155', fontSize: 13 },
      extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-radius: 8px;',
      formatter: (params) => {
        const name = params[0].name
        const approved = params.find(p => p.seriesName === '已整改')?.value || 0
        const pending = params.find(p => p.seriesName === '未整改')?.value || 0
        const total = approved + pending
        const rate = total > 0 ? ((approved / total) * 100).toFixed(1) : 0
        return `<div style="font-weight:600;margin-bottom:4px">${name}</div>` +
          `<div>已整改：<span style="color:#059669;font-weight:600">${approved}</span></div>` +
          `<div>未整改：<span style="color:#dc2626;font-weight:600">${pending}</span></div>` +
          `<div style="margin-top:4px;border-top:1px solid #eee;padding-top:4px">完成率：<b>${rate}%</b></div>`
      }
    },
    legend: {
      data: ['已整改', '未整改'],
      top: 0,
      right: 10,
      textStyle: { fontSize: 12, color: '#64748B' },
      itemWidth: 12,
      itemHeight: 12,
      itemGap: 16
    },
    grid: { left: 110, right: 50, top: 35, bottom: 15 },
    xAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#F1F5F9', type: 'dashed' } },
      axisLabel: { color: '#94A3B8' }
    },
    yAxis: {
      type: 'category',
      data: data.map(i => i.project_name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { fontSize: 12, color: '#64748B', width: 90, overflow: 'truncate' }
    },
    series: [
      {
        name: '已整改',
        type: 'bar',
        stack: 'total',
        data: data.map(i => i.approved),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#059669' },
            { offset: 1, color: '#34D399' }
          ]),
          borderRadius: [0, 0, 0, 0]
        },
        barWidth: 18,
        emphasis: { itemStyle: { shadowBlur: 6, shadowColor: 'rgba(5,150,105,0.2)' } }
      },
      {
        name: '未整改',
        type: 'bar',
        stack: 'total',
        data: data.map(i => i.pending),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#F87171' },
            { offset: 1, color: '#FCA5A5' }
          ]),
          borderRadius: [0, 6, 6, 0]
        },
        barWidth: 18,
        emphasis: { itemStyle: { shadowBlur: 6, shadowColor: 'rgba(220,38,38,0.2)' } }
      }
    ]
  })
}

// ==================== 工具函数 ====================
const getScoreCellClass = (score) => {
  if (score >= 90) return 'cell-good'
  if (score >= 70) return 'cell-ok'
  return 'cell-bad'
}

const getStatusText = (status) => {
  const map = { pending: '待开始', in_progress: '进行中', completed: '已完成' }
  return map[status] || status
}

const getRectStatusType = (status) => {
  const map = { pending: 'info', submitted: 'warning', approved: 'success', rejected: 'danger' }
  return map[status] || 'info'
}

const getRectStatusText = (status) => {
  const map = { pending: '待整改', submitted: '已提交', approved: '已通过', rejected: '已驳回' }
  return map[status] || status
}

const getPhotoUrl = (photo) => {
  if (typeof photo === 'string') return `/api/v1/records/photos/${photo}`
  if (photo.file_path) return `/api/v1/records/photos/${photo.photo_id}`
  if (photo.photo_id) return `/api/v1/records/photos/${photo.photo_id}`
  return ''
}

// ==================== 导航 ====================
const goToTask = (taskId) => {
  router.push(`/pc/tasks?task_id=${taskId}`)
}

const goToProjectTasks = (projectId) => {
  if (projectId) router.push(`/pc/tasks?project_id=${projectId}`)
}

// ==================== 抽屉1：检查任务 ====================
const openTaskDrawer = async (statusFilter = '') => {
  taskDrawer.value = { visible: true, list: [], total: 0, page: 1, pageSize: 20, statusFilter, projectFilter: '', loading: false }
  await loadTaskList()
}

// ==================== 抽屉2：覆盖率 ====================
const openCoverageDrawer = async () => {
  const detail = coverageDetail.value
  coverageDrawer.value = {
    visible: true,
    checkedProjects: detail.checked_projects || [],
    uncheckedProjects: detail.unchecked_projects || [],
    checkedCount: (detail.checked_projects || []).length,
  }
}

// ==================== 抽屉3：问题列表 ====================
const openIssueDrawer = async (severityFilter = '') => {
  issueDrawer.value = { visible: true, list: [], loading: false, severityFilter, moduleFilter: '', projectFilter: '', modules: [], projects: [] }
  try {
    const res = await getAllRectifications()
    const items = res.items || []
    issueDrawer.value.modules = [...new Set(items.map(i => i.module_name).filter(Boolean))].sort()
    issueDrawer.value.projects = [...new Set(items.map(i => i.project_name).filter(Boolean))].sort()
    issueDrawer.value.list = items
  } catch (e) {
    console.error('加载问题列表失败:', e)
  }
}

// ==================== 抽屉4：整改记录 ====================
const openRectDrawer = async (statusFilter = '') => {
  rectDrawer.value = { visible: true, list: [], loading: false, statusFilter, keyword: '' }
}

// ==================== 弹窗6：模块问题 ====================
const openModuleDialog = async (moduleName) => {
  moduleDialog.value = { visible: true, title: `${moduleName} — 问题列表`, list: [], loading: true }
  try {
    const res = await getAllRectifications({ module_name: moduleName })
    moduleDialog.value.list = res.items || []
  } catch (e) {
    console.error('加载模块问题失败:', e)
  } finally {
    moduleDialog.value.loading = false
  }
}

// ==================== 抽屉7：项目得分详情 ====================
const openProjectDrawer = async (row) => {
  projectDrawer.value = { visible: true, title: `${row.project_name} — 得分趋势与模块详情`, modules: [], loading: true, projectId: null }
  try {
    const taskRes = await getTasks({ page: 1, page_size: 50 })
    const projectTasks = (taskRes.items || []).filter(t => t.project_name === row.project_name && t.total_score != null)

    const latestTask = projectTasks[0]
    const latestTaskId = latestTask?.task_id
    projectDrawer.value.projectId = latestTask?.project_id

    await nextTick()
    renderMiniChart(projectTasks)

    if (latestTaskId) {
      try {
        const summaryRes = await getScoringSummary(latestTaskId)
        const modules = (summaryRes.modules || []).map(m => ({
          ...m,
          task_id: latestTaskId,
          items: [],
          _loading: false,
          _expanded: false
        }))
        projectDrawer.value.modules = modules
      } catch (e) {
        console.error('加载模块得分失败:', e)
      }
    }
  } catch (e) {
    console.error('加载项目详情失败:', e)
  } finally {
    projectDrawer.value.loading = false
  }
}

const renderMiniChart = (tasks) => {
  if (!miniChartRef.value) return
  if (!miniChart) {
    miniChart = echarts.init(miniChartRef.value)
  }
  const sorted = [...tasks].sort((a, b) => (a.check_date || '').localeCompare(b.check_date || ''))
  miniChart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.96)',
      borderColor: '#E2E8F0',
      borderWidth: 1,
      textStyle: { color: '#334155', fontSize: 12 }
    },
    grid: { left: 45, right: 15, top: 10, bottom: 25 },
    xAxis: {
      type: 'category',
      data: sorted.map(t => t.check_date || ''),
      axisLine: { lineStyle: { color: '#E2E8F0' } },
      axisTick: { show: false },
      axisLabel: { fontSize: 10, rotate: 30, color: '#94A3B8' }
    },
    yAxis: {
      type: 'value',
      min: 0, max: 100,
      splitLine: { lineStyle: { color: '#F1F5F9', type: 'dashed' } },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { fontSize: 10, color: '#94A3B8' }
    },
    series: [{
      type: 'line',
      data: sorted.map(t => t.total_score),
      smooth: 0.4,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: {
        width: 2,
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#059669' },
          { offset: 1, color: '#34D399' }
        ])
      },
      itemStyle: { color: '#059669', borderWidth: 2, borderColor: '#fff' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(5, 150, 105, 0.15)' },
          { offset: 1, color: 'rgba(5, 150, 105, 0.01)' }
        ])
      }
    }]
  })
}

const handleResize = () => {
  moduleChart?.resize()
  rectChart?.resize()
  miniChart?.resize()
}

onMounted(() => {
  fetchStats()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  moduleChart?.dispose()
  rectChart?.dispose()
  miniChart?.dispose()
})
</script>

<style scoped>
/* ==================== 页面基础 ==================== */
.dashboard-page {
  max-width: 1400px;
  padding: 0 0 40px;
}

.loading-wrap {
  padding: 40px;
}

/* ==================== 页面标题 ==================== */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header-left {
  display: flex;
  flex-direction: column;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #1a1d26;
  margin: 0;
  line-height: 1.3;
}

.page-desc {
  font-size: 13px;
  color: #9ba3af;
  margin: 4px 0 0;
}

/* ==================== 统计卡片 ==================== */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}

.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
  position: relative;
  overflow: hidden;
  animation: fadeInUp 0.4s ease-out both;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--accent-grad, var(--accent));
  border-radius: 12px 12px 0 0;
}

.stat-card:nth-child(1) { animation-delay: 0s; }
.stat-card:nth-child(2) { animation-delay: 0.05s; }
.stat-card:nth-child(3) { animation-delay: 0.1s; }
.stat-card:nth-child(4) { animation-delay: 0.15s; }
.stat-card:nth-child(5) { animation-delay: 0.2s; }

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
}

.stat-icon-box {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: var(--accent-light);
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: transform 0.25s;
}

.stat-card:hover .stat-icon-box {
  transform: scale(1.08);
}

.stat-body {
  flex: 1;
  min-width: 0;
}

.stat-label {
  display: block;
  font-size: 13px;
  color: #9ba3af;
  margin-bottom: 4px;
}

.stat-value {
  display: block;
  font-size: 28px;
  font-weight: 700;
  color: #1a1d26;
  line-height: 1.2;
}

.stat-unit {
  font-size: 14px;
  font-weight: 400;
  color: #9ba3af;
}

.stat-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.stat-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: #F1F5F9;
  color: #64748B;
}

.tag-blue { background: #EFF6FF; color: #2563eb; }
.tag-red { background: #FEF2F2; color: #dc2626; }
.tag-orange { background: #FFF7ED; color: #ea580c; }
.tag-green { background: #ECFDF5; color: #059669; }
.tag-gray { background: #F8FAFC; color: #64748B; }

.stat-arrow {
  color: #CBD5E1;
  flex-shrink: 0;
  transition: transform 0.2s, color 0.2s;
  font-size: 16px;
}

.stat-card:hover .stat-arrow {
  transform: translateX(3px);
  color: var(--accent);
}

/* ==================== 仪表盘卡片 ==================== */
.dash-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
  overflow: hidden;
}

.dash-card-header {
  padding: 16px 20px;
  border-bottom: 1px solid #F1F5F9;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dash-card-header-left {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.dash-card-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1d26;
}

.dash-card-sub {
  font-size: 12px;
  color: #9ba3af;
}

.dash-card-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* ==================== 图表 ==================== */
.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 16px;
}

.chart-area {
  height: 300px;
  padding: 8px;
}

/* ==================== 模块得分对比表 ==================== */
.module-table-wrap {
  padding: 0;
}

.module-score-table {
  width: 100%;
  cursor: pointer;
}

.cell-score {
  display: inline-block;
  min-width: 32px;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 600;
  text-align: center;
}

.cell-total {
  font-size: 14px;
  font-weight: 700;
}

.cell-good {
  background: #ECFDF5;
  color: #059669;
}

.cell-ok {
  background: #FFFBEB;
  color: #D97706;
}

.cell-bad {
  background: #FEF2F2;
  color: #DC2626;
}

/* ==================== 得分颜色 ==================== */
.score-good { color: #059669; font-weight: 600; }
.score-ok { color: #f59e0b; font-weight: 600; }
.score-bad { color: #dc2626; font-weight: 600; }
.text-muted { color: #9ba3af; }

/* ==================== 抽屉通用样式 ==================== */
.drawer-filter {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.drawer-top-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.drawer-table {
  width: 100%;
}

.drawer-pagination {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

/* 覆盖率 */
.coverage-summary {
  flex: 1;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 10px;
  padding: 14px 18px;
  font-size: 14px;
  color: #1a1d26;
}

.coverage-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.coverage-col-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 2px solid #e5e7eb;
}

.coverage-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  border-radius: 8px;
  margin-bottom: 4px;
  transition: background 0.15s;
}

.coverage-item.clickable {
  cursor: pointer;
}

.coverage-item.clickable:hover {
  background: #f0fdf4;
}

.coverage-name {
  font-size: 13px;
  font-weight: 500;
  color: #1a1d26;
}

.coverage-date {
  font-size: 12px;
  color: #9ba3af;
}

.coverage-empty {
  font-size: 13px;
  color: #9ba3af;
  text-align: center;
  padding: 20px 0;
}

/* 问题展开行 */
.issue-expand {
  padding: 12px 20px;
  background: #fafbfc;
  border-radius: 6px;
}

.expand-row {
  font-size: 13px;
  color: #334155;
  line-height: 1.6;
  margin-bottom: 6px;
}

.expand-label {
  color: #6b7280;
  font-weight: 500;
  margin-right: 4px;
}

.expand-photos {
  display: inline-flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 4px;
}

/* 项目详情抽屉 */
.project-drawer-content {
  padding: 0 4px;
}

.mini-chart-label {
  font-size: 13px;
  font-weight: 600;
  color: #1a1d26;
  margin-bottom: 8px;
}

.mini-chart-box {
  height: 180px;
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 10px;
}

/* ==================== 动画 ==================== */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ==================== 响应式 ==================== */
@media (max-width: 1200px) {
  .stat-grid { grid-template-columns: repeat(3, 1fr); }
  .charts-grid { grid-template-columns: 1fr; }
  .coverage-grid { grid-template-columns: 1fr; }
}

@media (max-width: 900px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
  .page-header { flex-direction: column; align-items: flex-start; gap: 12px; }
}
</style>
