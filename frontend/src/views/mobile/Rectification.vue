<template>
  <div class="rectification-page">
    <van-nav-bar title="整改闭环">
      <template #right>
        <van-icon name="user-o" size="20" @click="showUser = true" />
      </template>
    </van-nav-bar>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <van-dropdown-menu active-color="#2563eb">
        <van-dropdown-item v-model="projectFilter" :options="projectOptions" @change="onFilterChange" />
        <van-dropdown-item v-model="moduleFilter" :options="moduleOptions" @change="onFilterChange" />
        <van-dropdown-item v-model="statusFilter" :options="statusOptions" @change="onFilterChange" />
      </van-dropdown-menu>
    </div>

    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <van-loading v-if="loading && items.length === 0" class="loading-center" />

      <van-empty v-else-if="!loading && filteredItems.length === 0" description="暂无整改记录" />

      <div v-else class="grouped-list">
        <!-- 第一层：项目 -->
        <div
          v-for="group in groupedItems"
          :key="group.project_name"
          class="project-group"
        >
          <div class="project-header" @click="toggleProject(group.project_name)">
            <div class="project-header-left">
              <van-icon
                :name="expandedProjects.includes(group.project_name) ? 'arrow-down' : 'arrow'"
                color="#2563eb"
                size="14"
              />
              <span class="project-name">{{ group.project_name }}</span>
            </div>
            <div class="project-header-right">
              <span class="project-summary">{{ group.totalModules }}模块 {{ group.totalIssues }}项</span>
              <span v-if="group.pending" class="project-badge pending">{{ group.pending }}待整改</span>
            </div>
          </div>

          <!-- 展开的项目体 -->
          <div v-if="expandedProjects.includes(group.project_name)" class="project-body">
            <!-- 第二层：模块 -->
            <div
              v-for="mod in group.modules"
              :key="mod.module_name"
              class="module-group"
            >
              <div class="module-header" @click="toggleModule(group.project_name, mod.module_name)">
                <div class="module-header-left">
                  <van-icon
                    :name="isModuleExpanded(group.project_name, mod.module_name) ? 'arrow-down' : 'arrow'"
                    color="#64748b"
                    size="12"
                  />
                  <span class="module-name">{{ mod.module_name }}</span>
                </div>
                <div class="module-header-right">
                  <span class="module-count">{{ mod.items.length }}项</span>
                  <span v-if="mod.pending" class="module-badge">{{ mod.pending }}待整改</span>
                </div>
              </div>

              <!-- 展开的模块体：整改条目 -->
              <div v-if="isModuleExpanded(group.project_name, mod.module_name)" class="module-body">
                <div
                  v-for="item in mod.items"
                  :key="item.rectification_id"
                  class="rect-card"
                >
                  <div class="rect-top-row">
                    <span class="rect-desc-brief">{{ item.description }}</span>
                    <van-tag :type="getStatusType(item.status)" size="small">{{ getStatusText(item.status) }}</van-tag>
                  </div>
                  <div class="rect-meta">
                    <span>{{ item.check_date }}</span>
                    <van-tag plain size="small" :type="item.severity === '严重' ? 'danger' : 'warning'">
                      {{ item.severity }}
                    </van-tag>
                    <span v-if="item.deadline" class="rect-deadline" :class="{ 'rect-overdue': isOverdue(item.deadline), 'rect-expiring': isExpiring(item.deadline) }">
                      截止 {{ item.deadline }}
                    </span>
                  </div>

                  <!-- AI 审核结果 -->
                  <div v-if="item.ai_result" class="ai-result-block">
                    <div class="ai-result-header">
                      <van-icon name="shield-o" color="#2563eb" />
                      <span class="ai-result-title">AI 核查结果</span>
                      <van-tag :type="item.ai_result.rectification_qualified ? 'success' : 'danger'" size="small">
                        {{ item.ai_result.rectification_qualified ? '通过' : '未通过' }}
                      </van-tag>
                    </div>
                    <div class="ai-result-row">
                      <span class="ai-label">置信度</span>
                      <span class="ai-value">{{ item.ai_result.confidence_score || 0 }}分</span>
                    </div>
                    <div v-if="item.ai_result.analysis" class="ai-analysis">{{ item.ai_result.analysis }}</div>
                    <div v-if="item.ai_result.watermark_valid !== undefined" class="ai-result-row">
                      <span class="ai-label">水印验证</span>
                      <van-tag :type="item.ai_result.watermark_valid ? 'success' : 'danger'" plain size="small">
                        {{ item.ai_result.watermark_valid ? '有效' : '无效' }}
                      </van-tag>
                    </div>
                    <div v-if="item.ai_result.suggestion" class="ai-result-row">
                      <span class="ai-label">建议</span>
                      <van-tag :type="item.ai_result.suggestion === '通过' ? 'success' : 'danger'" plain size="small">
                        {{ item.ai_result.suggestion }}
                      </van-tag>
                    </div>
                    <div v-if="item.ai_checked_at" class="ai-time">
                      AI核查时间：{{ formatTime(item.ai_checked_at) }}
                    </div>
                  </div>

                  <!-- 驳回原因（人工驳回后 status 会重置为 pending，但保留 review_note） -->
                  <div v-if="item.status === 'pending' && item.review_note" class="rect-reject-reason">
                    <van-icon name="warning-o" color="#ee0a24" />
                    <span>驳回原因：{{ item.review_note }}</span>
                  </div>

                  <!-- 操作按钮 -->
                  <div class="rect-actions">
                    <van-button
                      v-if="item.status === 'pending'"
                      type="primary"
                      size="small"
                      round
                      icon="photograph"
                      @click="goSubmit(item)"
                    >
                      {{ item.review_note ? '重新整改' : '上传整改' }}
                    </van-button>
                    <van-button
                      v-if="item.status === 'ai_rejected' && authStore.isProjectStaff"
                      type="warning"
                      size="small"
                      round
                      plain
                      @click="openAppeal(item)"
                    >
                      申诉
                    </van-button>
                    <van-button
                      plain
                      type="primary"
                      size="small"
                      round
                      icon="eye-o"
                      @click="goDetail(item)"
                    >
                      查看详情
                    </van-button>
                  </div>
                </div>
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

    <MobileUserSheet v-model:show="showUser" />

    <!-- 申诉对话框 -->
    <van-dialog
      v-model:show="showAppealDialog"
      title="提交申诉"
      show-cancel-button
      :before-close="onAppealBeforeClose"
    >
      <div style="padding: 16px">
        <van-field
          v-model="appealNote"
          type="textarea"
          rows="3"
          placeholder="请说明申诉理由"
          maxlength="500"
          show-word-limit
        />
      </div>
    </van-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showSuccessToast } from 'vant'
