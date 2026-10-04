<template>
  <div class="dashboard-page dash-premium">
    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="5" animated />
    </div>

    <template v-else>
      <!-- 页面标题 -->
      <div class="phdr">
        <div>
          <div class="eyebrow">Overview · 数据概览</div>
          <h1>品质<span class="g-text">总览</span></h1>
          <div class="phdr-sub">组合品质体检 · 更新于今日</div>
        </div>
        <div class="phdr-acts">
          <button class="btn btn-dark" @click="exportAllData" :disabled="exportingAll">
            <svg viewBox="0 0 16 16"><path d="M2 3v10h12M8 7v6M5 10l3 3 3-3M2 3l3 3" /></svg>
            {{ exportingAll ? '导出中...' : '导出全部报表' }}
          </button>
        </div>
      </div>

      <!-- 核心指标卡片 -->
      <StatsCards :summary="summary" @open-task="openTaskDrawer()" @open-coverage="openCoverageDrawer()" @open-issue="openIssueDrawer()" @open-rect="openRectDrawer()" />

      <!-- 各项目模块得分对比（全宽） -->
      <div class="card">
        <div class="card-h">
          <div style="display:flex;align-items:baseline;gap:8px">
            <span class="card-t">各项目模块得分对比</span>
            <span class="card-d">最新一次检查 · 点击行查看详情</span>
          </div>
          <div style="display:flex;align-items:center;gap:8px">
            <span class="legend" style="font-size:11px">
              <span><i style="background:#edf6f0;border:1px solid var(--ok-border)" />≥90</span>
              <span><i style="background:#faf5e9;border:1px solid var(--warn-border)" />70–89</span>
              <span><i style="background:var(--err-bg);border:1px solid var(--err-border)" />&lt;70</span>
            </span>
            <el-dropdown @command="exportScoreTable">
              <button class="btn btn-sm">
                <svg viewBox="0 0 16 16"><path d="M2 3v10h12M8 7v6M5 10l3 3 3-3M2 3l3 3" /></svg>导出<svg viewBox="0 0 16 16" style="width:10px;height:10px;margin-left:2px"><path d="M4 6l4 4 4-4" /></svg>
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="excel">导出 Excel</el-dropdown-item>
                  <el-dropdown-item command="csv">导出 CSV</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
        <div class="module-table-wrap">
          <el-table :data="projectScores" stripe size="small" class="module-score-table" :header-cell-style="{ background: 'var(--bg-muted)', color: 'var(--ink-900)', fontWeight: 600, fontSize: '12px' }" @row-click="openProjectDrawer">
            <el-table-column prop="project_name" label="项目名称" fixed="left" width="130" show-overflow-tooltip />
            <el-table-column v-for="m in moduleNames" :key="m.key" :label="m.label" width="95" align="center">
              <template #default="{ row }">
                <span v-if="row.modules && row.modules[m.key] != null" class="sp" :class="getSpClass(row.modules[m.key])">{{ row.modules[m.key] }}</span>
                <span v-else class="sp sp-na">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="latest_score" label="总分" fixed="right" width="80" align="center" sortable>
              <template #default="{ row }">
                <span class="sp" :class="getSpClass(row.latest_score)" style="font-size:14px">{{ row.latest_score }}</span>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!projectScores.length" description="暂无数据" :image-size="60" />
        </div>
      </div>

      <!-- 底部双栏：问题分布 + 整改统计 -->
      <div class="charts">
        <div class="card">
          <div class="card-h">
            <span class="card-t">问题按模块分布</span>
            <el-dropdown @command="(cmd) => exportChart('module', cmd)">
              <button class="btn btn-sm">
                <svg viewBox="0 0 16 16"><path d="M2 3v10h12M8 7v6M5 10l3 3 3-3M2 3l3 3" /></svg>导出<svg viewBox="0 0 16 16" style="width:10px;height:10px;margin-left:2px"><path d="M4 6l4 4 4-4" /></svg>
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="png">导出图片</el-dropdown-item>
                  <el-dropdown-item command="excel">导出 Excel</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <div ref="moduleChartRef" class="chart-area"></div>
        </div>
        <div class="card">
          <div class="card-h">
            <span class="card-t">各项目整改完成率</span>
            <el-dropdown @command="(cmd) => exportChart('rect', cmd)">
              <button class="btn btn-sm">
                <svg viewBox="0 0 16 16"><path d="M2 3v10h12M8 7v6M5 10l3 3 3-3M2 3l3 3" /></svg>导出<svg viewBox="0 0 16 16" style="width:10px;height:10px;margin-left:2px"><path d="M4 6l4 4 4-4" /></svg>
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="png">导出图片</el-dropdown-item>
                  <el-dropdown-item command="excel">导出 Excel</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <div ref="rectChartRef" class="chart-area"></div>
        </div>
      </div>

      <!-- 检查得分趋势（原型：平均分趋势卡） -->
      <div class="card" style="margin-top:var(--gap-blk)">
        <div class="card-h">
          <span class="card-t">检查得分趋势</span>
          <span class="card-d">最近 {{ trendTasks.length }} 次已评分检查</span>
        </div>
        <div ref="trendChartRef" class="chart-area trend-area"></div>
      </div>
    </template>

    <!-- ==================== 抽屉组件 ==================== -->
    <TaskDrawer v-model:visible="taskDrawer.visible" :all-projects="allProjects" @go-to-task="goToTask" @export="exportDrawerData('task')" ref="taskDrawerRef" />
    <CoverageDrawer v-model:visible="coverageDrawer.visible" :loading="coverageDrawer.loading" :checked-projects="coverageDrawer.checkedProjects" :unchecked-projects="coverageDrawer.uncheckedProjects" :checked-count="coverageDrawer.checkedCount" :total-projects="summary.total_projects || 0" :coverage-rate="summary.coverage_rate || 0" @go-to-project="goToProjectTasks" @export="exportDrawerData('coverage')" @refresh="loadCoverageDetail" />
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
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { getDashboardStats } from '../../api/stats'
import { getTasks, getProjects } from '../../api/tasks'
import { getAllRectifications } from '../../api/rectification'
import { getScoringSummary } from '../../api/scoring'
import echarts from '../../utils/echarts'
import { RAMP, SEMANTIC, AXIS, TOOLTIP } from '../../utils/chartTheme'
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

