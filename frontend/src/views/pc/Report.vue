<template>
  <div class="page on">
    <!-- Page header -->
    <div class="phdr">
      <div>
        <h1>品质报告</h1>
        <div class="phdr-sub">AI品质检查报告查看、下载与管理</div>
      </div>
    </div>

    <!-- Filter bar -->
    <div class="filters">
      <input
        class="f-input"
        placeholder="搜索项目/报告ID"
        :value="searchKeyword"
        @input="searchKeyword = $event.target.value"
        @keyup.enter="onSearch"
        style="min-width:180px"
      />
      <div class="f-sep"></div>
      <input
        class="f-input"
        type="date"
        :value="dateRange ? dateRange[0] : ''"
        @input="onDateStartChange($event)"
        style="min-width:130px"
      />
      <span style="font-size:13px;color:var(--ink-400)">至</span>
      <input
        class="f-input"
        type="date"
        :value="dateRange ? dateRange[1] : ''"
        @input="onDateEndChange($event)"
        style="min-width:130px"
      />
      <button class="f-reset" @click="resetFilters">
        <svg viewBox="0 0 16 16" width="12" height="12"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" fill="none" stroke-width="1.8"/></svg>
        重置
      </button>
    </div>

    <!-- Report table card -->
    <div class="card" v-if="!loading && filteredReports.length > 0">
      <table class="tbl">
        <thead>
          <tr>
            <th>报告编号</th>
            <th>项目名称</th>
            <th>检查标准</th>
            <th>项目总分</th>
            <th>生成时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in filteredReports" :key="row.task_id">
            <td>{{ row.report_id }}</td>
            <td style="text-align:left;font-family:var(--sans);font-weight:600;color:var(--ink-900)">{{ row.project_name || '-' }}</td>
            <td>
              <span v-if="row.standard_type === 'diecheng'" class="kt kt-blue">蝶城</span>
              <span v-else class="kt kt-warn">非蝶城</span>
            </td>
            <td>
              <span v-if="row.total_score" class="sp" :class="getScoreSpClass(row.total_score)" @click="viewReport(row)" style="cursor:pointer">{{ row.total_score.toFixed(2) }}</span>
              <span v-else class="sp sp-na">-</span>
            </td>
            <td style="font-family:var(--mono);font-size:12px;color:var(--ink-400)">{{ formatDate(row.generated_at) }}</td>
            <td>
              <button class="act" @click="viewReport(row)">查看</button>
              <button class="act" @click="downloadFile(row.task_id, 'word')">Word</button>
              <button class="act" @click="downloadFile(row.task_id, 'pdf')">PDF</button>
              <button v-if="authStore.isAdmin" class="act act-err" @click="onDeleteReport(row)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div class="pagi">
        <div class="pagi-info">共 <b>{{ filteredReports.length }}</b> 条</div>
        <div class="pagi-btns">
          <button class="pg"><svg viewBox="0 0 16 16"><path d="M10 3L5 8l5 5"/></svg></button>
          <button class="pg on">1</button>
          <button class="pg"><svg viewBox="0 0 16 16"><path d="M6 3l5 5-5 5"/></svg></button>
        </div>
      </div>
    </div>

    <!-- Loading state -->
    <div class="card" v-if="loading" style="padding:60px 0;text-align:center">
      <div style="font-size:14px;font-weight:600;color:var(--ink-400)">加载中...</div>
    </div>

    <!-- Empty state -->
    <div class="card" v-if="!loading && filteredReports.length === 0" style="padding:60px 0;text-align:center">
      <div style="font-size:14px;font-weight:600;color:var(--ink-400)">暂无报告数据</div>
      <div style="font-size:12px;margin-top:4px;color:var(--ink-400)">尝试调整筛选条件</div>
    </div>

    <!-- Report detail drawer -->
    <el-drawer v-model="showDetail" :title="`报告详情 - ${currentReport.report_id}`" size="65%" class="styled-drawer">
      <template v-if="reportData">
        <div class="report-detail">
          <div class="detail-score-banner">
            <div class="score-banner-content">
              <div class="score-banner-left">
                <div class="score-banner-label">项目总分</div>
                <div class="score-banner-value" :class="getScoreClass(reportData.total_score)">
                  {{ reportData.total_score?.toFixed(2) || '-' }}
                </div>
              </div>
              <div class="score-banner-right">
                <div class="score-banner-info">{{ reportData.project_name }}</div>
                <div class="score-banner-date">{{ reportData.check_date }}</div>
              </div>
            </div>
          </div>

          <el-descriptions title="基本信息" :column="2" border>
            <el-descriptions-item label="项目名称">{{ reportData.project_name }}</el-descriptions-item>
            <el-descriptions-item label="检查日期">{{ reportData.check_date }}</el-descriptions-item>
            <el-descriptions-item label="项目总分">
              <span :class="getScoreClass(reportData.total_score)">{{ reportData.total_score?.toFixed(2) }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="生成时间">{{ formatDate(reportData.generated_at) }}</el-descriptions-item>
          </el-descriptions>

          <!-- Module scores -->
          <h3 style="margin: 20px 0 12px">各模块得分</h3>
          <el-table :data="reportData.content?.modules || []" border size="small">
            <el-table-column prop="module_name" label="模块名称" />
            <el-table-column label="得分" width="100">
              <template #default="{ row }">
                <span :class="getScoreClass(row.module_pct_score)">{{ row.module_pct_score?.toFixed(2) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="权重" width="80">
              <template #default="{ row }">{{ (row.weight_ratio * 100).toFixed(0) }}%</template>
            </el-table-column>
            <el-table-column label="贡献分" width="100">
              <template #default="{ row }">{{ row.weighted_contribution?.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="issue_count" label="问题数" width="80" />
          </el-table>

          <!-- AI module analysis -->
          <h3 style="margin: 20px 0 12px">AI 模块分析（DeepSeek）</h3>
          <el-collapse>
            <el-collapse-item v-for="ma in (reportData.content?.module_analyses || [])" :key="ma.module_name"
              :title="`${ma.module_name}（${ma.module_pct_score?.toFixed(2)}分）`">
              <p><strong>总体评价：</strong>{{ ma.overall_evaluation }}</p>
              <p v-if="ma.main_issues?.length"><strong>主要问题：</strong></p>
              <ul v-if="ma.main_issues?.length">
                <li v-for="iss in ma.main_issues" :key="iss">{{ iss }}</li>
              </ul>
              <p v-if="ma.improvement_suggestions?.length"><strong>改进建议：</strong></p>
              <ul v-if="ma.improvement_suggestions?.length">
                <li v-for="sug in ma.improvement_suggestions" :key="sug">{{ sug }}</li>
              </ul>
            </el-collapse-item>
          </el-collapse>

          <!-- AI full report -->
          <h3 style="margin: 20px 0 12px">AI 综合分析报告</h3>
          <div class="markdown-body" v-html="renderMarkdown(reportData.content?.ai_full_report || '')"></div>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { RefreshLeft, View, Document, Download } from '@element-plus/icons-vue'
import { getReportList, getReport, downloadReportFile, deleteReport } from '../../api/report'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '../../stores/auth'
import { marked } from '../../utils/markdown'

const reports = ref([])
const loading = ref(false)
const searchKeyword = ref('')
const dateRange = ref(null)

const showDetail = ref(false)
const currentReport = ref({})
const reportData = ref(null)
const viewLoading = ref(false)
const authStore = useAuthStore()

const filteredReports = computed(() => {
  let list = reports.value
  if (searchKeyword.value) {
    const q = searchKeyword.value.toLowerCase()
    list = list.filter(r =>
      (r.project_name || '').toLowerCase().includes(q) ||
      (r.report_id || '').toLowerCase().includes(q)
    )
  }
  if (dateRange.value && dateRange.value.length === 2) {
    const [start, end] = dateRange.value
    list = list.filter(r => {
      const d = (r.generated_at || '').slice(0, 10)
      return d >= start && d <= end
    })
  }
  return list
})

const fetchReports = async () => {
  loading.value = true
  try {
    const res = await getReportList({ page: 1, page_size: 100 })
    console.log('[Report] API response:', res)
    reports.value = res.items || []
    if (res.total === 0) {
      ElMessage.warning('暂无报告数据')
    } else {
      console.log(`[Report] Loaded ${res.items?.length || 0} reports, total: ${res.total}`)
    }
  } catch (e) {
    console.error('[Report] Fetch error:', e)
    ElMessage.error('获取报告列表失败: ' + (e.response?.data?.detail || e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const viewReport = async (row) => {
  if (viewLoading.value) return
  viewLoading.value = true
  currentReport.value = row
  try {
    const res = await getReport(row.task_id)
    reportData.value = res
    showDetail.value = true
  } catch (e) {
    ElMessage.error('获取报告详情失败')
  } finally {
    viewLoading.value = false
  }
}

const downloadFile = async (taskId, format) => {
  try {
    await downloadReportFile(taskId, format)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '下载失败')
  }
}

const onSearch = () => { /* filtered computed handles it */ }
const resetFilters = () => { searchKeyword.value = ''; dateRange.value = null }

const formatDate = (iso) => iso ? iso.slice(0, 19).replace('T', ' ') : '-'
const getScoreClass = (score) => {
  if (!score) return ''
  if (score >= 90) return 'score-excellent'
  if (score >= 80) return 'score-good'
  if (score >= 60) return 'score-normal'
  return 'score-poor'
}

/* Helper: map numeric score to prototype .sp-* class */
const getScoreSpClass = (score) => {
  if (!score) return 'sp-na'
  if (score >= 80) return 'sp-hi'
  if (score >= 60) return 'sp-mid'
  return 'sp-lo'
}

/* Helper: date input binding for native inputs */
const onDateStartChange = (e) => {
  const v = e.target.value
  if (!v) { dateRange.value = null; return }
  dateRange.value = [v, dateRange.value?.[1] || '']
}
const onDateEndChange = (e) => {
  const v = e.target.value
  if (!v) { dateRange.value = null; return }
  dateRange.value = [dateRange.value?.[0] || '', v]
}

const renderMarkdown = (text) => {
  if (!text) return ''
  try { return marked(text) } catch { return text.replace(/\n/g, '<br>') }
}

const onDeleteReport = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定删除报告 ${row.report_id}？删除后文件将无法恢复。`,
      '确认删除',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
  } catch { return }
  try {
    await deleteReport(row.task_id)
    ElMessage.success('报告已删除')
    fetchReports()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

onMounted(() => fetchReports())
</script>

<style scoped>
/* ===== Page ===== */
.page { display: block; }
.page.on { animation: pgIn .25s var(--ease); }

/* ===== Page header ===== */
.phdr { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 20px; }
.phdr h1 { font-size: 22px; font-weight: 800; color: var(--ink-900); letter-spacing: -.4px; margin: 0; }
.phdr-sub { font-size: 13px; color: var(--ink-400); margin-top: 3px; }
.phdr-acts { display: flex; gap: 8px; }

/* ===== Filter bar ===== */
.filters { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.f-input { padding: 7px 12px; border-radius: var(--r, 6px); font-size: 13px; font-weight: 400; color: var(--ink-800); border: 1px solid var(--ink-100); background: var(--bg-card); font-family: var(--sans); transition: all .12s; min-width: 180px; }
.f-input::placeholder { color: var(--ink-400); }
.f-input:hover { border-color: var(--ink-200); }
.f-input:focus { outline: none; border-color: var(--blue); box-shadow: 0 0 0 3px rgba(37,99,235,.1); }
.f-sep { width: 1px; height: 24px; background: var(--ink-100); }
.f-reset { font-size: 13px; font-weight: 500; color: var(--ink-400); cursor: pointer; border: none; background: none; font-family: var(--sans); padding: 6px 10px; border-radius: var(--r-sm, 4px); transition: all .1s; display: inline-flex; align-items: center; gap: 4px; }
.f-reset:hover { color: var(--ink-800); background: var(--bg-muted); }
.f-reset svg { width: 12px; height: 12px; stroke: currentColor; fill: none; stroke-width: 2; }

/* ===== Card ===== */
.card { background: var(--bg-card); border: 1px solid var(--ink-100); border-radius: var(--r-lg, 10px); overflow: hidden; margin-bottom: 14px; animation: kpiIn .3s cubic-bezier(.25,.1,.25,1) .05s both; }

/* ===== Table ===== */
.tbl { width: 100%; border-collapse: collapse; }
.tbl th { font-size: 12px; font-weight: 700; color: var(--ink-400); letter-spacing: .3px; text-align: center; padding: 10px 10px; background: var(--bg-muted); border-bottom: 1px solid var(--ink-100); }
.tbl th:first-child { text-align: left; padding-left: 20px; }
.tbl td { font-size: 14px; font-weight: 500; text-align: center; padding: 12px 10px; border-bottom: 1px solid var(--ink-100); color: var(--ink-600); }
.tbl td:first-child { text-align: left; padding-left: 20px; font-family: var(--mono); font-size: 12px; color: var(--ink-400); }
.tbl tbody tr { cursor: pointer; transition: background .08s; }
.tbl tbody tr:hover { background: var(--bg, #fafaf8); }

/* ===== Kind/Category tags ===== */
.kt { font-size: 11px; font-family: var(--mono); font-weight: 600; padding: 2px 7px; border-radius: 3px; }
.kt-ok { background: var(--ok-bg); color: var(--ok); }
.kt-warn { background: var(--warn-bg); color: var(--warn); }
.kt-err { background: var(--err-bg); color: var(--err); }
.kt-teal { background: var(--teal-50); color: var(--teal-700); }
.kt-muted { background: var(--bg-muted); color: var(--ink-600); }
.kt-blue { background: var(--blue-bg); color: var(--blue); }

/* ===== Score pills ===== */
.sp { display: inline-block; min-width: 32px; padding: 2px 6px; border-radius: 3px; font-family: var(--mono); font-size: 13px; font-weight: 700; text-align: center; }
.sp-hi { background: var(--ok-bg); color: var(--ok); }
.sp-mid { background: var(--warn-bg); color: var(--warn); }
.sp-lo { background: var(--err-bg); color: var(--err); }
.sp-na { color: var(--ink-200); }

/* ===== Action buttons ===== */
.act { font-size: 12px; font-weight: 600; color: var(--blue); cursor: pointer; border: none; background: none; font-family: var(--sans); padding: 4px 8px; border-radius: var(--r-sm, 4px); transition: background .1s; }
.act:hover { background: var(--blue-bg); }
.act + .act { margin-left: 2px; }
.act-warn { color: var(--warn); }
.act-warn:hover { background: var(--warn-bg); }
.act-ok { color: var(--ok); }
.act-ok:hover { background: var(--ok-bg); }
.act-err { color: var(--err); }
.act-err:hover { background: var(--err-bg); }

/* ===== Pagination ===== */
.pagi { display: flex; align-items: center; justify-content: space-between; padding: 14px 20px; border-top: 1px solid var(--ink-100); }
.pagi-info { font-size: 12px; color: var(--ink-400); }
.pagi-info b { color: var(--ink-800); }
.pagi-btns { display: flex; gap: 3px; }
.pg { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: var(--r-sm, 4px); font-size: 13px; font-weight: 500; color: var(--ink-600); cursor: pointer; border: 1px solid var(--ink-100); background: var(--bg-card); transition: all .1s; font-family: var(--sans); }
.pg:hover { background: var(--bg-muted); }
.pg.on { background: var(--blue); color: #fff; border-color: var(--blue); }
.pg svg { width: 12px; height: 12px; stroke: currentColor; fill: none; stroke-width: 2; }

/* ===== Score Colors (for drawer detail) ===== */
.score-excellent { color: var(--ok); font-weight: bold; }
.score-good { color: var(--blue); font-weight: bold; }
.score-normal { color: var(--warn); font-weight: bold; }
.score-poor { color: var(--err); font-weight: bold; }

/* ===== Report Detail Drawer ===== */
.report-detail { padding: 0 16px; }
.detail-score-banner { position: relative; border-radius: 10px; overflow: hidden; margin-bottom: 20px; background: linear-gradient(135deg, var(--blue-bg), var(--blue-bg)); border: 1px solid var(--blue-bg); }
.score-banner-content { padding: 24px; display: flex; align-items: center; justify-content: space-between; color: var(--ink-900); }
.score-banner-left { display: flex; flex-direction: column; }
.score-banner-label { font-size: 13px; color: var(--ink-600); margin-bottom: 4px; }
.score-banner-value { font-size: 36px; font-weight: 800; color: var(--blue) !important; }
.score-banner-info { font-size: 16px; font-weight: 600; }
.score-banner-date { font-size: 13px; color: var(--ink-600); margin-top: 4px; }

/* ===== Drawer ===== */
:deep(.styled-drawer .el-drawer__header) { background: var(--bg-muted); padding: 16px 20px; margin-bottom: 0; border-bottom: 1px solid var(--ink-200); }

/* ===== Markdown Body ===== */
.markdown-body { line-height: 1.8; background: #ffffff; padding: 16px 20px; border-radius: 8px; border: 1px solid var(--ink-200); color: var(--ink-900); }
.markdown-body :deep(h1), .markdown-body :deep(h2), .markdown-body :deep(h3) { margin: 16px 0 8px; color: var(--ink-900); font-weight: 600; }
.markdown-body :deep(table) { width: 100%; border-collapse: collapse; margin: 8px 0; }
.markdown-body :deep(th), .markdown-body :deep(td) { border: 1px solid var(--ink-200); padding: 8px 12px; }
.markdown-body :deep(th) { background: var(--bg-muted); font-weight: 600; color: var(--ink-600); }
.markdown-body :deep(ul) { padding-left: 20px; }

/* ===== Animations ===== */
@keyframes kpiIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
@keyframes pgIn { from { opacity: 0; } to { opacity: 1; } }
</style>
