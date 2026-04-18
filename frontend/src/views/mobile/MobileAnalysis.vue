<template>
  <div class="analysis-page">
    <van-nav-bar title="综合分析">
      <template #right>
        <van-icon name="user-o" size="20" @click="showUser = true" />
      </template>
    </van-nav-bar>

    <!-- 模式切换 -->
    <van-tabs v-model:active="mode" shrink sticky offset-top="46">
      <van-tab title="跨项目对比" name="cross_project">
        <div class="param-section">
          <van-cell title="报告 A" is-link :value="reportALabel || '请选择'" @click="openPicker('a')" />
          <van-cell title="报告 B" is-link :value="reportBLabel || '请选择'" @click="openPicker('b')" />
        </div>
      </van-tab>
      <van-tab title="跨时段对比" name="cross_time">
        <div class="param-section">
          <van-cell title="选择项目" is-link :value="selectedProjectLabel || '请选择'" @click="showProjectPicker = true" />
          <template v-if="projectReports.length > 0">
            <van-cell title="报告 T1（较早）" is-link :value="reportALabel || '请选择'" @click="openPicker('a')" />
            <van-cell title="报告 T2（较晚）" is-link :value="reportBLabel || '请选择'" @click="openPicker('b')" />
          </template>
        </div>
      </van-tab>
      <van-tab title="全项目概览" name="all_projects">
        <div class="param-section">
          <van-cell title="开始日期" is-link :value="form.time_range_start || '请选择'" @click="showStartPicker = true" />
          <van-cell title="结束日期" is-link :value="form.time_range_end || '请选择'" @click="showEndPicker = true" />
        </div>
      </van-tab>
      <van-tab title="历史记录" name="history">
        <div class="history-section">
          <van-loading v-if="historyLoading" class="history-loading-center" />
          <van-empty v-else-if="historyList.length === 0" description="暂无分析记录" />
          <div v-else>
            <div v-for="h in historyList" :key="h.analysis_id" class="history-card" @click="viewHistoryItem(h)">
              <div class="history-header">
                <van-tag :type="h.mode === 'cross_project' ? 'primary' : h.mode === 'cross_time' ? 'success' : 'warning'" size="small">
                  {{ modeLabel(h.mode) }}
                </van-tag>
                <span class="history-time">{{ h.created_at?.slice(0, 16).replace('T', ' ') }}</span>
              </div>
              <div class="history-summary">{{ h.summary || '无摘要' }}</div>
              <div class="history-footer">
                <van-tag plain size="small" :type="h.status === 'completed' ? 'success' : 'danger'">
                  {{ h.status === 'completed' ? '已完成' : '失败' }}
                </van-tag>
              </div>
            </div>
          </div>
        </div>
      </van-tab>
    </van-tabs>

    <!-- 分析参数和结果区域（仅非历史模式显示） -->
    <template v-if="mode !== 'history'">
    <!-- 开始分析按钮 -->
    <div class="action-bar">
      <van-button type="primary" block round :loading="analyzing" @click="onStartAnalysis">
        {{ analyzing ? '分析中...' : '开始分析' }}
      </van-button>
    </div>

    <!-- 进度 -->
    <div v-if="analyzing" class="progress-section">
      <van-progress :percentage="progressPct" :stroke-width="8" :show-pivot="true" color="#2563eb" />
      <p class="progress-text">{{ progressStep }}</p>
    </div>

    <!-- 结果 -->
    <div v-if="result && !analyzing" class="result-section">

      <!-- 1. 执行摘要 + 分数对比 -->
      <div class="result-card">
        <div class="result-title">执行摘要</div>
        <p class="result-text">{{ result.executive_summary || '无摘要' }}</p>

        <!-- 分数 VS 对比 -->
        <div v-if="result.score_analysis" class="score-vs-row">
          <div class="score-vs-block">
            <div class="score-vs-label">{{ result.label_a || 'A' }}</div>
            <div class="score-vs-num" :class="winnerClass('a')">{{ result.score_analysis.total_score_a?.toFixed(1) ?? '-' }}</div>
            <van-tag :type="gradeTagType(result.score_analysis.grade_a)" size="medium">{{ result.score_analysis.grade_a || '-' }}</van-tag>
          </div>
          <div class="score-vs-sep">VS</div>
          <div class="score-vs-block">
            <div class="score-vs-label">{{ result.label_b || 'B' }}</div>
            <div class="score-vs-num" :class="winnerClass('b')">{{ result.score_analysis.total_score_b?.toFixed(1) ?? '-' }}</div>
            <van-tag :type="gradeTagType(result.score_analysis.grade_b)" size="medium">{{ result.score_analysis.grade_b || '-' }}</van-tag>
          </div>
        </div>

        <!-- 全项目概览统计 -->
        <div v-if="result.score_analysis?.statistics" class="stats-grid">
          <div class="stat-mini">
            <span class="stat-mini-val">{{ result.score_analysis.statistics.count }}</span>
            <span class="stat-mini-label">项目数</span>
          </div>
          <div class="stat-mini">
            <span class="stat-mini-val">{{ result.score_analysis.statistics.mean?.toFixed(1) }}</span>
            <span class="stat-mini-label">平均分</span>
          </div>
          <div class="stat-mini">
            <span class="stat-mini-val">{{ result.score_analysis.statistics.max?.toFixed(1) }}</span>
            <span class="stat-mini-label">最高分</span>
          </div>
          <div class="stat-mini">
            <span class="stat-mini-val">{{ result.score_analysis.statistics.min?.toFixed(1) }}</span>
            <span class="stat-mini-label">最低分</span>
          </div>
        </div>
      </div>

      <!-- 2. 模块得分对比表 -->
      <div v-if="result.comparison_matrix?.length" class="result-card">
        <div class="result-title">模块得分对比</div>
        <div class="module-table">
          <div class="module-header">
            <span class="col-name">模块</span>
            <span class="col-score">{{ result.label_a || 'A' }}</span>
            <span class="col-score">{{ result.label_b || 'B' }}</span>
            <span class="col-diff">差异</span>
            <span class="col-winner">优胜</span>
          </div>
          <div v-for="m in result.comparison_matrix" :key="m.module_name" class="module-row">
            <span class="col-name">{{ m.module_name }}</span>
            <span class="col-score" :class="getScoreColor(m.score_a)">{{ m.score_a?.toFixed(1) ?? '-' }}</span>
            <span class="col-score" :class="getScoreColor(m.score_b)">{{ m.score_b?.toFixed(1) ?? '-' }}</span>
            <span class="col-diff" :class="diffClass(m.diff)">{{ m.diff > 0 ? '+' : '' }}{{ m.diff?.toFixed(2) ?? '-' }}</span>
            <span class="col-winner">
              <van-tag size="small" :type="winnerTagType(m.winner)">{{ m.winner === 'Tie' ? '持平' : m.winner }}</van-tag>
            </span>
          </div>
        </div>
      </div>

      <!-- 3. 项目排名（全项目模式） -->
      <div v-if="result.mode === 'all_projects' && result.score_analysis?.ranking?.length" class="result-card">
        <div class="result-title">项目排名</div>
        <van-cell-group inset>
          <van-cell v-for="(p, i) in result.score_analysis.ranking" :key="p.project_name">
            <template #title>
              <span class="rank-num" :class="i < 3 ? 'rank-top' : ''">{{ i + 1 }}</span>
              {{ p.project_name }}
            </template>
            <template #value>
              <span class="rank-score">{{ p.total_score?.toFixed(1) }}分</span>
              <van-tag :type="gradeTagType(p.grade)" size="small">{{ p.grade }}</van-tag>
            </template>
          </van-cell>
        </van-cell-group>
      </div>

      <!-- 4. AI 洞察 -->
      <div v-if="result.ai_result" class="result-card">
        <div class="result-title">AI 洞察分析</div>

        <div v-if="result.ai_result.overall_verdict" class="insight-block verdict-block">
          <p class="result-text">{{ result.ai_result.overall_verdict }}</p>
        </div>

        <div v-if="result.ai_result.strengths_a?.length" class="insight-block">
          <div class="insight-label">{{ result.label_a || 'A方' }} 优势</div>
          <p v-for="s in result.ai_result.strengths_a" :key="s" class="result-text">• {{ s }}</p>
        </div>

        <div v-if="result.ai_result.strengths_b?.length" class="insight-block">
          <div class="insight-label">{{ result.label_b || 'B方' }} 优势</div>
          <p v-for="s in result.ai_result.strengths_b" :key="s" class="result-text">• {{ s }}</p>
        </div>

        <div v-if="result.ai_result.weaknesses_a?.length" class="insight-block">
          <div class="insight-label insight-warn">{{ result.label_a || 'A方' }} 薄弱环节</div>
          <p v-for="w in result.ai_result.weaknesses_a" :key="w" class="result-text">• {{ w }}</p>
        </div>

        <div v-if="result.ai_result.weaknesses_b?.length" class="insight-block">
          <div class="insight-label insight-warn">{{ result.label_b || 'B方' }} 薄弱环节</div>
          <p v-for="w in result.ai_result.weaknesses_b" :key="w" class="result-text">• {{ w }}</p>
        </div>

        <div v-if="result.ai_result.action_items?.length" class="insight-block">
          <div class="insight-label">行动建议</div>
          <div v-for="a in result.ai_result.action_items" :key="a.action" class="action-row">
            <div class="action-text">{{ a.action }}</div>
            <div class="action-meta">
              <van-tag plain size="small">{{ a.responsible || '-' }}</van-tag>
              <van-tag plain size="small" type="warning">{{ a.deadline || '-' }}</van-tag>
            </div>
          </div>
        </div>

        <div v-if="result.ai_result.final_conclusion" class="insight-block conclusion-block">
          <div class="insight-label">结论</div>
          <p class="result-text">{{ result.ai_result.final_conclusion }}</p>
        </div>
      </div>

      <!-- 5. 导出按钮 -->
      <div v-if="result.export_paths?.word || result.export_paths?.pdf" class="result-card export-card">
        <van-button plain type="primary" block icon="description" @click="handleDownload('word')"
          style="margin-bottom: 8px" v-if="result.export_paths?.word">
          下载 Word 报告
        </van-button>
        <van-button plain type="primary" block icon="down" @click="handleDownload('pdf')"
          v-if="result.export_paths?.pdf">
          下载 PDF 报告
        </van-button>
      </div>
    </div>
    </template>

    <van-tabbar v-model="activeTab" route>
      <van-tabbar-item icon="chart-trending-o" to="/dashboard">概览</van-tabbar-item>
      <van-tabbar-item icon="home-o" to="/tasks">任务</van-tabbar-item>
      <van-tabbar-item icon="todo-list-o" to="/reports">报告</van-tabbar-item>
      <van-tabbar-item icon="shield-o" to="/rectification">整改</van-tabbar-item>
      <van-tabbar-item icon="bar-chart-o" to="/analysis-mobile">分析</van-tabbar-item>
    </van-tabbar>

    <!-- 报告选择 Picker -->
    <van-popup v-model:show="showReportPicker" position="bottom" round>
      <van-picker :columns="pickerColumns" @confirm="onReportConfirm" @cancel="showReportPicker = false"
        title="选择报告" />
    </van-popup>

    <!-- 项目选择 Picker -->
    <van-popup v-model:show="showProjectPicker" position="bottom" round>
      <van-picker :columns="projectColumns" @confirm="onProjectConfirm" @cancel="showProjectPicker = false"
        title="选择项目" />
    </van-popup>

    <!-- 日期选择 -->
    <van-popup v-model:show="showStartPicker" position="bottom" round>
      <van-date-picker v-model="startDateArr" @confirm="onStartConfirm" @cancel="showStartPicker = false"
        title="开始日期" />
    </van-popup>
    <van-popup v-model:show="showEndPicker" position="bottom" round>
      <van-date-picker v-model="endDateArr" @confirm="onEndConfirm" @cancel="showEndPicker = false"
        title="结束日期" />
    </van-popup>

    <van-action-sheet v-model:show="showUser" title="个人信息">
      <div class="user-info">
        <van-cell title="用户名" :value="user.username" />
        <van-cell title="姓名" :value="user.real_name" />
        <van-cell title="角色" :value="getRoleText(user.role)" />
        <van-button block type="danger" @click="onLogout" style="margin-top: 20px">退出登录</van-button>
      </div>
    </van-action-sheet>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { showToast, showSuccessToast } from 'vant'
