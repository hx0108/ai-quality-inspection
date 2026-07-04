<template>
  <div class="task-detail-page">
    <van-nav-bar title="任务详情" left-arrow @click-left="onBack" />

    <!-- 顶部信息卡 -->
    <div class="info-card">
      <div class="info-card-bg"></div>
      <div class="info-card-body">
        <div class="project-name">{{ task.project_name || '加载中...' }}</div>
        <div class="info-row">
          <div class="info-item">
            <div class="info-label">检查日期</div>
            <div class="info-value">{{ task.check_date || '-' }}</div>
          </div>
          <div class="info-item">
            <div class="info-label">任务状态</div>
            <div class="info-value">
              <van-tag :type="getStatusType(task.status)" size="medium">
                {{ getStatusText(task.status) }}
              </van-tag>
            </div>
          </div>
          <div class="info-item">
            <div class="info-label">项目总分</div>
            <div class="info-value score-value">{{ task.total_score ? `${task.total_score}` : '待评分' }}</div>
          </div>
        </div>
        <!-- 管理员执行按钮 -->
        <div v-if="isAdmin && task.status !== 'completed'" class="pipeline-action">
          <van-button type="primary" size="small" round @click="onRunPipeline" :loading="pipelineLoading">
            一键执行
          </van-button>
        </div>
      </div>
    </div>

    <!-- Pipeline 进度弹窗 -->
    <van-dialog
      v-model:show="showPipelineDialog"
      title="执行进度"
      :close-on-click-overlay="false"
      show-cancel-button
      cancel-button-text="关闭"
      @cancel="showPipelineDialog = false"
    >
      <div class="pipeline-dialog-content">
        <div class="pipeline-step" :class="getPipelineStepClass(1)">
          <div class="step-indicator">
            <van-icon v-if="pipelineStep > 1" name="passed" size="20" />
            <span v-else>{{ pipelineStep === 1 && pipelineRunning ? '...' : '1' }}</span>
          </div>
          <div class="step-info">
            <div class="step-name">AI评分</div>
            <div class="step-desc">{{ pipelineStep > 1 ? '已完成' : pipelineStep === 1 && pipelineRunning ? '执行中...' : '等待执行' }}</div>
          </div>
          <div v-if="pipelineStep > 1" class="step-score" :class="getScoreClass(task.total_score)">
            {{ task.total_score || '-' }}分
          </div>
        </div>
        <div class="pipeline-connector" :class="{ active: pipelineStep > 1 }"></div>
        <div class="pipeline-step" :class="getPipelineStepClass(2)">
          <div class="step-indicator">
            <van-icon v-if="pipelineStep > 2" name="passed" size="20" />
            <span v-else>{{ pipelineStep === 2 && pipelineRunning ? '...' : '2' }}</span>
          </div>
          <div class="step-info">
            <div class="step-name">生成报告</div>
            <div class="step-desc">{{ pipelineStep > 2 ? '已完成' : pipelineStep === 2 && pipelineRunning ? '执行中...' : '等待执行' }}</div>
          </div>
        </div>
        <div class="pipeline-connector" :class="{ active: pipelineStep > 2 }"></div>
        <div class="pipeline-step" :class="getPipelineStepClass(3)">
          <div class="step-indicator">
            <van-icon v-if="pipelineStep > 3" name="passed" size="20" />
            <span v-else>{{ pipelineStep === 3 && pipelineRunning ? '...' : '3' }}</span>
          </div>
          <div class="step-info">
            <div class="step-name">整改追踪</div>
            <div class="step-desc">{{ pipelineStep > 3 ? '已完成' : pipelineStep === 3 && pipelineRunning ? '执行中...' : '等待执行' }}</div>
          </div>
        </div>
        <div v-if="pipelineError" class="pipeline-error">
          <van-icon name="warning-o" size="16" /> {{ pipelineError }}
        </div>
      </div>
    </van-dialog>

    <!-- 模块列表 -->
    <div class="section-title">模块检查情况</div>
    <div class="module-list">
      <div
        v-for="module in task.modules"
        :key="module.module_name"
        class="module-card"
        :class="`module-${getModuleCardClass(module)}`"
        @click="onModuleClick(module)"
      >
        <div class="module-card-body">
          <div class="module-left">
            <div class="module-name">{{ module.module_name }}</div>
            <div class="module-weight">权重 {{ (module.weight * 100).toFixed(0) }}%</div>
          </div>
          <div class="module-right">
            <van-tag v-if="!module.assigned && !isAdmin" type="default" size="medium">未分配</van-tag>
            <template v-else-if="!module.assigned && isAdmin && module.status !== 'completed'">
              <van-tag type="default" size="medium" style="margin-right:6px">未分配</van-tag>
              <van-button size="mini" type="primary" plain round @click.stop="goInspect(module)">开始检查</van-button>
            </template>
            <van-button v-else-if="module.status === 'not_started'" size="mini" type="primary" plain round @click.stop="goInspect(module)">开始检查</van-button>
            <van-button v-else-if="module.status === 'in_progress'" size="mini" type="warning" plain round @click.stop="goInspect(module)">继续检查</van-button>
            <template v-else>
              <span v-if="module.pct_score !== null && module.pct_score !== undefined" class="module-score" :class="getScoreClass(module.pct_score)">{{ module.pct_score }}分</span>
              <van-tag type="success" size="medium">已完成</van-tag>
            </template>
            <van-icon name="arrow" color="#9ba3af" />
          </div>
        </div>
      </div>
    </div>

    <div v-if="task.modules.length === 0" class="empty-modules">暂无模块数据</div>

    <!-- 模块详情弹窗 -->
    <van-popup v-model:show="showModulePopup" position="bottom" round style="height: auto; max-height: 60%">
      <div class="module-detail" v-if="currentModule">
        <div class="popup-header">
          <div class="popup-title">{{ currentModule.module_name }}</div>
          <van-tag :type="getModuleStatusType(currentModule)" size="medium">
            {{ getModuleStatusText(currentModule) }}
          </van-tag>
        </div>
        <div class="popup-info">
          <span class="popup-info-item">权重 {{ (currentModule.weight * 100).toFixed(0) }}%</span>
          <span class="popup-info-divider">|</span>
          <span class="popup-info-item">检查员 {{ currentModule.inspector_name || (isAdmin ? '未分配' : '我') }}</span>
        </div>

        <!-- 评分信息区域（已完成模块显示） -->
        <div v-if="currentModule.status === 'completed'" class="popup-score-section">
          <template v-if="currentModule.scoring_status === 'completed' && currentModule.pct_score !== null && currentModule.pct_score !== undefined">
            <div class="popup-score-main">
              <span class="popup-score-label">AI评分</span>
              <span class="popup-score-value" :class="getScoreClass(currentModule.pct_score)">{{ currentModule.pct_score.toFixed(2) }}</span>
              <span class="popup-score-unit">分</span>
            </div>
            <van-button type="primary" block round size="small" @click="goScoringDetail" style="margin-top: 10px;">
              查看评分详情 / 修改分数
            </van-button>
          </template>
          <template v-else-if="currentModule.scoring_status === 'scoring'">
            <div class="popup-score-main">
              <van-loading size="18" color="#2563eb" style="margin-right: 8px;" />
              <span class="popup-score-label">AI 评分中...</span>
            </div>
          </template>
          <template v-else>
            <div class="popup-score-main">
              <span class="popup-score-label" style="color: #9ba3af;">AI 评分待启动</span>
            </div>
          </template>
        </div>

        <!-- 操作按钮 -->
        <div class="popup-actions">
          <van-button
            v-if="isAdmin && canAssign"
            size="small"
            :type="currentModule.assigned ? 'warning' : 'default'"
            round
            @click="showAssignSection = true; showInspectorPicker = true"
          >
            {{ currentModule.assigned ? '重新分配' : '分配检查员' }}
          </van-button>
          <van-button
            v-if="(currentModule.assigned || isAdmin) && currentModule.status !== 'completed'"
            size="small"
            type="primary"
            round
            @click="startInspection"
            :loading="startingInspection"
          >
            {{ currentModule.status === 'in_progress' ? '继续检查' : '开始检查' }}
          </van-button>
          <van-button
            v-if="(currentModule.assigned || isAdmin) && currentModule.status === 'completed'"
            size="small"
            type="success"
            round
            @click="startInspection"
          >
            查看
          </van-button>
          <van-button
            v-if="!isAdmin && !currentModule.assigned"
            size="small"
            type="default"
            round
            disabled
          >
            等待管理员分配
          </van-button>
        </div>

        <!-- 分配检查员选择器（内嵌） -->
        <van-cell-group v-if="isAdmin && showAssignSection" inset style="margin-top: 8px">
          <van-field
            v-model="selectedInspectorName"
            is-link
            readonly
            label="选择检查员"
            placeholder="点击选择"
            @click="showInspectorPicker = true"
          />
          <div style="padding: 8px 16px">
            <van-button type="primary" block size="small" @click="doAssign" :loading="assigning" :disabled="!selectedInspectorId">
              确认分配
            </van-button>
          </div>
        </van-cell-group>
      </div>
    </van-popup>

    <!-- 检查员选择器 -->
    <van-popup v-model:show="showInspectorPicker" position="bottom" round>
      <van-picker
        :columns="inspectorColumns"
        @confirm="onInspectorConfirm"
        @cancel="showInspectorPicker = false"
      />
    </van-popup>

    <!-- 底部操作栏（有评分结果或全部完成时显示） -->
    <div v-if="hasAnyScore || allCompleted" class="completed-actions">
      <div class="bottom-action-bar">
        <van-button type="primary" plain round block @click="router.push(`/scoring/${task.task_id}`)">查看评分</van-button>
        <van-button v-if="task.status === 'completed'" type="success" round block @click="router.push(`/report/${task.task_id}`)">查看报告</van-button>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { showToast, showSuccessToast, showConfirmDialog, closeToast } from 'vant'