// 模块列：从当前展示项目的实际模块动态聚合（兼容蝶城/非蝶城/砺质），无数据时回退蝶城默认
const MODULE_SHORT_LABEL = {
  '客户服务': '客户服务', '安全管理': '安全管理', 'EHS及风险管理': 'EHS', '环境管理': '环境管理',
  '机电运维': '机电运维', '设施维护': '设施维护', '综合管理': '综合管理', '财务管理': '财务管理',
  '管家响应加速度': '管家响应', '安防楼道净通行': '安防楼道', '环境桶净无漏溢': '环境桶净',
  '技术乘梯稳安心': '技术乘梯', 'BI及5S': 'BI及5S',
  '管家礼韵塑新颜': '管家礼韵', '安防礼韵塑新颜': '安防礼韵', '环境礼韵塑新颜': '环境礼韵',
  '技术礼韵塑新颜': '技术礼韵', '其他场所5S': '其他5S'
}
const _DC_FALLBACK = ['客户服务', '安全管理', 'EHS及风险管理', '环境管理', '机电运维', '设施维护', '综合管理', '财务管理']
const moduleNames = computed(() => {
  const seen = new Map()
  for (const p of projectScores.value || []) {
    if (p.modules) {
      for (const k of Object.keys(p.modules)) {
        if (!seen.has(k)) seen.set(k, { key: k, label: MODULE_SHORT_LABEL[k] || k })
      }
    }
  }
  if (!seen.size) {
    for (const k of _DC_FALLBACK) seen.set(k, { key: k, label: MODULE_SHORT_LABEL[k] || k })
  }
  return [...seen.values()]
})

