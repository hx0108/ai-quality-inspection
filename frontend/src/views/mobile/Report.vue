<template>
  <div class="report-page">
    <van-nav-bar title="检查报告" left-arrow @click-left="onBack">
      <template #right>
        <van-icon v-if="reportData.total_score" name="down" size="18" @click="downloadReport" />
      </template>
    </van-nav-bar>

    <van-loading v-if="loading" class="loading-center" />

    <!-- 生成中状态 -->
    <div v-else-if="generating" class="generating-area">
      <van-loading size="24px" vertical>DeepSeek AI 正在分析报告...</van-loading>
      <van-progress :percentage="genPercentage" stroke-width="12" class="gen-progress" />
      <p class="gen-text">模块分析：{{ genProgress.modules_done }}/{{ genProgress.modules_total }}</p>
      <p class="gen-step">{{ genStepText }}</p>
      <p class="gen-tip">每个模块约5-10秒，请耐心等待</p>
    </div>

    <!-- 未生成状态 -->
    <div v-else-if="notFound" class="not-found-area">
      <van-empty description="报告尚未生成">
        <template #image>
          <van-icon name="description" size="80" color="#2563eb" />
        </template>
        <van-button type="primary" @click="startGenerate" :loading="genLoading">
          生成 AI 分析报告
        </van-button>
      </van-empty>
    </div>

    <!-- 报告内容 -->
    <div v-else class="report-content">
      <!-- 概况 -->
      <van-cell-group inset>
        <van-cell title="项目名称" :value="reportData.project_name" />
        <van-cell title="检查日期" :value="reportData.check_date" />
        <van-cell title="项目总分" title-class="total-title">
          <template #value>
            <span :class="getScoreClass(reportData.total_score)">
              {{ reportData.total_score?.toFixed(2) }} 分
            </span>
          </template>
        </van-cell>
      </van-cell-group>

      <!-- 模块得分 -->
      <van-cell-group inset title="各模块得分">
        <div v-for="module in reportData.modules" :key="module.module_name" class="module-item">
          <div class="module-header">
            <span class="module-name">{{ module.module_name }}</span>
            <span class="module-score">{{ module.module_pct_score?.toFixed(2) }}</span>
          </div>
          <van-progress
            :percentage="module.module_pct_score || 0"
            :color="getProgressColor(module.module_pct_score)"
            stroke-width="8"
            show-pivot="false"
          />
        </div>
      </van-cell-group>

      <!-- AI 模块分析 -->
      <van-cell-group v-if="moduleAnalyses.length > 0" inset title="AI 模块分析">
        <van-collapse v-model="activeAnalyses">
          <van-collapse-item
            v-for="analysis in moduleAnalyses"
            :key="analysis.module_name"
            :name="analysis.module_name"
          >
            <template #title>
              <div class="analysis-title">
                <span>{{ analysis.module_name }}</span>
                <span class="analysis-score">{{ analysis.module_pct_score }}分</span>
              </div>
            </template>
            <div class="analysis-content">
              <p class="analysis-eval">{{ analysis.overall_evaluation }}</p>
              <div v-if="analysis.main_issues && analysis.main_issues.length" class="analysis-section">
                <h4>主要问题</h4>
                <van-tag
                  v-for="(issue, idx) in analysis.main_issues"
                  :key="idx"
                  type="danger"
                  plain
                  class="issue-tag"
                >{{ issue }}</van-tag>
              </div>
              <div v-if="analysis.improvement_suggestions && analysis.improvement_suggestions.length" class="analysis-section">
                <h4>改进建议</h4>
                <p v-for="(sug, idx) in analysis.improvement_suggestions" :key="idx" class="suggestion-item">
                  {{ sug }}
                </p>
              </div>
            </div>
          </van-collapse-item>
        </van-collapse>
      </van-cell-group>

      <!-- AI 综合报告 -->
      <van-cell-group v-if="aiFullReport" inset title="综合分析报告">
        <div class="markdown-content" v-html="renderedReport"></div>
      </van-cell-group>

      <!-- 问题清单 -->
      <van-cell-group inset title="问题清单">
        <van-collapse v-model="activeIssues">
          <van-collapse-item
            v-for="(issues, severity) in reportData.issues"
            :key="severity"
            :name="severity"
          >
            <template #title>
              <van-badge :content="issues.length">
                <span>{{ severity }}问题</span>
              </van-badge>
            </template>
            <van-cell
              v-for="issue in issues"
              :key="issue.issue_id"
              :title="issue.item_name"
              :label="issue.description"
            />
            <van-empty v-if="issues.length === 0" description="暂无问题" />
          </van-collapse-item>
        </van-collapse>
      </van-cell-group>

      <!-- 下载按钮 -->
      <div class="download-area">
        <van-button type="primary" block @click="downloadReport('word')" style="margin-bottom: 8px">
          下载 Word 报告
        </van-button>
        <van-button plain type="primary" block @click="downloadReport('pdf')">
          下载 PDF 报告
        </van-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { showToast, showSuccessToast } from 'vant'