import { getTaskDetail, assignModule, getInspectors } from '../../api/tasks'
import { createRecord } from '../../api/inspection'
import { getScoringStatus, getModuleScoringStatus } from '../../api/scoring'
import { runFullPipeline, getPipelineStatus } from '../../api/orchestrator'
import { useAuthStore } from '../../stores/auth'
import { usePolling } from '../../composables/usePolling'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const task = ref({ modules: [] })
const showModulePopup = ref(false)
const currentModule = ref(null)
const showInspectorPicker = ref(false)
const showAssignSection = ref(false)
const inspectors = ref([])
const selectedInspectorId = ref(null)
const selectedInspectorName = ref('')
const assigning = ref(false)
const startingInspection = ref(false)
const scoringLoading = ref(false)
const scoringStatus = ref(null)
const scoringProgress = ref('')
// 统一轮询管理：自动在卸载/路由离开时清理（修复手势返回泄漏）
// 回调内含停止条件，scoringStatus 非评分中时停止
const { start: _startScoringPolling, stop: stopScoringPolling } = usePolling(
  () => checkScoringStatus().then(() => {
    if (scoringStatus.value !== 'scoring') stopScoringPolling()
  }),
  { interval: 5000, immediate: true }
)
const pipelineLoading = ref(false)
const showPipelineDialog = ref(false)
const pipelineStep = ref(0)
const pipelineRunning = ref(false)
const pipelineError = ref('')