const moduleChartRef = ref(null)
const trendChartRef = ref(null)
let trendChart = null
const trendTasks = ref([])
let moduleChart = null

const rectChartRef = ref(null)
let rectChart = null
const projectRectStats = ref([])

// ==================== 抽屉/弹窗状态 ====================
const taskDrawer = ref({ visible: false, list: [], total: 0, page: 1, pageSize: 20, statusFilter: '', projectFilter: '', loading: false })
const coverageDrawer = ref({ visible: false, checkedProjects: [], uncheckedProjects: [], checkedCount: 0, loading: false })
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
  if (format === 'lizhi') return exportLizhiTable()
  const headers = ['项目名称', ...moduleNames.value.map(m => m.label), '总分']
  const rows = projectScores.value.map(p => {
    return [
      p.project_name,
      ...moduleNames.value.map(m => p.modules?.[m.key] ?? '-'),
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

// ==================== 导出：砺质礼韵专项表（固定 8 列） ====================
const LIZHI_MODULES = ['管家礼韵塑新颜', '安防礼韵塑新颜', '环境礼韵塑新颜', '技术礼韵塑新颜', '其他场所5S']

const exportLizhiTable = () => {
  // 全量项目（含未检查的，留空），按名称排序，对齐砺质月报模板
  const scoreByName = new Map(projectScores.value.map(p => [p.project_name, p]))
  const names = new Set([
    ...allProjects.value.map(p => p.name || p.project_name).filter(Boolean),
    ...projectScores.value.map(p => p.project_name)
  ])
  const ordered = [...names].sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'))

  const headers = ['序号', '项目名称', '项目总分', ...LIZHI_MODULES.map(m => `${m}得分`)]
  const rows = ordered.map((name, idx) => {
    const p = scoreByName.get(name)
    return [
      idx + 1,
      name,
      p?.latest_score ?? '',
      ...LIZHI_MODULES.map(m => p?.modules?.[m] ?? '')
    ]
  })
  const data = buildSheet(headers, rows)
  const ts = new Date().toISOString().slice(0, 10)
  saveExcel(data, `砺质礼韵专项得分表_${ts}.xlsx`, '礼韵专项得分')
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
      const scoreHeaders = ['项目名称', ...moduleNames.value.map(m => m.label), '总分']
      const scoreRows = projectScores.value.map(p => [
        p.project_name, ...moduleNames.value.map(m => p.modules?.[m.key] ?? '-'), p.latest_score ?? '-'
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
  let rectRaw = []
  try {
    const res = await getDashboardStats()
    summary.value = res.summary || {}
    projectScores.value = res.project_latest_scores || []
    issueByModule.value = res.issue_by_module || []
    rectRaw = res.project_rectification_stats || []
    coverageDetail.value = res.coverage_detail || { checked_projects: [], unchecked_projects: [] }

    // 预加载项目列表（供筛选器使用）
    try {
      const projRes = await getProjects()
      allProjects.value = projRes.items || []
    } catch (e) { /* ignore */ }

    // 补齐零整改项目：全量项目都应出现在「各项目整改完成率」中
    const have = new Set(rectRaw.map(r => r.project_name))
    const missing = allProjects.value
      .map(p => p.name)
      .filter(n => n && !have.has(n))
      .map(n => ({ project_name: n, approved: 0, pending: 0, total: 0, rate: 0 }))
    projectRectStats.value = [...rectRaw, ...missing]
  } catch (e) {
    console.error('获取仪表盘数据失败:', e)
  } finally {
    loading.value = false
  }

  // 趋势数据：最近 12 次有评分的检查（按检查日排序）
  try {
    const tRes = await getTasks({ page: 1, page_size: 60 })
    trendTasks.value = (tRes.items || [])
      .filter(t => t.total_score != null && t.total_score > 0 && t.check_date)
      .sort((a, b) => (a.check_date || '').localeCompare(b.check_date || ''))
      .slice(-12)
  } catch (e) { /* ignore */ }

  await nextTick()
  renderModuleChart()
  renderRectChart()
  renderTrendChart()
}

// ==================== 趋势折线（原型：平均分趋势卡） ====================
const renderTrendChart = () => {
  if (!trendChartRef.value || !trendTasks.value.length) return
  if (!trendChart) {
    trendChart = echarts.init(trendChartRef.value)
  }
  const data = trendTasks.value
  trendChart.setOption({
    tooltip: { trigger: 'axis', ...TOOLTIP },
    grid: { left: 45, right: 20, top: 15, bottom: 28 },
    xAxis: {
      type: 'category',
      data: data.map(t => (t.check_date || '').slice(5)),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { fontSize: 11, color: AXIS.axisLabel }
    },
    yAxis: {
      type: 'value',
      min: 50,
      max: 100,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: AXIS.splitLine } },
      axisLabel: { fontSize: 11, color: AXIS.axisLabel }
    },
    series: [{
      type: 'line',
      data: data.map(t => t.total_score),
      smooth: 0.35,
      symbol: 'circle',
      symbolSize: 5,
      lineStyle: { width: 2, color: '#0f8a80' },
      itemStyle: { color: '#0f8a80', borderWidth: 2, borderColor: '#fff' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(15, 138, 128, 0.14)' },
          { offset: 1, color: 'rgba(15, 138, 128, 0.01)' }
        ])
      }
    }]
  })
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
  const reversed = [...issueByModule.value].reverse()
  moduleChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      ...TOOLTIP
    },
    grid: { left: 110, right: 40, top: 8, bottom: 8 },
    xAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false }
    },
    yAxis: {
      type: 'category',
      data: reversed.map(i => i.module_name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { fontSize: 12, color: '#474753', width: 90, overflow: 'truncate' }
    },
    series: [{
      type: 'bar',
      data: reversed.map((i, idx) => ({
        value: i.count,
        itemStyle: {
          color: RAMP[idx % RAMP.length],
          borderRadius: 12
        }
      })),
      barCategoryGap: '45%',
      barMaxWidth: 18,
      showBackground: true,
      backgroundStyle: { color: '#eef0f4', borderRadius: 12 },
      label: { show: true, position: 'right', fontSize: 12, fontWeight: 600, color: '#61616d' },
      emphasis: {
        itemStyle: { shadowBlur: 6, shadowColor: 'rgba(22,22,28,0.1)' }
      }
    }]
  })
}