import { useAuthStore } from '../../stores/auth'
import MobileUserSheet from '../../components/MobileUserSheet.vue'
import { getPendingRectifications, appealRectification } from '../../api/rectification'

const router = useRouter()
const authStore = useAuthStore()

const activeTab = ref(3)
const showUser = ref(false)
const showAppealDialog = ref(false)
const appealNote = ref('')
const appealTarget = ref(null)
const loading = ref(false)
const refreshing = ref(false)
const items = ref([])
const projectFilter = ref('')
const moduleFilter = ref('')
const statusFilter = ref('')

// 两级展开状态
const expandedProjects = ref([])
const expandedModules = ref({})  // { projectName: [moduleName, ...] }

const toggleProject = (name) => {
  const idx = expandedProjects.value.indexOf(name)
  if (idx >= 0) {
    expandedProjects.value.splice(idx, 1)
    delete expandedModules.value[name]
  } else {
    expandedProjects.value.push(name)
  }
}

const toggleModule = (projectName, moduleName) => {
  if (!expandedModules.value[projectName]) {
    expandedModules.value[projectName] = []
  }
  const arr = expandedModules.value[projectName]
  const idx = arr.indexOf(moduleName)
  if (idx >= 0) {
    arr.splice(idx, 1)
  } else {
    arr.push(moduleName)
  }
  // 触发响应式更新
  expandedModules.value = { ...expandedModules.value }
}