import { useAuthStore } from '../../stores/auth'
import { getProjectsWithReports, startAnalysis, getAnalysisProgress, getAnalysisResult, downloadAnalysisFile, getAnalysisHistory } from '../../api/analysis'
import { getReportList } from '../../api/report'

const authStore = useAuthStore()

const mode = ref('cross_project')
const activeTab = ref(4)
const showUser = ref(false)
const analyzing = ref(false)
const progressPct = ref(0)
const progressStep = ref('')
const result = ref(null)

const form = ref({
  report_a_id: null,
  report_b_id: null,
  project_a_id: null,
  time_range_start: '',
  time_range_end: ''
})

const allReports = ref([])
const projectsList = ref([])
const projectReports = ref([])

// Picker 状态
const showReportPicker = ref(false)
const pickerTarget = ref('a')
const showProjectPicker = ref(false)
const showStartPicker = ref(false)
const showEndPicker = ref(false)
const startDateArr = ref(['2026', '01', '01'])
const endDateArr = ref(['2026', '12', '31'])

const user = computed(() => authStore.user || {})

const pickerColumns = computed(() => {
  const list = mode.value === 'cross_time' ? projectReports.value : allReports.value
  return list.map(r => ({
    text: `${r.project_name || '未知'} (${(r.generated_at || '').slice(0, 10)}) ${r.total_score}分`,
    value: r.report_id
  }))
})