import { getReport, getReportStatus, generateReport as apiGenerateReport, downloadReportFile } from '../../api/report'
import { marked as renderMarkdownSafe } from '../../utils/markdown'
import { usePolling } from '../../composables/usePolling'

const router = useRouter()
const route = useRoute()
const taskId = route.params.taskId

const loading = ref(true)
const generating = ref(false)
const notFound = ref(false)
const genLoading = ref(false)
const genProgress = ref({ modules_done: 0, modules_total: 0 })
const genStep = ref('')

const reportData = ref({ modules: [], issues: {} })
const moduleAnalyses = ref([])
const aiFullReport = ref('')
const activeAnalyses = ref([])
const activeIssues = ref(['严重', '一般', '轻微'])

// 统一轮询管理：自动在卸载/路由离开时清理（修复手势返回泄漏）
// 用箭头包裹延迟求值（pollReportStatus 定义在下方）
const { start: startPolling, stop: stopPolling } = usePolling(() => pollReportStatus(), { interval: 1500, immediate: false })

const genPercentage = computed(() => {
  const total = genProgress.value.modules_total || 1
  return Math.min(100, Math.round((genProgress.value.modules_done / total) * 100))
})

const genStepText = computed(() => {
  const step = genStep.value
  if (step.startsWith('analyzing:')) {
    const moduleName = step.replace('analyzing:', '')
    return `正在分析模块：${moduleName}`
  }
  if (step === 'generating_report') return '正在生成综合报告...'
  if (step === 'collecting_data') return '正在收集数据...'
  return step || '准备中...'
})

const renderedReport = computed(() => {
  if (!aiFullReport.value) return ''
  // 使用安全渲染器（含XSS过滤）
  return renderMarkdownSafe(aiFullReport.value)
})

const fetchReport = async () => {
  try {
    const res = await getReport(taskId)
    const content = res.content || {}
    reportData.value = content
    moduleAnalyses.value = content.module_analyses || []
    aiFullReport.value = content.ai_full_report || ''
    activeAnalyses.value = moduleAnalyses.value.map(m => m.module_name)
  } catch (e) {
    if (e.response?.status === 404) {
      // 报告不存在，立即开始轮询（不再串行多等一次 getReportStatus）
      generating.value = true
      notFound.value = false
      startPolling()  // 1.5s 轮询，快速响应
    } else {
      showToast('获取报告失败')
    }
  } finally {
    loading.value = false
  }
}

const startGenerate = async () => {
  genLoading.value = true
  try {
    await apiGenerateReport(taskId)
    generating.value = true
    notFound.value = false
    showSuccessToast('报告生成已启动')
    startPolling()
  } catch (e) {
    showToast(e.response?.data?.detail || '生成报告失败')
  } finally {
    genLoading.value = false
  }
}

const pollReportStatus = async () => {
  try {
    const status = await getReportStatus(taskId)
    genProgress.value = status
    genStep.value = status.current_step || ''
    if (status.status === 'completed') {
      stopPolling()
      generating.value = false
      await fetchReport()
    } else if (status.status === 'failed') {
      stopPolling()
      generating.value = false
      showToast('报告生成失败: ' + (status.error || '未知错误'))
      notFound.value = true
    }
  } catch (e) {
    console.error('轮询报告状态失败:', e)
  }
}

const downloadReport = async (format) => {
  const ext = format || 'word'
  try {
    await downloadReportFile(taskId, ext)
    showSuccessToast('下载已开始')
  } catch (e) {
    showToast(e.message || '下载失败')
  }
}