const user = computed(() => authStore.user)
const isAdmin = computed(() => user.value.role === 'admin' || user.value.role === 'field_supervisor')

const canAssign = computed(() => {
  if (!isAdmin.value || !currentModule.value) return false
  // 未分配 或 已分配但未完成 → 都允许分配/重新分配
  return !currentModule.value.assigned || currentModule.value.status !== 'completed'
})

const allCompleted = computed(() => {
  return task.value.modules.length > 0 && task.value.modules.every(m => m.status === 'completed')
})

const hasAnyScore = computed(() => {
  return task.value.modules.some(m => m.scoring_status === 'completed' && m.pct_score !== null && m.pct_score !== undefined)
})

const inspectorColumns = computed(() => {
  return inspectors.value.map(i => ({ text: `${i.real_name} (${i.role === 'site_supervisor' ? '阵地督导' : i.role === 'field_supervisor' ? '驻场经理' : '检查员'})`, value: i.id }))
})

const fetchTask = async () => {
  const taskId = route.params.taskId
  try {
    const res = await getTaskDetail(taskId)
    task.value = res
    // 只要有已完成的模块，就加载评分数据并合并到模块中
    const hasCompleted = task.value.modules?.some(m => m.status === 'completed')
    if (hasCompleted || allCompleted.value) {
      await checkScoringStatus()
      if (scoringStatus.value === 'scoring') {
        startScoringPolling()
      }
      await loadModuleScores()
    }
  } catch (e) {
    showToast('获取任务失败')
  }
}