const projectColumns = computed(() => {
  return projectsList.value.map(p => ({
    text: `${p.project_name} (${p.report_count}份报告)`,
    value: p.project_id
  }))
})

const reportALabel = computed(() => {
  const id = form.value.report_a_id
  if (!id) return ''
  const r = allReports.value.find(x => x.report_id === id) || projectReports.value.find(x => x.report_id === id)
  return r ? `${r.project_name} (${(r.generated_at || '').slice(0, 10)})` : ''
})

const reportBLabel = computed(() => {
  const id = form.value.report_b_id
  if (!id) return ''
  const r = allReports.value.find(x => x.report_id === id) || projectReports.value.find(x => x.report_id === id)
  return r ? `${r.project_name} (${(r.generated_at || '').slice(0, 10)})` : ''
})

const selectedProjectLabel = computed(() => {
  const p = projectsList.value.find(x => x.project_id === form.value.project_a_id)
  return p ? p.project_name : ''
})

// 辅助函数
const winnerClass = (side) => {
  if (!result.value?.score_analysis) return ''
  const sa = result.value.score_analysis
  if (sa.total_score_a == null || sa.total_score_b == null) return ''
  if (side === 'a' && sa.total_score_a > sa.total_score_b) return 'score-winner'
  if (side === 'b' && sa.total_score_b > sa.total_score_a) return 'score-winner'
  return ''
}