const renderRectChart = () => {
  if (!rectChartRef.value || !projectRectStats.value.length) return
  // 高度随项目数自适应，避免横条拥挤
  rectChartRef.value.style.height = Math.max(300, projectRectStats.value.length * 38) + 'px'
  if (!rectChart) {
    rectChart = echarts.init(rectChartRef.value)
  } else {
    rectChart.resize()
  }
  const data = [...projectRectStats.value].reverse()
  rectChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      ...TOOLTIP,
      formatter: (params) => {
        const name = params[0].name
        const approved = params.find(p => p.seriesName === '已整改')?.value || 0
        const pending = params.find(p => p.seriesName === '未整改')?.value || 0
        const total = approved + pending
        const rate = total > 0 ? ((approved / total) * 100).toFixed(1) : 0
        return `<div style="font-weight:600;margin-bottom:4px">${name}</div>` +
          `<div>已整改：<span style="color:${SEMANTIC.ok};font-weight:600">${approved}</span></div>` +
          `<div>未整改：<span style="color:#61616d;font-weight:600">${pending}</span></div>` +
          `<div style="margin-top:4px;border-top:1px solid #eee;padding-top:4px">完成率：<b>${rate}%</b></div>`
      }
    },
    legend: {
      data: ['已整改', '未整改'],
      top: 0,
      right: 10,
      textStyle: { fontSize: 12, color: '#474753' },
      itemWidth: 12,
      itemHeight: 12,
      itemGap: 16
    },
    grid: { left: 110, right: 46, top: 30, bottom: 8 },
    xAxis: {
      type: 'value',
      max: Math.max(...data.map(i => (i.approved || 0) + (i.pending || 0)), 1) * 1.14,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false }
    },
    yAxis: {
      type: 'category',
      data: data.map(i => i.project_name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { fontSize: 12, color: '#474753', width: 90, overflow: 'truncate' }
    },
    series: [
      {
        name: '已整改',
        type: 'bar',
        stack: 'total',
        data: data.map(i => i.approved),
        itemStyle: {
          color: SEMANTIC.ok,
          borderRadius: [0, 0, 0, 0]
        },
        barWidth: 18,
        emphasis: { itemStyle: { shadowBlur: 6, shadowColor: 'rgba(39,148,91,0.2)' } }
      },
      {
        name: '未整改',
        type: 'bar',
        stack: 'total',
        data: data.map(i => i.pending),
        itemStyle: {
          color: SEMANTIC.neutral,
          borderRadius: [0, 12, 12, 0]
        },
        barWidth: 18,
        emphasis: { itemStyle: { shadowBlur: 6, shadowColor: 'rgba(22,22,28,0.15)' } }
      },
      {
        name: '完成率',
        type: 'scatter',
        symbolSize: 0,
        silent: true,
        data: data.map(i => {
          const total = (i.approved || 0) + (i.pending || 0)
          return {
            value: [total, i.project_name],
            rate: total > 0 ? Math.round(((i.approved || 0) / total) * 100) : 0
          }
        }),
        label: {
          show: true,
          position: 'right',
          fontSize: 12,
          fontWeight: 600,
          color: '#61616d',
          formatter: p => p.data.rate + '%'
        }
      }
    ]
  })
}