// 加载各模块评分数据
const loadModuleScores = async () => {
  try {
    const res = await getModuleScoringStatus(task.value.task_id)
    for (const scoreModule of res.modules || []) {
      const target = task.value.modules.find(m => m.module_name === scoreModule.module_name)
      if (target) {
        target.pct_score = scoreModule.pct_score
        target.scoring_status = scoreModule.scoring_status
      }
    }
    // 同步总分
    if (res.current_total_score != null) {
      task.value.total_score = res.current_total_score
    }
  } catch (e) {
    console.error('获取评分数据失败', e)
  }
}

const fetchInspectors = async () => {
  try {
    const res = await getInspectors()
    inspectors.value = res.items || []
  } catch (e) {
    console.error('获取检查员失败', e)
  }
}

const onModuleClick = (module) => {
  currentModule.value = module
  selectedInspectorId.value = module.inspector_id || null
  selectedInspectorName.value = module.inspector_name || ''
  showAssignSection.value = false

  // 已分配且未完成 → 直接开始检查
  if (module.assigned && module.status !== 'completed' && !isAdmin.value) {
    startInspection()
    return
  }

  showModulePopup.value = true
}

const goInspect = (module) => {
  currentModule.value = module
  startInspection()
}

const onInspectorConfirm = ({ selectedOptions }) => {
  const selected = selectedOptions[0]
  selectedInspectorId.value = selected.value
  selectedInspectorName.value = selected.text
  showInspectorPicker.value = false
  showAssignSection.value = true
}

const doAssign = async () => {
  if (!selectedInspectorId.value) {
    showToast('请选择检查员')
    return
  }

  assigning.value = true
  try {
    const res = await assignModule(task.value.task_id, {
      module_name: currentModule.value.module_name,
      inspector_id: selectedInspectorId.value
    })
    showSuccessToast(res.message || '分配成功')
    currentModule.value.assigned = true
    currentModule.value.inspector_id = selectedInspectorId.value
    currentModule.value.inspector_name = selectedInspectorName.value
    showAssignSection.value = false
    await fetchTask()
  } catch (e) {
    showToast(e.response?.data?.detail || '分配失败')
  } finally {
    assigning.value = false
  }
}

const startInspection = async () => {
  startingInspection.value = true
  try {
    const res = await createRecord({
      task_id: task.value.task_id,
      module_name: currentModule.value.module_name
    })
    showModulePopup.value = false

    // 如果已有检查数据（继续检查），直接跳转列表模式
    if (res.item_count > 0) {
      router.push(`/inspection/${res.record_id}`)
      return
    }

    // 首次检查：选择检查模式
    try {
      await showConfirmDialog({
        title: '选择检查模式',
        message: '巡检模式：逐项卡片引导，适合现场检查\n列表模式：查看所有检查项，适合复查',
        confirmButtonText: '巡检模式',
        cancelButtonText: '列表模式',
      })
      // 确认 → 巡检模式
      await new Promise(r => setTimeout(r, 100))
      router.push(`/inspection-card/${res.record_id}`)
    } catch {
      // 取消 → 列表模式
      await new Promise(r => setTimeout(r, 100))
      router.push(`/inspection/${res.record_id}`)
    }
  } catch (e) {
    showToast(e.response?.data?.detail || '创建记录失败')
  } finally {
    startingInspection.value = false
  }
}

const startScoring = async () => {
  if (scoringStatus.value === 'not_started') {
    // 手动启动评分
    scoringLoading.value = true
    try {
      const { startScoring: apiStartScoring } = await import('../../api/scoring')
      await apiStartScoring(task.value.task_id)
      scoringStatus.value = 'scoring'
      scoringProgress.value = '0/' + task.value.modules.length
      startScoringPolling()
    } catch (e) {
      showToast(e.response?.data?.detail || '启动评分失败')
    } finally {
      scoringLoading.value = false
    }
  } else {
    // 评分已启动或已完成，跳转查看
    router.push(`/scoring/${task.value.task_id}`)
  }
}

