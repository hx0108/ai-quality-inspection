<template>
  <div class="task-list-page">
    <van-nav-bar>
      <template #title>
        <div v-if="authStore.hasMultipleProjects" class="project-switcher" @click="showProjectSheet = true">
          {{ authStore.activeProjectName || '选择项目' }} <van-icon name="arrow-down" size="12" />
        </div>
        <span v-else>巡检任务</span>
      </template>
      <template #right>
        <van-icon name="user-o" size="18" style="margin-right:8px" @click="showUser = true" />
        <van-icon v-if="isAdmin" name="plus" size="18" @click="showCreate = true" />
      </template>
    </van-nav-bar>

    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <van-loading v-if="loading && tasks.length === 0" class="loading-center" />

      <van-empty v-else-if="!loading && tasks.length === 0" description="暂无检查任务">
        <van-button v-if="isAdmin" type="primary" @click="showCreate = true">
          创建检查任务
        </van-button>
        <p v-else class="empty-tip">请等待管理员分配检查任务</p>
      </van-empty>

      <div v-else class="task-list">
        <div v-for="task in tasks" :key="task.task_id" class="task-card" :class="`status-${task.status}`">
          <div class="task-header" @click="toggleTask(task.task_id)">
            <div class="task-info">
              <div class="task-title">{{ task.project_name }}</div>
              <div class="task-date">检查日期：{{ task.check_date }}</div>
            </div>
            <van-tag :type="getStatusType(task.status)">{{ getStatusText(task.status) }}</van-tag>
            <van-icon :name="expandedTaskId === task.task_id ? 'arrow-up' : 'arrow-down'" />
          </div>

          <!-- 展开区域 -->
          <div v-if="expandedTaskId === task.task_id">
            <!-- 评分信息卡片（有评分结果时显示） -->
            <div v-if="task.total_score != null || hasScoringResults(task.task_id)" class="score-card">
              <div class="score-card-left">
                <span class="score-card-label">AI评分</span>
                <span v-if="task.total_score != null" class="score-card-value" :class="getScoreClass(task.total_score)">{{ task.total_score }}</span>
                <span v-else-if="scoringStatusMap.get(task.task_id)?.status === 'scoring'" class="score-card-loading">
                  <van-loading size="14" color="#d97706" style="margin-right: 4px" />评分中...
                </span>
                <span v-else class="score-card-value" style="color: #9ba3af">待评分</span>
              </div>
              <van-button v-if="!isViewOnly" size="small" :type="getScoringButtonType(task.task_id)" round @click.stop="goScoring(task.task_id)">
                {{ getScoringButtonText(task.task_id) }}
              </van-button>
            </div>

            <!-- 管理员：操作按钮 -->
            <div v-if="isAdmin" class="task-actions">
              <van-button size="small" type="primary" plain @click="goToTask(task.task_id)">
                查看详情 / 分配模块
              </van-button>
              <van-button v-if="!hasScoringResults(task.task_id) && task.status === 'completed'" size="small" type="success" plain @click.stop="goScoring(task.task_id)">
                AI 评分
              </van-button>
            </div>

            <!-- 驻场经理/项目人员：只读模块列表 -->
            <div v-if="isViewOnly && task.my_modules && task.my_modules.length > 0" class="module-list">
              <div
                v-for="mod in task.my_modules"
                :key="mod.module_name"
                class="module-item"
              >
                <div class="module-info">
                  <span class="module-name">{{ mod.module_name }}</span>
                  <div class="module-tags">
                    <van-tag
                      size="medium"
                      :type="getModuleStatusType(mod.status)"
                    >{{ getModuleStatusText(mod.status) }}</van-tag>
                    <van-tag v-if="mod.score != null" size="medium" type="success" style="margin-left:4px">{{ mod.score }}分</van-tag>
                  </div>
                </div>
                <van-button
                  v-if="mod.record_id"
                  size="small"
                  type="default"
                  @click.stop="viewModuleDetail(mod.record_id)"
                >
                  查看
                </van-button>
              </div>
            </div>

            <!-- 检查员：显示模块列表 -->
            <div v-if="isInspector && task.my_modules && task.my_modules.length > 0" class="module-list">
              <div
                v-for="mod in task.my_modules"
                :key="mod.module_name"
                class="module-item"
                @click="onModuleClick(task.task_id, mod)"
              >
                <div class="module-info">
                  <span class="module-name">{{ mod.module_name }}</span>
                  <van-tag
                    size="medium"
                    :type="getModuleStatusType(mod.status)"
                  >{{ getModuleStatusText(mod.status) }}</van-tag>
                </div>
                <van-button
                  size="small"
                  :type="mod.status === 'not_started' ? 'primary' : 'warning'"
                  :loading="mod._starting"
                  @click.stop="onModuleClick(task.task_id, mod)"
                >
                  {{ mod.status === 'not_started' ? '开始检查' : mod.status === 'in_progress' ? '继续检查' : '查看' }}
                </van-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </van-pull-refresh>

    <van-tabbar v-model="activeTab" route>
      <van-tabbar-item icon="chart-trending-o" to="/dashboard">概览</van-tabbar-item>
      <van-tabbar-item icon="home-o" to="/tasks">任务</van-tabbar-item>
      <van-tabbar-item icon="todo-list-o" to="/reports">报告</van-tabbar-item>
      <van-tabbar-item icon="shield-o" to="/rectification">整改</van-tabbar-item>
      <van-tabbar-item icon="bar-chart-o" to="/analysis-mobile">分析</van-tabbar-item>
    </van-tabbar>

    <!-- 用户信息弹窗 -->
    <van-action-sheet v-model:show="showProjectSheet" title="切换项目">
      <div class="project-sheet-list">
        <div
          v-for="p in authStore.projects"
          :key="p.id"
          class="project-sheet-item"
          :class="{ 'project-sheet-active': p.id === authStore.activeProjectId }"
          @click="onSwitchProject(p.id)"
        >
          {{ p.name }}
          <van-icon v-if="p.id === authStore.activeProjectId" name="success" color="#c6a56a" />
        </div>
      </div>
    </van-action-sheet>

    <MobileUserSheet v-model:show="showUser" />

    <!-- 创建任务弹窗 -->
    <van-popup v-model:show="showCreate" position="bottom" round style="height: 60%">
      <div class="create-form">
        <h3>创建检查任务</h3>
        <van-form @submit="onCreateTask">
          <van-cell-group inset>
            <van-field
              v-model="newTask.project_name"
              is-link
              readonly
              label="项目名称"
              placeholder="选择项目"
              @click="showProjectPicker = true"
            />
            <van-field
              v-model="standardLabel"
              is-link
              readonly
              label="检查标准"
              placeholder="选择检查标准"
              @click="showStandardPicker = true"
            />
            <van-field
              v-model="newTask.check_date"
              is-link
              readonly
              label="检查日期"
              placeholder="选择日期"
              @click="showDatePicker = true"
            />
          </van-cell-group>
          <div style="margin: 16px;">
            <van-button round block type="primary" native-type="submit" :loading="creating">
              创建任务
            </van-button>
          </div>
        </van-form>
      </div>
    </van-popup>

    <!-- 项目选择器 -->
    <van-popup v-model:show="showProjectPicker" position="bottom" round>
      <van-picker
        :columns="projectColumns"
        @confirm="onProjectConfirm"
        @cancel="showProjectPicker = false"
      />
    </van-popup>

    <!-- 日期选择器 -->
    <van-popup v-model:show="showDatePicker" position="bottom" round>
      <van-date-picker
        v-model="selectedDate"
        @confirm="onDateConfirm"
        @cancel="showDatePicker = false"
      />
    </van-popup>

    <!-- 检查标准选择器 -->
    <van-popup v-model:show="showStandardPicker" position="bottom" round>
      <van-picker
        :columns="standardColumns"
        @confirm="onStandardConfirm"
        @cancel="showStandardPicker = false"
      />
    </van-popup>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showSuccessToast } from 'vant'