// ==================== 工具函数 ====================
const getSpClass = (score) => {
  if (score >= 90) return 'sp-hi'
  if (score >= 70) return 'sp-mid'
  return 'sp-lo'
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
  coverageDrawer.value = {
    visible: false,
    checkedProjects: [],
    uncheckedProjects: [],
    checkedCount: 0,
    loading: false,
    page: 1,
    pageSize: 20,
    statusFilter: ''
  }
  await loadCoverageDetail()
  coverageDrawer.value.visible = true
}

const loadCoverageDetail = async () => {
  coverageDrawer.value.loading = true
  try {
    const res = await getDashboardStats()
    coverageDetail.value = res.coverage_detail || { checked_projects: [], unchecked_projects: [] }
    coverageDrawer.value.checkedProjects = coverageDetail.value.checked_projects || []
    coverageDrawer.value.uncheckedProjects = coverageDetail.value.unchecked_projects || []
    coverageDrawer.value.checkedCount = (coverageDetail.value.checked_projects || []).length
  } catch (e) {
    console.error('加载覆盖率详情失败:', e)
  } finally {
    coverageDrawer.value.loading = false
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
      ...TOOLTIP
    },
    grid: { left: 45, right: 15, top: 10, bottom: 25 },
    xAxis: {
      type: 'category',
      data: sorted.map(t => t.check_date || ''),
      axisLine: { lineStyle: { color: AXIS.axisLine } },
      axisTick: { show: false },
      axisLabel: { fontSize: 10, rotate: 30, color: AXIS.axisLabel }
    },
    yAxis: {
      type: 'value',
      min: 0, max: 100,
      splitLine: { lineStyle: { color: AXIS.splitLine, type: 'dashed' } },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { fontSize: 10, color: AXIS.axisLabel }
    },
    series: [{
      type: 'line',
      data: sorted.map(t => t.total_score),
      smooth: 0.4,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { width: 2, color: '#0f8a80' },
      itemStyle: { color: '#0f8a80', borderWidth: 2, borderColor: '#fff' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(15, 138, 128, 0.15)' },
          { offset: 1, color: 'rgba(15, 138, 128, 0.01)' }
        ])
      }
    }]
  })
}