const viewReport = () => {
  router.push(`/report/${task.value.task_id}`)
}

const goScoringDetail = () => {
  showModulePopup.value = false
  router.push(`/scoring/${task.value.task_id}`)
}

// 检查评分状态
const checkScoringStatus = async () => {
  try {
    const res = await getScoringStatus(task.value.task_id)
    if (res.is_complete) {
      scoringStatus.value = 'completed'
    } else if (res.scored_modules > 0 || res.total_modules > 0) {
      scoringStatus.value = 'scoring'
      scoringProgress.value = `${res.scored_modules}/${res.total_modules}`
    } else {
      scoringStatus.value = 'not_started'
    }
  } catch (e) {
    scoringStatus.value = 'not_started'
  }
}

// 开始评分状态轮询
const startScoringPolling = () => {
  _startScoringPolling()
}

const onBack = () => {
  router.back()
}

const getStatusType = (status) => {
  const map = { pending: 'default', in_progress: 'warning', completed: 'success' }
  return map[status] || 'default'
}

const getStatusText = (status) => {
  const map = { pending: '待开始', in_progress: '进行中', completed: '已完成' }
  return map[status] || status
}

const getModuleStatusType = (module) => {
  if (!module.assigned) return 'default'
  if (module.status === 'not_started') return 'warning'
  if (module.status === 'in_progress') return 'primary'
  return 'success'
}

const getModuleStatusText = (module) => {
  if (!module.assigned) return '未分配'
  if (module.status === 'not_started') return '开始检查'
  if (module.status === 'in_progress') return '继续检查'
  return '已完成'
}

const getModuleCardClass = (module) => {
  if (!module.assigned) return 'pending'
  return module.status || 'pending'
}

const getScoreClass = (score) => {
  if (score >= 90) return 'score-excellent'
  if (score >= 75) return 'score-good'
  if (score >= 60) return 'score-normal'
  return 'score-poor'
}

// 一键执行 Pipeline
const onRunPipeline = async () => {
  pipelineLoading.value = true
  pipelineError.value = ''
  pipelineStep.value = 0
  pipelineRunning.value = true
  showPipelineDialog.value = true
  try {
    pipelineStep.value = 1
    const res = await runFullPipeline(task.value.task_id)
    pipelineRunning.value = false
    if (res.success) {
      pipelineStep.value = 3
      pipelineError.value = ''
      await fetchTask()
      showSuccessToast('执行完成')
    } else {
      pipelineError.value = res.error_detail || res.error || '执行失败'
      if (res.steps_completed?.includes('scoring')) pipelineStep.value = 2
    }
  } catch (e) {
    pipelineRunning.value = false
    pipelineError.value = e.response?.data?.detail || '执行异常'
  } finally {
    pipelineLoading.value = false
  }
}

// 获取 pipeline 步骤样式
const getPipelineStepClass = (step) => {
  if (pipelineStep.value > step) return 'step-done'
  if (pipelineStep.value === step) return pipelineRunning.value ? 'step-running' : 'step-current'
  return 'step-waiting'
}

onMounted(() => {
  fetchTask()
  if (isAdmin.value) {
    fetchInspectors()
  }
})

onUnmounted(() => {
  // 定时器清理已由 usePolling 自动处理；这里只关弹窗
  // 使用 Vant API 正确关闭弹窗
  closeToast()
})
</script>

<style scoped>
.task-detail-page {
  min-height: 100vh;
  background: #f5f7fa;
  padding-bottom: 80px;
}

/* 顶部信息卡 */
.info-card {
  position: relative;
  margin: 12px;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

.info-card-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
}

.info-card-body {
  position: relative;
  padding: 20px;
  color: #fff;
}

.project-name {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
  line-height: 1.4;
}

.info-row {
  display: flex;
  gap: 16px;
}

.info-item {
  flex: 1;
}

.info-label {
  font-size: 11px;
  opacity: 0.6;
  margin-bottom: 4px;
}

.info-value {
  font-size: 13px;
  font-weight: 500;
}

.score-value {
  font-size: 20px;
  font-weight: 700;
  color: #ffffff;
}