import { useAuthStore } from '../../stores/auth'
import MobileUserSheet from '../../components/MobileUserSheet.vue'
import { getMyTasks, getProjects, createTask } from '../../api/tasks'
import { createRecord } from '../../api/inspection'
import { getScoringStatus, getModuleScoringStatus } from '../../api/scoring'

const router = useRouter()
const authStore = useAuthStore()

const tasks = ref([])
const loading = ref(false)
const refreshing = ref(false)
const activeTab = ref(1)
const showUser = ref(false)
const showProjectSheet = ref(false)

const onSwitchProject = (projectId) => {
  showProjectSheet.value = false
  authStore.setActiveProject(projectId)
}
const showCreate = ref(false)
const showProjectPicker = ref(false)
const showDatePicker = ref(false)
const showStandardPicker = ref(false)
const standardTypes = ref([])
const creating = ref(false)
const expandedTaskId = ref(null)

const projects = ref([])
const newTask = ref({
  project_id: null,
  project_name: '',
  standard_type: 'diecheng',
  check_date: ''
})
const selectedDate = ref(['2026', '03', '31'])

const user = computed(() => authStore.user)
const isAdmin = computed(() => user.value.role === 'admin')
const isProjectStaff = computed(() => user.value.role === 'project_staff')
const isInspector = computed(() => user.value.role === 'inspector')
const isViewOnly = computed(() => user.value.role === 'field_supervisor' || user.value.role === 'project_staff')