const onBack = () => {
  stopPolling()
  router.back()
}

const getScoreClass = (score) => {
  if (!score) return ''
  if (score >= 90) return 'score-excellent'
  if (score >= 80) return 'score-good'
  if (score >= 60) return 'score-normal'
  return 'score-poor'
}

const getProgressColor = (score) => {
  if (!score) return '#e5e5e5'
  if (score >= 90) return '#059669'
  if (score >= 80) return '#2563eb'
  if (score >= 60) return '#d97706'
  return '#dc2626'
}

onMounted(() => {
  fetchReport()
})
</script>

<style scoped>
.report-page {
  min-height: 100vh;
  background: #f5f7fa;
  padding-bottom: 80px;
}

.loading-center {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 50vh;
}

.report-content {
  padding: 12px;
}

.report-content :deep(.van-cell-group) {
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  margin-bottom: 12px;
}

.total-title {
  font-size: 16px;
  font-weight: bold;
}

.score-excellent {
  color: #059669;
  font-weight: bold;
  font-size: 20px;
}

.score-good {
  color: #2563eb;
  font-weight: bold;
  font-size: 20px;
}

.score-normal {
  color: #d97706;
  font-weight: bold;
  font-size: 20px;
}

.score-poor {
  color: #dc2626;
  font-weight: bold;
  font-size: 20px;
}

.module-item {
  padding: 14px 16px;
  border-bottom: 1px solid #f0f0f0;
}

.module-item:last-child {
  border-bottom: none;
}

.module-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}

.module-name {
  font-size: 14px;
  color: #1a1d26;
  font-weight: 500;
}

.module-score {
  font-size: 15px;
  font-weight: 600;
  color: #1a1d26;
}

/* 生成中 */
.generating-area {
  text-align: center;
  margin-top: 48px;
  padding: 20px;
}

.gen-progress {
  margin: 20px;
}

.gen-text {
  color: #1a1d26;
  font-size: 16px;
  font-weight: 500;
  margin-top: 12px;
}

.gen-step {
  color: #2563eb;
  font-size: 14px;
  margin-top: 4px;
}

.gen-tip {
  color: #9ba3af;
  font-size: 13px;
  margin-top: 8px;
}

/* 未生成 */
.not-found-area {
  margin-top: 40px;
}

/* AI 分析 */
.analysis-title {
  display: flex;
  justify-content: space-between;
  width: 100%;
  align-items: center;
}

.analysis-score {
  color: #2563eb;
  font-size: 13px;
  font-weight: 600;
}

.analysis-content {
  padding: 8px 0;
}

.analysis-eval {
  font-size: 14px;
  color: #333;
  line-height: 1.7;
  margin-bottom: 12px;
  background: #f7f8fa;
  padding: 10px 12px;
  border-radius: 8px;
  border-left: 3px solid #2563eb;
}

.analysis-section {
  margin-top: 8px;
}

.analysis-section h4 {
  font-size: 13px;
  color: #9ba3af;
  margin: 8px 0 4px;
}

.issue-tag {
  margin: 2px 4px;
  display: inline-block;
}

.suggestion-item {
  font-size: 13px;
  color: #333;
  padding: 4px 0;
  line-height: 1.5;
}

/* Markdown 渲染 */
.markdown-content {
  padding: 12px 16px;
  font-size: 14px;
  line-height: 1.8;
  color: #333;
}

.markdown-content :deep(h2) {
  font-size: 16px;
  font-weight: bold;
  margin: 16px 0 8px;
  color: #1a1d26;
}

.markdown-content :deep(h3) {
  font-size: 15px;
  font-weight: bold;
  margin: 12px 0 6px;
  color: #1a1d26;
}

.markdown-content :deep(h4) {
  font-size: 14px;
  font-weight: bold;
  margin: 8px 0 4px;
  color: #1a1d26;
}

.markdown-content :deep(li) {
  margin-left: 16px;
  list-style: disc;
  margin-bottom: 4px;
}

.markdown-content :deep(br) {
  display: block;
  content: '';
  margin-top: 0;
}

/* 下载 */
.download-area {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 12px 16px;
  background: #fff;
  box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.06);
}

.download-area .van-button {
  border-radius: 8px;
  font-weight: 500;
}
</style>