const diffClass = (diff) => {
  if (diff == null) return ''
  if (diff > 0.2) return 'diff-positive'
  if (diff < -0.2) return 'diff-negative'
  return 'diff-neutral'
}

const winnerTagType = (w) => {
  if (w === 'A') return 'primary'
  if (w === 'B') return 'success'
  return 'default'
}

const gradeTagType = (grade) => {
  if (!grade) return 'default'
  if (grade.startsWith('A')) return 'success'
  if (grade.startsWith('B')) return 'warning'
  return 'danger'
}

const getScoreColor = (score) => {
  if (score == null) return ''
  if (score >= 90) return 'score-good'
  if (score >= 70) return 'score-warn'
  return 'score-bad'
}

const handleDownload = async (fileType) => {
  if (!result.value?.export_paths) return
  try {
    const analysisId = result.value.analysis_id
    const blob = await downloadAnalysisFile(analysisId, fileType)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const ext = fileType === 'pdf' ? 'pdf' : 'docx'
    a.download = `综合分析报告_${analysisId}.${ext}`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    showToast('下载失败')
  }
}

const openPicker = (target) => {
  pickerTarget.value = target
  showReportPicker.value = true
}

const onReportConfirm = ({ selectedOptions }) => {
  const selected = selectedOptions[0]
  if (pickerTarget.value === 'a') form.value.report_a_id = selected.value
  else form.value.report_b_id = selected.value
  showReportPicker.value = false
}

const onProjectConfirm = ({ selectedOptions }) => {
  const selected = selectedOptions[0]
  form.value.project_a_id = selected.value
  showProjectPicker.value = false
  loadProjectReports(selected.value)
}

const onStartConfirm = ({ selectedValues }) => {
  form.value.time_range_start = selectedValues.join('-')
  showStartPicker.value = false
}

const onEndConfirm = ({ selectedValues }) => {
  form.value.time_range_end = selectedValues.join('-')
  showEndPicker.value = false
}