const isModuleExpanded = (projectName, moduleName) => {
  return expandedModules.value[projectName]?.includes(moduleName) ?? false
}

const statusOptions = [
  { text: '全部状态', value: '' },
  { text: '待整改', value: 'pending' },
  { text: 'AI通过', value: 'ai_approved' },
  { text: 'AI驳回', value: 'ai_rejected' },
  { text: '待审核', value: 'pending_review' },
  { text: '已通过', value: 'approved' }
]

const projectOptions = computed(() => {
  const projects = [...new Set(items.value.map(i => i.project_name).filter(Boolean))].sort()
  return [{ text: '全部项目', value: '' }, ...projects.map(p => ({ text: p, value: p }))]
})

const moduleOptions = computed(() => {
  const modules = [...new Set(items.value.map(i => i.module_name).filter(Boolean))].sort()
  return [{ text: '全部模块', value: '' }, ...modules.map(m => ({ text: m, value: m }))]
})

const filteredItems = computed(() => {
  let list = items.value
  if (projectFilter.value) {
    list = list.filter(i => i.project_name === projectFilter.value)
  }
  if (moduleFilter.value) {
    list = list.filter(i => i.module_name === moduleFilter.value)
  }
  if (statusFilter.value) {
    list = list.filter(i => i.status === statusFilter.value)
  }
  return list
})

const groupedItems = computed(() => {
  const groups = {}
  for (const item of filteredItems.value) {
    const proj = item.project_name || '未分配'
    const mod = item.module_name || '未分配'
    if (!groups[proj]) groups[proj] = {}
    if (!groups[proj][mod]) groups[proj][mod] = []
    groups[proj][mod].push(item)
  }
  return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b)).map(([project_name, modules]) => ({
    project_name,
    modules: Object.entries(modules).sort(([a], [b]) => a.localeCompare(b)).map(([module_name, items]) => ({
      module_name,
      items,
      total: items.length,
      pending: items.filter(i => i.status === 'pending').length,
    })),
    totalIssues: Object.values(modules).flat().length,
    totalModules: Object.keys(modules).length,
    pending: Object.values(modules).flat().filter(i => i.status === 'pending').length,
  }))
})

const onFilterChange = () => {
  // computed 自动处理筛选，此处处理自动展开
  if (projectFilter.value) {
    if (!expandedProjects.value.includes(projectFilter.value)) {
      expandedProjects.value = [projectFilter.value]
    }
    // 展开该项目下所有模块
    const group = groupedItems.value.find(g => g.project_name === projectFilter.value)
    if (group) {
      expandedModules.value = {
        [projectFilter.value]: group.modules.map(m => m.module_name)
      }
    }
    if (moduleFilter.value) {
      expandedModules.value = {
        [projectFilter.value]: [moduleFilter.value]
      }
    }
  } else if (moduleFilter.value) {
    for (const group of groupedItems.value) {
      if (group.modules.some(m => m.module_name === moduleFilter.value)) {
        if (!expandedProjects.value.includes(group.project_name)) {
          expandedProjects.value.push(group.project_name)
        }
        expandedModules.value = {
          ...expandedModules.value,
          [group.project_name]: [moduleFilter.value]
        }
      }
    }
  }
}

const getStatusType = (status) => {
  const map = {
    pending: 'warning',
    submitted: 'primary',
    ai_approved: 'success',
    ai_rejected: 'danger',
    pending_review: 'warning',
    approved: 'success'
  }
  return map[status] || 'default'
}

const getStatusText = (status) => {
  const map = {
    pending: '待整改',
    submitted: 'AI核查中',
    ai_approved: 'AI通过',
    ai_rejected: 'AI驳回',
    pending_review: '待人工审核',
    approved: '已通过'
  }
  return map[status] || status
}

const isOverdue = (deadline) => {
  if (!deadline) return false
  return new Date(deadline) < new Date(new Date().toISOString().slice(0, 10))
}
const isExpiring = (deadline) => {
  if (!deadline) return false
  const diff = (new Date(deadline) - new Date(new Date().toISOString().slice(0, 10))) / 86400000
  return diff > 0 && diff <= 5
}