const handleResize = () => {
  trendChart?.resize()
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

/* ==================== 页面标题 (prototype .phdr) ==================== */
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

.phdr-acts {
  display: flex;
  gap: 8px;
}

/* ==================== Button (prototype .btn) ==================== */

/* ==================== Card (prototype .card) ==================== */
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

.card-d {
  font-size: 12px;
  color: var(--ink-400);
  margin-left: 8px;
}

/* ==================== Score pills (prototype .sp) ==================== */
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

.sp-hi { background: var(--ok-bg); color: var(--ok); }
.sp-mid { background: var(--warn-bg); color: var(--warn); }
.sp-lo { background: var(--err-bg); color: var(--err); }
.sp-na { color: var(--ink-200); }

/* ==================== Charts grid ==================== */
.charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.chart-area {
  height: 300px;
  padding: 8px;
}

.trend-area {
  height: 210px;
}

/* ==================== Module table ==================== */
.module-table-wrap {
  padding: 0;
}

.module-score-table {
  width: 100%;
  cursor: pointer;
}

/* Table header override */
.card :deep(.el-table) {
  --el-table-border-color: var(--ink-100);
  --el-table-header-bg-color: var(--bg-muted);
}

.card :deep(.el-table th.el-table__cell) {
  font-size: 12px;
  font-weight: 700;
  color: var(--ink-400);
  letter-spacing: 0.3px;
  background: var(--bg-muted);
}

.card :deep(.el-table td.el-table__cell) {
  font-size: 14px;
  font-weight: 500;
  color: var(--ink-600);
}

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
  background: var(--blue-bg);
  border: 1px solid var(--brand-border);
  border-radius: 10px;
  padding: 14px 18px;
  font-size: 14px;
  color: var(--ink-900);
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
  border-bottom: 2px solid var(--ink-200);
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
  background: var(--ok-bg);
}

.coverage-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--ink-900);
}

.coverage-date {
  font-size: 12px;
  color: var(--ink-400);
}

.coverage-empty {
  font-size: 13px;
  color: var(--ink-400);
  text-align: center;
  padding: 20px 0;
}

/* 问题展开行 */
.issue-expand {
  padding: 12px 20px;
  background: var(--bg);
  border-radius: 6px;
}

.expand-row {
  font-size: 13px;
  color: var(--ink-900);
  line-height: 1.6;
  margin-bottom: 6px;
}

.expand-label {
  color: var(--ink-600);
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
  color: var(--ink-900);
  margin-bottom: 8px;
}

.mini-chart-box {
  height: 180px;
  background: var(--bg-card);
  border: 1px solid var(--ink-100);
  border-radius: 10px;
}

/* ==================== 动画 ==================== */
@keyframes kpiIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ==================== 响应式 ==================== */
@media (max-width: 1200px) {
  .charts { grid-template-columns: 1fr; }
  .coverage-grid { grid-template-columns: 1fr; }
}

@media (max-width: 900px) {
  .phdr { flex-direction: column; align-items: flex-start; gap: 12px; }
}

/* ===== REF-DASH 参考图仪表盘语法 ===== */
.dashboard-page .phdr h1 {
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -0.8px;
}
.dashboard-page .phdr { margin-bottom: 26px; }
.dashboard-page .phdr-sub { font-size: 14px; margin-top: 6px; }

/* 磁贴 */
.dashboard-page .card {
  border-radius: 20px;
  border: 1px solid var(--ink-100);
  box-shadow: 0 1px 2px rgba(16, 40, 36, 0.04), 0 14px 36px -14px rgba(16, 40, 36, 0.10);
}
.dashboard-page .card-h { padding: 18px 22px; border-bottom: 1px solid var(--ink-100); }
.dashboard-page .card-t { font-size: 16px; }
.dashboard-page .charts { gap: 18px; margin-top: 18px; }
.dashboard-page .chart-area { padding: 6px 14px 10px; }
.dashboard-page .module-table-wrap :deep(.el-table) { --el-table-border-color: var(--ink-100); }
</style>