const loadProjectReports = async (projectId) => {
  try {
    const res = await getReportList({ page: 1, page_size: 100 })
    const all = res.items || []
    const proj = projectsList.value.find(p => p.project_id === projectId)
    projectReports.value = all.filter(r => r.project_name === proj?.project_name)
    form.value.report_a_id = null
    form.value.report_b_id = null
  } catch (e) { /* ignore */ }
}

const fetchData = async () => {
  try {
    const [reportRes, projRes] = await Promise.all([
      getReportList({ page: 1, page_size: 100 }),
      getProjectsWithReports({})
    ])
    allReports.value = reportRes.items || []
    projectsList.value = projRes.projects || []
  } catch (e) {
    console.error('加载数据失败:', e)
  }
}

const onStartAnalysis = async () => {
  if (mode.value === 'cross_project' && (!form.value.report_a_id || !form.value.report_b_id)) {
    showToast('请选择两份报告')
    return
  }
  if (mode.value === 'cross_time' && (!form.value.report_a_id || !form.value.report_b_id)) {
    showToast('请选择两份报告')
    return
  }
  if (mode.value === 'all_projects' && (!form.value.time_range_start || !form.value.time_range_end)) {
    showToast('请选择日期范围')
    return
  }

  analyzing.value = true
  result.value = null
  progressPct.value = 0
  progressStep.value = '启动分析...'

  try {
    const payload = { mode: mode.value }
    if (mode.value === 'cross_project' || mode.value === 'cross_time') {
      payload.report_a_id = form.value.report_a_id
      payload.report_b_id = form.value.report_b_id
    }
    if (mode.value === 'cross_time') {
      payload.project_a_id = form.value.project_a_id
    }
    if (mode.value === 'all_projects') {
      payload.time_range_start = form.value.time_range_start
      payload.time_range_end = form.value.time_range_end
    }

    const startRes = await startAnalysis(payload)
    const analysisId = startRes.analysis_id

    // 轮询进度
    await new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const p = await getAnalysisProgress(analysisId)
          progressPct.value = Math.round((p.progress || 0) * 100)
          progressStep.value = p.current_step || '处理中...'
          if (p.status === 'completed') {
            resolve()
          } else if (p.status === 'failed') {
            reject(new Error(p.error || '分析失败'))
          } else {
            setTimeout(poll, 2000)
          }
        } catch (e) {
          reject(e)
        }
      }
      setTimeout(poll, 1000)
    })

    // 加载结果
    const res = await getAnalysisResult(analysisId)
    result.value = { ...res, analysis_id: analysisId }
    showSuccessToast('分析完成')
  } catch (e) {
    showToast(e.message || e.response?.data?.detail || '分析失败')
  } finally {
    analyzing.value = false
  }
}

// 历史记录
const historyList = ref([])
const historyLoading = ref(false)

const modeLabel = (m) => {
  const map = { cross_project: '跨项目对比', cross_time: '跨时段对比', all_projects: '全项目概览' }
  return map[m] || m
}

const loadHistory = async () => {
  historyLoading.value = true
  try {
    const res = await getAnalysisHistory({ page: 1, size: 50 })
    historyList.value = res.records || []
  } catch (e) {
    console.error('加载历史记录失败:', e)
  } finally {
    historyLoading.value = false
  }
}

const viewHistoryItem = async (h) => {
  if (h.status !== 'completed') {
    showToast('该分析未完成')
    return
  }
  try {
    const res = await getAnalysisResult(h.analysis_id)
    result.value = { ...res, analysis_id: h.analysis_id }
    mode.value = h.mode
    showSuccessToast('已加载历史分析结果')
  } catch (e) {
    showToast('加载分析结果失败')
  }
}

const getRoleText = (role) => {
  const map = { admin: '管理员', inspector: '检查员', site_supervisor: '阵地督导', field_supervisor: '驻场经理', project_staff: '项目人员' }
  return map[role] || role
}

const onLogout = () => { authStore.logout() }

watch(mode, (val) => {
  if (val === 'history') loadHistory()
})

onMounted(fetchData)
</script>

<style scoped>
.analysis-page {
  min-height: 100vh;
  background: #f5f7fa;
  padding-bottom: 60px;
}

.param-section { padding: 12px; }
.action-bar { padding: 0 16px 12px; }