/* 模块列表 */
.section-title {
  font-size: 14px;
  color: #666;
  padding: 16px 16px 8px;
  font-weight: 500;
}

.module-list {
  padding: 0 12px;
}

.module-card {
  background: #fff;
  border-radius: 10px;
  margin-bottom: 8px;
  overflow: hidden;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.04);
  transition: transform 0.15s, box-shadow 0.15s;
}

.module-card:active {
  transform: scale(0.985);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.module-card.module-pending { border-left: 4px solid #9ba3af; }
.module-card.module-not_started { border-left: 4px solid #2563eb; }
.module-card.module-in_progress { border-left: 4px solid #d97706; }
.module-card.module-completed { border-left: 4px solid #059669; }

.module-card-body {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
}

.module-left {
  flex: 1;
  min-width: 0;
}

.module-name {
  font-size: 15px;
  font-weight: 500;
  color: #1a1d26;
}

.module-weight {
  font-size: 12px;
  color: #9ba3af;
  margin-top: 3px;
}

.module-score {
  font-size: 14px;
  font-weight: 700;
  margin-right: 6px;
}

.module-score.score-excellent { color: #059669; }
.module-score.score-good { color: #2563eb; }
.module-score.score-normal { color: #d97706; }
.module-score.score-poor { color: #dc2626; }

.module-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.empty-modules {
  text-align: center;
  color: #9ba3af;
  padding: 40px 0;
  font-size: 14px;
}

/* 弹窗样式 */
.module-detail {
  padding: 20px 0 28px;
}

.popup-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px 12px;
}

.popup-title {
  font-size: 17px;
  font-weight: 600;
  color: #1a1d26;
}

.popup-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  background: #f7f8fa;
  margin: 0 16px;
  border-radius: 8px;
  font-size: 13px;
  color: #666;
}

.popup-info-divider {
  color: #ddd;
}

.popup-actions {
  display: flex;
  gap: 10px;
  padding: 16px 20px 0;
  justify-content: center;
}

/* 评分信息区域 */
.popup-score-section {
  margin: 12px 16px 0;
  padding: 14px 16px;
  background: #f7f8fa;
  border-radius: 10px;
}

.popup-score-main {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.popup-score-label {
  font-size: 13px;
  color: #666;
}

.popup-score-value {
  font-size: 28px;
  font-weight: 700;
}

.popup-score-unit {
  font-size: 13px;
  color: #999;
  margin-left: 2px;
}

.action-row {
  display: flex;
  gap: 8px;
  padding: 8px 16px 12px;
}

.bottom-action {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 16px;
  background: white;
}

.completed-actions {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: white;
  box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.08);
}

.bottom-action-bar {
  display: flex;
  gap: 12px;
  padding: 16px;
}

.bottom-action-bar .van-button {
  flex: 1;
}

/* Pipeline 执行按钮 */
.pipeline-action {
  margin-top: 12px;
  display: flex;
  justify-content: flex-start;
}

/* Pipeline 弹窗内容 */
.pipeline-dialog-content {
  padding: 24px 20px;
}

.pipeline-step {
  display: flex;
  align-items: center;
  gap: 12px;
}

.step-indicator {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
  background: #e5e7eb;
  color: #9ba3af;
}

.pipeline-step.step-done .step-indicator {
  background: #dcfce7;
  color: #16a34a;
}

.pipeline-step.step-current .step-indicator {
  background: #dbeafe;
  color: #2563eb;
}

.pipeline-step.step-running .step-indicator {
  background: #fef3c7;
  color: #d97706;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.step-info {
  flex: 1;
}

.step-name {
  font-size: 15px;
  font-weight: 500;
  color: #1a1d26;
}

.step-desc {
  font-size: 12px;
  color: #9ba3af;
  margin-top: 2px;
}

.step-score {
  font-size: 14px;
  font-weight: 700;
}

.pipeline-connector {
  width: 2px;
  height: 24px;
  background: #e5e7eb;
  margin: 4px 0 4px 15px;
  border-radius: 1px;
}

.pipeline-connector.active {
  background: #16a34a;
}

.pipeline-error {
  margin-top: 16px;
  padding: 10px 12px;
  background: #fef2f2;
  border-radius: 8px;
  color: #dc2626;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>
