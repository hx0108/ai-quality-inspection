<template>
  <div class="pc-page">
    <div class="report-content" v-loading="loading">
          <div v-if="report" class="report-container">
            <!-- 报告头部 -->
            <el-card shadow="never" class="report-header">
              <h2>{{ report.project_name }}</h2>
              <div class="report-meta">
                <span>检查日期: {{ report.inspection_date }}</span>
                <span>报告编号: {{ report.task_code }}</span>
              </div>
            </el-card>
            
            <el-row :gutter="20">
              <!-- 总分 -->
              <el-col :span="8">
                <el-card shadow="never" class="score-card">
                  <div class="score-title">综合得分</div>
                  <div class="score-value" :style="{ color: getScoreColor(report.total_score) }">
                    {{ report.total_score?.toFixed(1) || 0 }}
                  </div>
                  <el-progress 
                    :percentage="report.total_score || 0" 
                    :color="getScoreColor(report.total_score)"
                    :show-text="false"
                  />
                </el-card>
              </el-col>
              
              <!-- 问题统计 -->
              <el-col :span="16">
                <el-card shadow="never" class="issues-card">
                  <div class="issues-title">问题统计</div>
                  <el-row :gutter="20">
                    <el-col :span="8">
                      <div class="issue-stat minor">
                        <div class="issue-count">{{ report.minor_issues || 0 }}</div>
                        <div class="issue-label">轻微问题</div>
                      </div>
                    </el-col>
                    <el-col :span="8">
                      <div class="issue-stat moderate">
                        <div class="issue-count">{{ report.moderate_issues || 0 }}</div>
                        <div class="issue-label">一般问题</div>
                      </div>
                    </el-col>
                    <el-col :span="8">
                      <div class="issue-stat major">
                        <div class="issue-count">{{ report.major_issues || 0 }}</div>
                        <div class="issue-label">严重问题</div>
                      </div>
                    </el-col>
                  </el-row>
                </el-card>
              </el-col>
            </el-row>
            
            <!-- 模块得分 -->
            <el-card shadow="never" class="module-scores">
              <template #header>
                <span>各模块得分</span>
              </template>
              <el-table :data="report.module_scores" style="width: 100%">
                <el-table-column prop="module_name" label="模块名称" />
                <el-table-column prop="score" label="得分" width="150">
                  <template #default="{ row }">
                    <span :style="{ color: getScoreColor(row.score) }">{{ row.score?.toFixed(1) }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="得分率" width="200">
                  <template #default="{ row }">
                    <el-progress 
                      :percentage="row.score || 0" 
                      :color="getScoreColor(row.score)"
                    />
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
            
            <!-- AI分析 -->
            <el-card shadow="never" class="ai-analysis">
              <template #header>
                <span><el-icon><ChatDotRound /></el-icon> AI分析建议</span>
              </template>
              <div class="analysis-content" v-html="formatAnalysis(report.ai_analysis)"></div>
            </el-card>
            
            <!-- 操作按钮 -->
            <div class="actions">
              <el-button type="primary" @click="downloadReport('json')">
                <el-icon><Download /></el-icon> 导出JSON
              </el-button>
              <el-button @click="downloadReport('markdown')">
                <el-icon><Download /></el-icon> 导出Markdown
              </el-button>
            </div>
          </div>
          
          <el-empty v-else description="暂无报告数据" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../../stores/auth'
import { getReport, generateReport, downloadReport as downloadReportApi } from '../../api/report'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const activeMenu = computed(() => router.currentRoute.value.path)
const taskId = Number(route.params.taskId)
const loading = ref(true)
const report = ref<any>(null)

const getScoreColor = (score: number) => {
  if (score >= 90) return '#67c23a'
  if (score >= 80) return '#409eff'
  if (score >= 60) return '#e6a23c'
  return '#f56c6c'
}

const formatAnalysis = (text: string) => {
  if (!text) return ''
  return text.replace(/\n/g, '<br>')
}

const handleCommand = (command: string) => {
  if (command === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}

const loadReport = async () => {
  loading.value = true
  try {
    report.value = await getReport(taskId)
  } catch (error: any) {
    if (error.response?.status === 404) {
      try {
        ElMessage.info('正在生成报告...')
        report.value = await generateReport(taskId)
      } catch (e) {
        ElMessage.error('生成报告失败')
      }
    }
  } finally {
    loading.value = false
  }
}

const downloadReport = async (format: string) => {
  try {
    const blob = await downloadReportApi(taskId, format)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${taskId}.${format}`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

onMounted(() => {
  loadReport()
})
</script>

<style scoped>
.sidebar {
  background: #304156;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #263445;
}

.logo h1 {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
}

.sidebar-menu {
  border-right: none;
  background: transparent;
}

.header {
  background: #fff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.user-name {
  font-size: 14px;
  color: #333;
}

.main-content {
  background: #f5f5f5;
  padding: 20px;
}

.report-container {
  max-width: 1200px;
  margin: 0 auto;
}

.report-header {
  text-align: center;
  margin-bottom: 20px;
}

.report-header h2 {
  font-size: 24px;
  color: #333;
  margin-bottom: 8px;
}

.report-meta {
  display: flex;
  justify-content: center;
  gap: 24px;
  font-size: 14px;
  color: #999;
}

.score-card {
  text-align: center;
  padding: 20px;
}

.score-title {
  font-size: 16px;
  color: #666;
  margin-bottom: 12px;
}

.score-value {
  font-size: 48px;
  font-weight: 600;
  margin-bottom: 12px;
}

.issues-card {
  padding: 20px;
}

.issues-title {
  font-size: 16px;
  color: #666;
  margin-bottom: 20px;
}

.issue-stat {
  text-align: center;
  padding: 16px;
  border-radius: 8px;
}

.issue-stat.minor {
  background: #ecf5ff;
}

.issue-stat.moderate {
  background: #fdf6ec;
}

.issue-stat.major {
  background: #fef0f0;
}

.issue-count {
  font-size: 32px;
  font-weight: 600;
}

.issue-stat.minor .issue-count {
  color: #409eff;
}

.issue-stat.moderate .issue-count {
  color: #e6a23c;
}

.issue-stat.major .issue-count {
  color: #f56c6c;
}

.issue-label {
  font-size: 14px;
  color: #999;
  margin-top: 8px;
}

.module-scores {
  margin-top: 20px;
}

.ai-analysis {
  margin-top: 20px;
}

.analysis-content {
  font-size: 14px;
  line-height: 1.8;
  color: #666;
}

.actions {
  margin-top: 20px;
  display: flex;
  gap: 12px;
}
</style>
