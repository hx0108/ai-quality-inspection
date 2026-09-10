<template>
  <div class="rectification-page">
    <van-nav-bar title="整改闭环">
      <template #right>
        <van-icon name="user-o" size="20" @click="showUser = true" />
      </template>
    </van-nav-bar>

    <!-- 筛选栏（原型：下拉 + 状态 chips） -->
    <div class="filter-bar">
      <van-dropdown-menu active-color="var(--blue)">
        <van-dropdown-item v-model="projectFilter" :options="projectOptions" @change="onFilterChange" />
        <van-dropdown-item v-model="moduleFilter" :options="moduleOptions" @change="onFilterChange" />
      </van-dropdown-menu>
    </div>
    <div class="status-chips">
      <button
        v-for="s in statusChips"
        :key="s.value"
        class="chip"
        :class="{ on: statusFilter === s.value }"
        @click="statusFilter = s.value; onFilterChange()"
      >{{ s.label }}</button>
    </div>

    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <van-loading v-if="loading && items.length === 0" class="loading-center" />

      <van-empty v-else-if="!loading && filteredItems.length === 0" description="暂无整改记录" />

      <!-- 扁平整改卡（原型 09） -->
      <div v-else class="flat-list">
        <div v-for="item in filteredItems" :key="item.rectification_id" class="rc-card">
          <div class="rc-top">
            <span class="rc-id">{{ item.rectification_id }}</span>
            <span class="kt" :class="rectKtClass(item.status)">{{ getStatusText(item.status) }}</span>
          </div>
          <div class="rc-desc">{{ item.description }}</div>
          <div class="rc-meta">
            <span class="ktag ktag-muted">{{ item.project_name }}</span>
            <span class="rc-module">{{ item.module_name }}</span>
            <van-tag plain size="small" :type="item.severity === '严重' ? 'danger' : 'warning'">
              {{ item.severity }}
            </van-tag>
          </div>

          <!-- AI 审核结果 -->
          <div v-if="item.ai_result" class="ai-result-block">
            <div class="ai-result-header">
              <van-icon name="shield-o" color="var(--blue)" />
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
            <div v-if="item.ai_checked_at" class="ai-time">
              AI核查时间：{{ formatTime(item.ai_checked_at) }}
            </div>
          </div>

          <!-- 驳回原因 -->
          <div v-if="item.status === 'pending' && item.review_note" class="rect-reject-reason">
            <van-icon name="warning-o" color="var(--err)" />
            <span>驳回原因：{{ item.review_note }}</span>
          </div>

          <div class="rc-foot">
            <span
              v-if="item.deadline"
              class="rc-due"
              :class="{ 'rect-overdue': isOverdue(item.deadline), 'rect-expiring': isExpiring(item.deadline) }"
            >期限 {{ item.deadline }}</span>
            <span v-else class="rc-due">期限 —</span>
            <div class="rc-acts">
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
                详情
              </van-button>
            </div>
          </div>
        </div>
      </div>
    </van-pull-refresh>

    <MobileTabbar />

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
import MobileTabbar from '../../components/MobileTabbar.vue'
import { getPendingRectifications, appealRectification } from '../../api/rectification'

const router = useRouter()
const authStore = useAuthStore()

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

// 状态筛选 chips（原型形态）
const statusChips = [
  { label: '全部', value: '' },
  { label: '待整改', value: 'pending' },
  { label: 'AI驳回', value: 'ai_rejected' },
  { label: '待审核', value: 'pending_review' },
  { label: 'AI通过', value: 'ai_approved' },
  { label: '已通过', value: 'approved' }
]

// 状态 → 芯片语义色
const rectKtClass = (status) => {
  const map = {
    pending: 'kt-muted',
    submitted: 'kt-warn',
    pending_review: 'kt-warn',
    approved: 'kt-ok',
    ai_approved: 'kt-ok',
    ai_rejected: 'kt-err',
    rejected: 'kt-err',
    disputed: 'kt-brand'
  }
  return map[status] || 'kt-muted'
}

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
  color: var(--orange);
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
  color: var(--orange);
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

/* ===== 原型形态：状态 chips + 扁平整改卡 ===== */
.status-chips {
  display: flex;
  gap: 6px;
  padding: 8px 14px 2px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
.status-chips::-webkit-scrollbar { display: none; }

.chip {
  flex-shrink: 0;
  height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid var(--ink-200);
  background: var(--bg-card);
  font-family: var(--sans);
  font-size: 12.5px;
  font-weight: 500;
  color: var(--ink-600);
  cursor: pointer;
  transition: all 0.12s;
}
.chip.on {
  background: var(--blue);
  border-color: var(--blue);
  color: #fff;
  font-weight: 600;
}

.flat-list { padding: 10px 14px; }

.rc-card {
  background: var(--bg-card);
  border: 1px solid var(--ink-200);
  border-radius: 12px;
  padding: 13px 14px;
  margin-bottom: 10px;
}

.rc-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.rc-id {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--ink-400);
}

.rc-desc {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink-900);
  margin-top: 7px;
  line-height: 1.5;
}

.rc-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.rc-module {
  font-size: 12px;
  color: var(--ink-500);
}

.rc-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 11px;
}

.rc-due {
  font-size: 12px;
  color: var(--ink-500);
  font-variant-numeric: tabular-nums;
}

.rc-due.rect-overdue { color: var(--err-strong); font-weight: 700; }
.rc-due.rect-expiring { color: var(--warn-strong); font-weight: 600; }

.rc-acts {
  display: flex;
  gap: 8px;
  margin-left: auto;
}
</style>