const projectColumns = computed(() => {
  return projects.value.map(p => ({ text: p.name, value: p.id }))
})

const standardColumns = computed(() => {
  return standardTypes.value.map(s => ({ text: s.label, value: s.value }))
})

const standardLabel = computed(() => {
  const found = standardTypes.value.find(s => s.value === newTask.value.standard_type)
  return found ? found.label : '标准版'
})

const toggleTask = (taskId) => {
  expandedTaskId.value = expandedTaskId.value === taskId ? null : taskId
}

const onLoad = async () => {
  loading.value = true
  try {
    const res = await getMyTasks({ project_id: authStore.activeProjectId })
    tasks.value = (res.items || []).map(t => ({
      ...t,
      my_modules: (t.my_modules || []).map(m => ({ ...m, _starting: false }))
    }))
    // 查询所有任务的评分状态
    for (const t of tasks.value) {
      await fetchScoringStatus(t.task_id)
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const onRefresh = async () => {
  await onLoad()
  refreshing.value = false
}

const fetchProjects = async () => {
  try {
    const res = await getProjects()
    projects.value = res.items || []
  } catch (e) {
    console.error(e)
  }
}

const fetchStandardTypesList = () => {
  standardTypes.value = [
    { value: 'diecheng', label: '标准版' },
    { value: 'feidiecheng', label: '简化版' }
  ]
}

const onModuleClick = async (taskId, mod) => {
  // 已有记录 → 直接跳转检查页
  if (mod.record_id) {
    router.push(`/inspection/${mod.record_id}`)
    return
  }

  // 没有记录 → 先创建，再跳转
  mod._starting = true
  try {
    const res = await createRecord({ task_id: taskId, module_name: mod.module_name })
    router.push(`/inspection/${res.record_id}`)
  } catch (e) {
    showToast(e.response?.data?.detail || '创建记录失败')
  } finally {
    mod._starting = false
  }
}

const goToTask = (taskId) => {
  router.push(`/task/${taskId}`)
}

const viewModuleDetail = (recordId) => {
  router.push(`/inspection/${recordId}`)
}

const onProjectConfirm = ({ selectedOptions }) => {
  const selected = selectedOptions[0]
  newTask.value.project_id = selected.value
  newTask.value.project_name = selected.text
  showProjectPicker.value = false
}

const onDateConfirm = ({ selectedValues }) => {
  newTask.value.check_date = selectedValues.join('-')
  showDatePicker.value = false
}

const onStandardConfirm = ({ selectedOptions }) => {
  const selected = selectedOptions[0]
  newTask.value.standard_type = selected.value
  showStandardPicker.value = false
}

const onCreateTask = async () => {
  if (!newTask.value.project_id) {
    showToast('请选择项目')
    return
  }
  if (!newTask.value.check_date) {
    showToast('请选择日期')
    return
  }

  creating.value = true
  try {
    await createTask({
      project_id: newTask.value.project_id,
      check_date: newTask.value.check_date,
      standard_type: newTask.value.standard_type
    })
    showSuccessToast('任务创建成功')
    showCreate.value = false
    await onLoad()
  } catch (e) {
    showToast('创建失败')
  } finally {
    creating.value = false
  }
}

const getStatusType = (status) => {
  const map = { pending: 'default', in_progress: 'warning', completed: 'success' }
  return map[status] || 'default'
}

const getStatusText = (status) => {
  const map = { pending: '待开始', in_progress: '进行中', completed: '已完成' }
  return map[status] || status
}

const getModuleStatusType = (status) => {
  const map = { not_started: 'default', in_progress: 'warning', completed: 'success' }
  return map[status] || 'default'
}

const getModuleStatusText = (status) => {
  const map = { not_started: '未开始', in_progress: '检查中', completed: '已完成' }
  return map[status] || status
}

// 评分状态缓存
const scoringStatusMap = ref(new Map())  // taskId -> { status, progress }

const isAllModulesCompleted = (task) => {
  const modules = task.my_modules || []
  return modules.length > 0 && modules.every(m => m.status === 'completed')
}

const fetchScoringStatus = async (taskId) => {
  try {
    const res = await getScoringStatus(taskId)
    let status = 'not_started'
    let progress = ''
    if (res.is_complete) {
      status = 'completed'
    } else if (res.scored_modules > 0 || res.total_modules > 0) {
      status = 'scoring'
      progress = `${res.scored_modules}/${res.total_modules}`
    }
    scoringStatusMap.value.set(taskId, { status, progress })

    // 如果有评分数据，获取总分
    if (status !== 'not_started') {
      try {
        const moduleRes = await getModuleScoringStatus(taskId)
        const task = tasks.value.find(t => t.task_id === taskId)
        if (task && moduleRes.current_total_score != null) {
          task.total_score = Math.round(moduleRes.current_total_score * 100) / 100
        }
      } catch (e) { /* ignore */ }
    }

    // 触发响应式更新
    scoringStatusMap.value = new Map(scoringStatusMap.value)
  } catch (e) {
    scoringStatusMap.value.set(taskId, { status: 'not_started', progress: '' })
    scoringStatusMap.value = new Map(scoringStatusMap.value)
  }
}

const getScoringButtonType = (taskId) => {
  const info = scoringStatusMap.value.get(taskId)
  if (!info) return 'primary'
  if (info.status === 'scoring') return 'warning'
  if (info.status === 'completed') return 'success'
  return 'primary'
}

const getScoringButtonText = (taskId) => {
  const info = scoringStatusMap.value.get(taskId)
  if (!info) return 'AI 评分'
  if (info.status === 'scoring') return `AI 评分中 (${info.progress})...`
  if (info.status === 'completed') return '查看评分结果'
  return 'AI 评分'
}

const hasScoringResults = (taskId) => {
  const info = scoringStatusMap.value.get(taskId)
  return info && (info.status === 'completed' || info.status === 'scoring')
}

const getScoringStatusText = (taskId) => {
  const info = scoringStatusMap.value.get(taskId)
  if (!info) return '未评分'
  if (info.status === 'completed') return '已评分'
  if (info.status === 'scoring') return '评分中...'
  return '未评分'
}

const getScoreClass = (score) => {
  if (score >= 90) return 'score-excellent'
  if (score >= 75) return 'score-good'
  if (score >= 60) return 'score-normal'
  return 'score-poor'
}

const goScoring = (taskId) => {
  router.push(`/scoring/${taskId}`)
}

onMounted(() => {
  onLoad()
  if (isAdmin.value) {
    fetchProjects()
    fetchStandardTypesList()
  }
})
</script>

<style scoped>
.project-switcher {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  color: var(--van-nav-bar-title-text-color, var(--van-text-color, #323233));
}
.project-sheet-list { padding: 8px 0; }
.project-sheet-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  font-size: 15px;
  cursor: pointer;
}
.project-sheet-item:active { background: #f5f5f5; }
.project-sheet-active { color: #c6a56a; font-weight: 600; }

.task-list-page {
  min-height: 100vh;
  background: #f5f7fa;
  padding-bottom: 60px;
}

.loading-center {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 50vh;
}

.task-list {
  padding: 12px;
}

.task-card {
  background: #fff;
  border-radius: 12px;
  margin-bottom: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  position: relative;
  transition: box-shadow 0.2s;
}

.task-card:active {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* 左侧状态条 */
.task-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: #9ba3af;
}

.task-card.status-pending::before { background: #9ba3af; }
.task-card.status-in_progress::before { background: #d97706; }
.task-card.status-completed::before { background: #059669; }

.task-header {
  display: flex;
  align-items: center;
  padding: 16px 16px 16px 20px;
  gap: 10px;
}

.task-info {
  flex: 1;
  min-width: 0;
}

.task-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1d26;
  line-height: 1.4;
}

.task-date {
  font-size: 12px;
  color: #9ba3af;
  margin-top: 4px;
}

.task-actions {
  padding: 0 16px 14px 20px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* 评分信息卡片 */
.score-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px 12px 20px;
  background: linear-gradient(135deg, #f0f9ff, #eff6ff);
  border-top: 1px solid #e0e7ff;
}

.score-card-left {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.score-card-label {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
}

.score-card-value {
  font-size: 24px;
  font-weight: 700;
}

.score-card-value.score-excellent { color: #059669; }
.score-card-value.score-good { color: #2563eb; }
.score-card-value.score-normal { color: #d97706; }
.score-card-value.score-poor { color: #dc2626; }

.score-card-loading {
  display: flex;
  align-items: center;
  font-size: 13px;
  color: #d97706;
}

.module-list {
  border-top: 1px solid #f5f5f5;
  background: #fafbfc;
}

.module-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.15s;
}

.module-item:last-child {
  border-bottom: none;
}

.module-item:active {
  background: #f5f7fa;
}

.module-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-width: 0;
}

.module-name {
  font-size: 14px;
  color: #333;
}

.empty-tip {
  color: #9ba3af;
  font-size: 14px;
  margin-top: 10px;
}

.create-form {
  padding: 20px;
}

.create-form h3 {
  text-align: center;
  margin-bottom: 20px;
  font-size: 17px;
  color: #1a1d26;
}

/* 弹窗内装饰条 */
.create-form::before {
  content: '';
  display: block;
  height: 3px;
  background: #2563eb;
  border-radius: 2px;
  margin-bottom: 20px;
}
</style>