.progress-section {
  padding: 16px;
  text-align: center;
}

.progress-text {
  font-size: 13px;
  color: #9ba3af;
  margin-top: 8px;
}

/* 结果 */
.result-section { padding: 0 12px 12px; }

.result-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.result-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1d26;
  margin-bottom: 10px;
}

.result-text {
  font-size: 14px;
  color: #475569;
  line-height: 1.6;
  margin: 4px 0;
}

/* 分数 VS 对比 */
.score-vs-row {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 16px;
  gap: 12px;
}

.score-vs-block {
  flex: 1;
  text-align: center;
  padding: 12px 8px;
  background: #F8FAFC;
  border-radius: 10px;
}

.score-vs-label {
  font-size: 12px;
  color: #9ba3af;
  margin-bottom: 4px;
}

.score-vs-num {
  font-size: 28px;
  font-weight: 700;
  color: #475569;
  font-family: "SF Mono", Consolas, monospace;
}

.score-vs-num.score-winner { color: #059669; }

.score-vs-sep {
  font-size: 16px;
  font-weight: 700;
  color: #dc2626;
}

/* 统计网格 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-top: 12px;
}

.stat-mini {
  text-align: center;
  padding: 8px 4px;
  background: #F8FAFC;
  border-radius: 8px;
}

.stat-mini-val {
  display: block;
  font-size: 16px;
  font-weight: 700;
  color: #1a1d26;
}

.stat-mini-label {
  display: block;
  font-size: 11px;
  color: #9ba3af;
  margin-top: 2px;
}

/* 模块对比表 */
.module-table {
  font-size: 12px;
}

.module-header {
  display: flex;
  align-items: center;
  padding: 8px 4px;
  border-bottom: 1px solid #E2E8F0;
  font-weight: 600;
  color: #64748b;
}

.module-row {
  display: flex;
  align-items: center;
  padding: 10px 4px;
  border-bottom: 1px solid #F1F5F9;
}

.module-row:last-child { border-bottom: none; }

.col-name { flex: 2; font-size: 13px; color: #1e293b; }
.col-score { flex: 1; text-align: center; font-weight: 600; font-family: "SF Mono", Consolas, monospace; }
.col-diff { flex: 1; text-align: center; font-weight: 600; font-family: "SF Mono", Consolas, monospace; }
.col-winner { flex: 0.8; text-align: center; }

.score-good { color: #059669; }
.score-warn { color: #d97706; }
.score-bad { color: #dc2626; }
.diff-positive { color: #059669; }
.diff-negative { color: #dc2626; }
.diff-neutral { color: #94a3b8; }

/* 排名 */
.rank-num {
  display: inline-block;
  width: 22px;
  height: 22px;
  line-height: 22px;
  text-align: center;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
  margin-right: 6px;
  background: #F1F5F9;
  color: #64748b;
}

.rank-num.rank-top {
  background: #2563eb;
  color: #fff;
}

.rank-score {
  font-weight: 700;
  font-family: "SF Mono", Consolas, monospace;
  margin-right: 6px;
}

/* AI 洞察 */
.insight-block { margin-bottom: 12px; }
.insight-block:last-child { margin-bottom: 0; }

.insight-label {
  font-size: 13px;
  font-weight: 600;
  color: #2563eb;
  margin-bottom: 4px;
}

.insight-label.insight-warn { color: #d97706; }

.verdict-block {
  background: #f0f9ff;
  border-radius: 8px;
  padding: 12px;
}

.conclusion-block {
  background: #f0fdf4;
  border-radius: 8px;
  padding: 12px;
}

.action-row {
  padding: 8px 0;
  border-bottom: 1px solid #F1F5F9;
}

.action-row:last-child { border-bottom: none; }

.action-text {
  font-size: 14px;
  color: #1e293b;
  margin-bottom: 4px;
}

.action-meta {
  display: flex;
  gap: 6px;
}

.export-card { padding: 12px 16px; }

/* 历史记录 */
.history-section { padding: 12px; }
.history-loading-center { display: flex; justify-content: center; padding: 40px 0; }
.history-card {
  background: #fff;
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  border: 1px solid #f0f0f0;
}
.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.history-time { font-size: 12px; color: #9ba3af; }
.history-summary {
  font-size: 13px;
  color: #475569;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.history-footer { margin-top: 6px; }

.user-info { padding: 16px; }
</style>