const formatTime = (isoStr) => {
  if (!isoStr) return ''
  return isoStr.slice(0, 16).replace('T', ' ')
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getPendingRectifications()
    items.value = res.items || []
  } catch (e) {
    showToast('加载失败')
  } finally {
    loading.value = false
  }
}

const onRefresh = async () => {
  await fetchData()
  refreshing.value = false
}

const goDetail = (item) => {
  router.push(`/rectification/${item.rectification_id}`)
}

const goSubmit = (item) => {
  router.push(`/rectification/${item.rectification_id}`)
}

const openAppeal = (item) => {
  appealTarget.value = item
  appealNote.value = ''
  showAppealDialog.value = true
}

const onAppealBeforeClose = async (action) => {
  if (action === 'confirm') {
    if (!appealNote.value.trim()) {
      showToast('请填写申诉理由')
      return false
    }
    try {
      await appealRectification(appealTarget.value.rectification_id, { appeal_note: appealNote.value.trim() })
      showSuccessToast('申诉已提交')
      fetchData()
      return true
    } catch (e) {
      showToast(e.response?.data?.detail || '申诉失败')
      return false
    }
  }
  return true
}

onMounted(fetchData)
</script>

<style scoped>
.rectification-page {
  min-height: 100vh;
  background: #f5f6fa;
  padding-bottom: 60px;
}

.filter-bar {
  position: sticky;
  top: 0;
  z-index: 10;
}

.loading-center {
  display: flex;
  justify-content: center;
  padding: 60px 0;
}

.grouped-list {
  padding: 8px 12px;
}

/* 项目组 */
.project-group {
  margin-bottom: 10px;
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  border-radius: 10px;
  padding: 14px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.project-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.project-name {
  font-size: 16px;
  font-weight: 700;
  color: #1a1d26;
}

.project-header-right {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.project-summary {
  font-size: 12px;
  color: #9ba3af;
}

.project-badge {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
}

.project-badge.pending {
  background: #fef3c7;
  color: #d97706;
}

.project-body {
  padding-left: 12px;
  margin-top: 6px;
}

/* 模块组 */
.module-group {
  margin-bottom: 6px;
}

.module-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 8px;
}

.module-header-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.module-name {
  font-size: 14px;
  font-weight: 600;
  color: #475569;
}

.module-header-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.module-count {
  font-size: 12px;
  color: #9ba3af;
}

.module-badge {
  font-size: 11px;
  color: #d97706;
}

.module-body {
  padding: 4px 0 0 8px;
}

/* 整改卡片 */
.rect-card {
  background: #fff;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 6px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}

.rect-top-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.rect-desc-brief {
  font-size: 13px;
  color: #333;
  flex: 1;
  min-width: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.rect-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #9ba3af;
  margin-top: 6px;
}
.rect-deadline {
  font-size: 11px;
  color: #9ba3af;
}
.rect-deadline.rect-overdue {
  color: #ee0a24;
  font-weight: 500;
}
.rect-deadline.rect-expiring {
  color: #ff976a;
}

/* AI 审核结果 */
.ai-result-block {
  margin-top: 8px;
  padding: 10px;
  background: #f0f9ff;
  border-radius: 8px;
  border: 1px solid #bae6fd;
}

.ai-result-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.ai-result-title {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  flex: 1;
}

.ai-result-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 12px;
}

.ai-label {
  color: #64748b;
}

.ai-value {
  font-weight: 600;
  color: #1e293b;
  font-family: "SF Mono", Consolas, monospace;
}

.ai-analysis {
  font-size: 12px;
  color: #475569;
  line-height: 1.5;
  margin: 6px 0;
  padding: 6px;
  background: #fff;
  border-radius: 6px;
}

.ai-time {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 6px;
}

.rect-reject-reason {
  margin-top: 8px;
  padding: 8px;
  background: #fff5f5;
  border-radius: 6px;
  font-size: 12px;
  color: #ee0a24;
  display: flex;
  align-items: center;
  gap: 4px;
}

.rect-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}

</style>
