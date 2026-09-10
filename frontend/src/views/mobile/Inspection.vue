<template>
  <div class="inspection-page">
    <van-nav-bar :title="moduleName" left-arrow @click-left="onBack">
      <template #right>
        <van-icon name="bars" size="18" @click="switchToCardMode" title="切换巡检模式" />
      </template>
    </van-nav-bar>

    <!-- 离线状态提示条 -->
    <OfflineBanner
      :is-online="isOnline"
      :pending-count="offlinePendingCount"
      :syncing="offlineSyncing"
      :sync-progress="offlineSyncProgress"
      :conflict-count="offlineConflictCount"
      @retry-sync="trySyncNow"
    />

    <!-- 顶部信息 -->
    <div class="header-info">
      <div class="header-bg"></div>
      <div class="header-content">
        <div class="progress-row">
          <span class="progress-label">{{ checkedCount }} / {{ items.length }} 已检查</span>
          <span class="progress-pct">{{ progress }}%</span>
        </div>
        <van-progress :percentage="progress" stroke-width="8" :show-pivot="false" color="var(--ok-strong)" track-color="rgba(255,255,255,0.2)" />
        <div class="action-row">
          <van-button size="small" type="primary" plain round @click="markAllQualified" :disabled="pendingCount === 0 || isCompleted">
            全部合格 ({{ pendingCount }}项)
          </van-button>
        </div>
      </div>
    </div>

    <!-- 搜索与筛选 -->
    <div v-if="!loading" class="filter-bar">
      <van-search
        v-model="searchKeyword"
        placeholder="搜索检查项名称..."
        shape="round"
        clearable
        class="filter-search"
      />
      <van-tabs v-model:active="filterStatus" shrink class="filter-tabs">
        <van-tab title="全部" :badge="items.length || ''" />
        <van-tab title="待检" :badge="pendingCount || ''" />
        <van-tab title="已检" :badge="checkedCount || ''" />
        <van-tab title="有问题" :badge="issueCount || ''" />
      </van-tabs>
    </div>

    <!-- AI 检查引导 -->
    <div v-if="!loading && guideTips.length > 0" class="guide-section">
      <div class="guide-header" @click="showGuide = !showGuide">
        <span class="guide-title">AI 检查建议</span>
        <van-icon :name="showGuide ? 'arrow-up' : 'arrow-down'" size="14" />
      </div>
      <div v-if="showGuide" class="guide-content">
        <div v-for="(tip, idx) in guideTips" :key="idx" class="guide-tip">
          <van-tag :type="tip.type === 'recurring' ? 'danger' : tip.type === 'last_check' ? 'warning' : 'primary'" size="medium" class="guide-tag">
            {{ tip.type === 'recurring' ? '反复出现' : tip.type === 'last_check' ? '上次扣分' : tip.type === 'cross_project' ? '共性问题' : '重点关注' }}
          </van-tag>
          <span class="guide-msg">{{ tip.message }}</span>
          <div v-if="tip.items && tip.items.length" class="guide-items">
            <div v-for="(gi, giIdx) in tip.items.slice(0, 3)" :key="giIdx" class="guide-item-row">
              <span v-if="gi.item_id" class="guide-item-id">{{ gi.item_id }}</span>
              <span class="guide-item-text">{{ gi.content || gi.item_name || gi.item_id }}</span>
              <van-tag v-if="gi.last_score" size="small" type="danger">{{ gi.last_score }}分</van-tag>
            </div>
          </div>
        </div>
        <div v-if="guideFocusItems.length > 0" class="guide-focus">
          <div class="guide-focus-title">重点检查项：</div>
          <div v-for="fi in guideFocusItems.slice(0, 5)" :key="fi.item_id" class="guide-focus-item" @click="scrollToItem(fi.item_id)">
            {{ fi.item_id }} {{ fi.item_name }}
            <van-tag v-if="fi.priority === 'high'" size="small" type="danger">高</van-tag>
          </div>
        </div>
      </div>
    </div>

    <!-- 检查项列表 -->
    <van-loading v-if="loading && !fetchError" class="loading-center" />

    <!-- 加载错误提示 -->
    <div v-if="fetchError" class="fetch-error-box">
      <van-icon name="warning-o" size="24" color="var(--err)" />
      <div class="fetch-error-msg">{{ fetchError }}</div>
      <van-button type="primary" size="small" @click="fetchRecord" style="margin-top: 8px;">重新加载</van-button>
    </div>

    <!-- 空状态 -->
    <div v-else-if="items.length === 0" class="empty-state">
      <van-empty description="未加载到检查项模板，请确认模板文件已部署" />
      <van-button type="primary" size="small" @click="fetchRecord" style="margin-top: 8px;">重新加载</van-button>
    </div>

    <div v-else class="items-list">
      <div
        v-for="item in filteredItems"
        :key="item.item_id"
        :data-item-id="item.item_id"
        class="chk-card"
        :class="getItemClass(item)"
      >
        <div class="chk-head" @click="toggleExpand(item)">
          <span class="chk-id">{{ item.item_id }}</span>
          <div class="chk-info">
            <div class="chk-name">{{ item.item_name }}</div>
            <div class="chk-method">{{ item.check_method }}</div>
          </div>
          <span v-if="item.has_issue" class="kt kt-err">有问题<van-icon v-if="item.isOffline" name="cloud-o" style="margin-left:2px" /></span>
          <span v-else-if="item.status === 'checked' && item.qualified" class="kt kt-ok">合格<van-icon v-if="item.isOffline" name="cloud-o" style="margin-left:2px" /></span>
          <span v-else-if="item.status === 'skipped'" class="kt kt-muted">跳过</span>
        </div>

        <!-- 合格 / 有问题（原型：按钮直接上卡片） -->
        <div v-if="!isCompleted" class="m-check-row">
          <button
            class="m-check-btn pass"
            :class="{ on: item.status === 'checked' && item.qualified && !item.has_issue }"
            @click="markQualified(item)"
          >合格</button>
          <button
            class="m-check-btn fail"
            :class="{ on: item.has_issue }"
            @click="markIssue(item)"
          >有问题</button>
        </div>

        <!-- 展开：显示检查标准详情 -->
        <div v-if="expandedId === item.item_id" class="standard-section">
          <div class="standard-card">
            <div class="standard-title">检查标准</div>
            <div class="standard-text">{{ item.check_standard }}</div>
            <div v-if="item.check_method" class="standard-meta">
              <span class="standard-label">检查方法：</span>{{ item.check_method }}
            </div>
            <div v-if="item.scoring_rule" class="standard-meta">
              <span class="standard-label">评分规则：</span>{{ item.scoring_rule }}
            </div>
          </div>
        </div>

        <!-- 展开：已有问题 → 显示描述+照片（可预览） -->
        <div v-if="expandedId === item.item_id && item.has_issue" class="issue-display">
          <div v-for="issue in item.issues" :key="issue.issue_id" class="existing-issue">
            <!-- 编辑模式 -->
            <template v-if="editIssueId === issue.issue_id">
              <van-field
                v-model="issueForm.description"
                rows="3"
                autosize
                type="textarea"
                label="问题描述"
                placeholder="请描述发现的问题..."
              />
              <van-field label="严重程度">
                <template #input>
                  <van-radio-group v-model="issueForm.severity" direction="horizontal">
                    <van-radio name="严重" icon-size="16px">严重</van-radio>
                    <van-radio name="一般" icon-size="16px">一般</van-radio>
                    <van-radio name="轻微" icon-size="16px">轻微</van-radio>
                  </van-radio-group>
                </template>
              </van-field>
              <van-field
                v-model="issueForm.location"
                label="问题位置"
                placeholder="如：3栋2单元5楼走廊（选填）"
              />
              <van-field label="问题照片">
                <template #input>
                  <WatermarkCamera
                    :current-count="issueForm.photos.length"
                    :max-count="5"
                    :project-name="projectName"
                    :project-address="projectAddress"
                    :inspector-name="authStore.user.real_name || ''"
                    @photo-added="onPhotoAdded"
                  />
                  <van-uploader v-model="issueForm.photos" :max-count="5" :show-upload="false" deletable />
                </template>
              </van-field>
              <div class="issue-actions">
                <van-button size="small" @click="cancelEdit">取消</van-button>
                <van-button size="small" type="primary" @click="saveEditIssue(item, issue)" :loading="item.saving">保存修改</van-button>
              </div>
            </template>
            <!-- 显示模式 -->
            <template v-else>
              <div class="issue-severity-tag">
                <van-tag :type="issue.severity === '严重' ? 'danger' : issue.severity === '轻微' ? 'default' : 'warning'" size="medium">
                  {{ issue.severity || '一般' }}
                </van-tag>
              </div>
              <div class="issue-desc-label">问题描述</div>
              <div class="issue-desc-text">{{ issue.description }}</div>
              <div v-if="issue.photos && issue.photos.length > 0" class="issue-photos">
                <div class="issue-photos-label">问题照片</div>
                <div class="photo-grid">
                  <van-image
                    v-for="photo in issue.photos"
                    :key="photo.photo_id"
                    :src="photo.blobUrl"
                    width="80"
                    height="80"
                    fit="cover"
                    radius="4"
                    @click="previewPhoto(issue, photo)"
                  >
                    <template #error>
                      <div class="photo-loading">加载中...</div>
                    </template>
                  </van-image>
                </div>
              </div>
              <div v-if="!isCompleted" class="issue-actions">
                <van-button size="small" type="primary" @click="startEditIssue(issue)">编辑</van-button>
                <van-button size="small" type="danger" @click="onDeleteIssue(item, issue)">删除问题</van-button>
              </div>
            </template>
          </div>
        </div>

        <!-- 展开：无问题 → 显示输入表单 -->
        <div v-if="expandedId === item.item_id && !item.has_issue && !isCompleted" class="issue-form">
          <van-field
            v-model="issueForm.description"
            rows="3"
            autosize
            type="textarea"
            label="问题描述"
            placeholder="请描述发现的问题..."
          />
          <van-field label="严重程度">
            <template #input>
              <van-radio-group v-model="issueForm.severity" direction="horizontal">
                <van-radio name="严重" icon-size="16px">严重</van-radio>
                <van-radio name="一般" icon-size="16px">一般</van-radio>
                <van-radio name="轻微" icon-size="16px">轻微</van-radio>
              </van-radio-group>
            </template>
          </van-field>
          <van-field
            v-model="issueForm.location"
            label="问题位置"
            placeholder="如：3栋2单元5楼走廊（选填）"
          />
          <van-field label="问题照片">
            <template #input>
              <WatermarkCamera
                :current-count="issueForm.photos.length"
                :max-count="5"
                :project-name="projectName"
                :project-address="projectAddress"
                :inspector-name="authStore.user.real_name || ''"
                @photo-added="onPhotoAdded"
              />
              <van-uploader v-model="issueForm.photos" :max-count="5" :show-upload="false" deletable />
            </template>
          </van-field>
          <div class="issue-actions">
            <van-button size="small" @click="expandedId = null">取消</van-button>
            <van-button size="small" type="primary" @click="submitIssue(item)" :loading="item.saving">保存问题</van-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部完成栏（原型：进度信息 + 主按钮） -->
    <div class="bottom-bar">
      <div class="bb-info">
        进度 <b>{{ checkedCount }}/{{ items.length }}</b>
        <span class="bb-issues" v-if="issueCount > 0">问题 {{ issueCount }}</span>
      </div>
      <van-button
        :type="isCompleted ? 'success' : 'primary'"
        round
        @click="completeInspection"
        :disabled="isCompleted"
        :loading="completing"
        class="bb-btn"
      >
        {{ isCompleted ? '检查已完成' : `完成检查 (${progress}%)` }}
      </van-button>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { showToast, showSuccessToast, showConfirmDialog, showImagePreview, closeToast } from 'vant'
import { getRecordDetail, createIssue, completeRecord, uploadPhoto, updateItemStatus, batchUpdateItems, updateIssue, deleteIssue, deletePhoto } from '../../api/inspection'
import { getModuleTemplate, getTaskDetail } from '../../api/tasks'
import { getFocusItems } from '../../api/guide'
import { useOfflineSync } from '../../utils/syncManager'
import { getInspectionState } from '../../utils/inspectionState'
import { forceOverlayCleanup, scheduleCleanup } from '../../utils/overlayGuard'
import OfflineBanner from '../../components/OfflineBanner.vue'
import WatermarkCamera from '../../components/WatermarkCamera.vue'
import { useAuthStore } from '../../stores/auth'
import { getAuthToken } from '../../utils/authStorage'

const router = useRouter()
const route = useRoute()

const recordId = route.params.recordId
const authStore = useAuthStore()
const projectName = ref('')
const projectAddress = ref('')
const items = ref([])
const searchKeyword = ref('')
const filterStatus = ref(0)  // 0=全部, 1=待检, 2=已检, 3=有问题
const loading = ref(true)
const expandedId = ref(null)
const completing = ref(false)
const moduleName = ref('')
const taskId = ref('')
const isCompleted = ref(false)
const editIssueId = ref(null) // 正在编辑的问题ID
const fetchError = ref(null) // 加载错误信息

// ===== AI 检查引导（使用共享状态） =====
const showGuide = ref(true)
const sharedState = getInspectionState(recordId)
const guideTips = sharedState.guideTips
const guideFocusItems = sharedState.guideFocusItems

// ===== 离线同步 =====
const {
  isOnline,
  pendingCount: offlinePendingCount,
  syncing: offlineSyncing,
  syncProgress: offlineSyncProgress,
  conflictCount: offlineConflictCount,
  trySyncNow,
  saveOfflineIssue,
  saveOfflineQualified,
  deleteOfflineQualified,
  refreshPendingCount,
  setIdReplacedCallback,
  setQualifiedSyncedCallback
} = useOfflineSync(recordId)

const issueForm = ref({
  description: '',
  severity: '一般',
  location: '',
  photos: []
})

// 保存所有弹窗实例以便在 onUnmounted 中关闭
let imagePreviewInstance = null
let dialogInstance = null

const checkedCount = computed(() =>
  items.value.filter(i => i.status === 'checked' || i.status === 'skipped').length
)

const pendingCount = computed(() =>
  items.value.filter(i => i.status === 'pending').length
)

const issueCount = computed(() =>
  items.value.filter(i => i.has_issue).length
)

const progress = computed(() => {
  if (!items.value.length) return 0
  return Math.round((checkedCount.value / items.value.length) * 100)
})

const filteredItems = computed(() => {
  let list = items.value
  // 搜索过滤
  if (searchKeyword.value.trim()) {
    const kw = searchKeyword.value.trim().toLowerCase()
    list = list.filter(i =>
      i.item_name?.toLowerCase().includes(kw) ||
      i.item_id?.toLowerCase().includes(kw) ||
      i.check_method?.toLowerCase().includes(kw)
    )
  }
  // 状态过滤
  if (filterStatus.value === 1) {
    list = list.filter(i => i.status === 'pending')
  } else if (filterStatus.value === 2) {
    list = list.filter(i => i.status === 'checked' || i.status === 'skipped')
  } else if (filterStatus.value === 3) {
    list = list.filter(i => i.has_issue)
  }
  return list
})

const getItemClass = (item) => ({
  'item-qualified': item.status === 'checked' && item.qualified && !item.has_issue,
  'item-issue': item.has_issue,
  'item-skipped': item.status === 'skipped'
})

// 从后端加载照片并转为 blob URL
const loadPhotoBlob = async (photoId) => {
  try {
    const token = getAuthToken()
    const resp = await fetch(`/api/v1/records/photos/${photoId}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!resp.ok) return null
    const blob = await resp.blob()
    return URL.createObjectURL(blob)
  } catch (e) {
    console.error('加载照片失败', e)
    return null
  }
}

// 异步并行加载所有已有问题的照片
const loadAllPhotoBlobs = async () => {
  const tasks = []
  for (const item of items.value) {
    for (const issue of item.issues || []) {
      for (const photo of issue.photos || []) {
        if (!photo.blobUrl && photo.photo_id) {
          tasks.push(loadPhotoBlob(photo.photo_id).then(blobUrl => {
            if (blobUrl) photo.blobUrl = blobUrl
          }))
        }
      }
    }
  }
  await Promise.all(tasks)
}

const previewPhoto = (issue, photo) => {
  const urls = (issue.photos || [])
    .filter(p => p.blobUrl)
    .map(p => p.blobUrl)
  if (urls.length === 0) return
  const startPosition = Math.max(0, issue.photos.findIndex(p => p.photo_id === photo.photo_id))
  // 使用 base64 关闭图标，确保不依赖外部字体/CDN
  const closeIcon = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='18' y1='6' x2='6' y2='18'/%3E%3Cline x1='6' y1='6' x2='18' y2='18'/%3E%3C/svg%3E"
  imagePreviewInstance = showImagePreview({
    images: urls,
    startPosition,
    closeable: true,
    closeIcon,
    closeIconPosition: 'top-right'
  })
}

const fetchRecord = async () => {
  loading.value = true
  fetchError.value = null
  console.log('[Inspection] fetchRecord start, recordId:', recordId)

  // 优先从共享状态恢复（从巡检卡片模式切换过来时直接用内存数据）
  try {
    const shared = getInspectionState(recordId)
    if (shared.loaded.value && shared.items.value.length > 0) {
      items.value = shared.items.value
      taskId.value = shared.taskId.value
      moduleName.value = shared.moduleName.value
      isCompleted.value = shared.isCompleted.value
      loading.value = false
      // 共享状态恢复时：如果引导数据还没加载过，则加载
      if (guideTips.value.length === 0 && taskId.value && moduleName.value) {
        loadGuideTips(taskId.value, moduleName.value)
      }
      console.log('[Inspection] restored from shared state, items:', items.value.length)
      return
    }
  } catch (e) {
    console.error('[Inspection] shared state restore error:', e)
    // Continue to API fetch
  }

  try {
    const data = await getRecordDetail(recordId)
    taskId.value = data.task_id
    moduleName.value = data.module_name
    projectName.value = data.project_name || ''
    projectAddress.value = data.project_address || ''
    isCompleted.value = data.status === 'completed'
    console.log('[Inspection] getRecordDetail OK:', data.record_id, 'module:', data.module_name, 'standard_type:', data.standard_type)

    const templateRes = await getModuleTemplate(data.module_name, data.standard_type || 'diecheng')
    const templateItems = templateRes.items || []
    console.log('[Inspection] getModuleTemplate OK:', 'total:', templateRes.total, 'items:', templateItems.length)

    if (templateItems.length === 0) {
      fetchError.value = `模板加载结果为空（模块: ${data.module_name}, 标准: ${data.standard_type || 'diecheng'}），请检查模板文件`
      loading.value = false
      return
    }

    // 立即解除loading，让页面可交互
    loading.value = false

    const persistedStatuses = data.item_statuses || {}
    const issues = data.issues || {}

    items.value = templateItems.map(item => {
      const ps = persistedStatuses[item.item_id] || null
      const itemIssues = issues[item.item_id] || []
      const hasIssue = itemIssues.length > 0

      let status = 'pending'
      let qualified = false
      let checked = false

      if (ps) {
        status = ps.status || 'pending'
        qualified = ps.qualified !== false
        checked = status === 'checked' || status === 'skipped'
      } else if (hasIssue) {
        status = 'checked'
        qualified = false
        checked = true
      }

      return {
        ...item,
        status,
        qualified,
        has_issue: hasIssue,
        issues: hasIssue ? itemIssues : [],
        checked,
        saving: false
      }
    })

    // 异步加载照片
    loadAllPhotoBlobs()

    // 异步加载 AI 检查引导（不阻塞主流程）
    loadGuideTips(data.task_id, data.module_name)

    // 合并 IndexedDB 中的离线待同步数据
    try {
      const { getPendingOps } = await import('../../utils/offlineDB')
      const pendingOps = await getPendingOps(recordId)
      for (const op of pendingOps) {
        if (op.status === 'synced' || op.status === 'conflict') continue
        const existingItem = items.value.find(i => i.item_id === op.item_id)
        if (!existingItem) continue

        if (op.op_type === 'qualified') {
          // 离线合格项
          existingItem.status = 'checked'
          existingItem.qualified = true
          existingItem.checked = true
          existingItem.isOffline = true
        } else {
          // 离线问题项
          const offlinePhotos = []
          for (const photo of op.photos || []) {
            const blob = new Blob([photo.data], { type: photo.type })
            offlinePhotos.push({
              photo_id: `TMP-PHO-${op.temp_issue_id}`,
              blobUrl: URL.createObjectURL(blob),
              isOffline: true
            })
          }
          existingItem.status = 'checked'
          existingItem.has_issue = true
          existingItem.qualified = false
          existingItem.checked = true
          existingItem.isOffline = true
          existingItem.issues = [{
            issue_id: op.temp_issue_id,
            description: op.description,
            severity: op.severity,
            photos: offlinePhotos,
            isOffline: true
          }]
        }
      }
    } catch (e) {
      console.error('[Inspection] 合并离线数据失败:', e)
    }
  } catch (e) {
    console.error('[Inspection] fetchRecord error:', e)
    fetchError.value = `加载失败: ${e.message || e}. recordId=${recordId}`
    loading.value = false
  } finally {
    loading.value = false
  }
}

// 加载 AI 检查引导（写入共享状态，两种模式共用）
let _guideLoading = false
let _guideProjectId = null

const loadGuideTips = async (tid, modName) => {
  if (_guideLoading) return
  // 已有数据则跳过（避免重复加载）
  if (guideTips.value.length > 0) return
  _guideLoading = true
  try {
    if (!_guideProjectId) {
      const taskData = await getTaskDetail(tid)
      _guideProjectId = taskData.project_id
    }
    if (!_guideProjectId) return

    const data = await getFocusItems(_guideProjectId, modName)
    // 写入共享状态，列表模式和巡检模式都能读到
    guideTips.value = data.tips || []
    guideFocusItems.value = data.focus_items || []
  } catch (e) {
    console.log('AI引导加载失败（不影响检查流程）:', e)
  } finally {
    _guideLoading = false
  }
}

// 点击引导项滚动到对应检查项
const scrollToItem = (itemId) => {
  expandedId.value = itemId
  const el = document.querySelector(`[data-item-id="${itemId}"]`)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

// 卡片直按：标记合格（复用勾选逻辑）
const markQualified = (item) => {
  if (isCompleted.value) return
  if (item.has_issue) {
    showToast('该项已记录问题，请先删除问题再标合格')
    return
  }
  item.checked = !item.checked
  onCheckToggle(item)
}

// 卡片直按：有问题（展开问题表单）
const markIssue = (item) => {
  if (isCompleted.value) return
  expandedId.value = expandedId.value === item.item_id ? null : item.item_id
}

const onCheckToggle = async (item) => {
  if (isCompleted.value) return

  if (item.checked) {
    // 标记合格
    item.status = 'checked'
    item.qualified = true

    if (!navigator.onLine) {
      // 离线：保存到 IndexedDB
      try {
        await saveOfflineQualified({ item_id: item.item_id, item_name: item.item_name })
        item.isOffline = true
        showToast('已保存到本地（离线模式）')
      } catch (e) {
        item.status = 'pending'
        item.qualified = false
        item.checked = false
        showToast('本地保存失败')
      }
      return
    }

    try {
      await updateItemStatus(recordId, item.item_id, { status: 'checked' })
    } catch (e) {
      if (!e.response) {
        // 网络异常 → 回退到离线保存
        try {
          await saveOfflineQualified({ item_id: item.item_id, item_name: item.item_name })
          item.isOffline = true
          showToast('网络异常，已保存到本地')
        } catch (dbError) {
          item.status = 'pending'
          item.qualified = false
          item.checked = false
          showToast('保存失败')
        }
      } else {
        item.status = 'pending'
        item.qualified = false
        item.checked = false
        showToast('保存失败')
      }
    }
  } else {
    // 取消合格
    if (item.isOffline) {
      // 离线标记的合格项 → 从 IndexedDB 删除
      try {
        await deleteOfflineQualified(item.item_id)
      } catch (e) {
        console.error('删除离线合格记录失败:', e)
      }
    }
    item.status = 'pending'
    item.qualified = false
    item.isOffline = false
  }
}

const markAllQualified = async () => {
  try {
    if (dialogInstance) {
      dialogInstance.close()
    }
    dialogInstance = showConfirmDialog({ title: '确认', message: `将剩余 ${pendingCount.value} 项全部标记为合格？` })
    await dialogInstance
  } catch { return }

  const count = pendingCount.value
  const pendingItems = items.value.filter(i => i.status === 'pending')

  if (!navigator.onLine) {
    // 离线：逐项保存到 IndexedDB
    for (const item of pendingItems) {
      try {
        await saveOfflineQualified({ item_id: item.item_id, item_name: item.item_name })
        item.status = 'checked'
        item.qualified = true
        item.checked = true
        item.isOffline = true
      } catch (e) {
        console.error('离线保存合格失败:', item.item_name, e)
      }
    }
    showSuccessToast(`已标记 ${count} 项合格（离线模式）`)
    scheduleCleanup()
    return
  }

  try {
    await batchUpdateItems(recordId, { item_ids: [], status: 'checked' })
    pendingItems.forEach(item => {
      item.status = 'checked'
      item.qualified = true
      item.checked = true
    })
    showSuccessToast(`已标记 ${count} 项合格`)
    scheduleCleanup()
    // 在线提交成功后，同步积压的离线数据
    trySyncNow()
  } catch (e) {
    if (!e.response) {
      // 网络异常 → 回退到离线保存
      for (const item of pendingItems) {
        try {
          await saveOfflineQualified({ item_id: item.item_id, item_name: item.item_name })
          item.status = 'checked'
          item.qualified = true
          item.checked = true
          item.isOffline = true
        } catch (dbError) {
          console.error('离线保存合格失败:', item.item_name, dbError)
        }
      }
      showSuccessToast(`已标记 ${count} 项合格（离线模式）`)
    } else {
      showToast('操作失败')
    }
  }
}

const onPhotoAdded = (photoData) => {
  if (issueForm.value.photos.length >= 5) {
    showToast('最多上传5张照片')
    return
  }
  issueForm.value.photos.push(photoData)
}

const toggleExpand = (item) => {
  if (expandedId.value === item.item_id) {
    expandedId.value = null
    editIssueId.value = null
  } else {
    issueForm.value = {
      description: '',
      severity: '一般',
      location: '',
      photos: []
    }
    editIssueId.value = null
    expandedId.value = item.item_id
  }
}

const startEditIssue = (issue) => {
  editIssueId.value = issue.issue_id
  issueForm.value = {
    description: issue.description || '',
    severity: issue.severity || '一般',
    location: issue.location || '',
    photos: (issue.photos || []).map(p => ({
      url: p.blobUrl,
      photo_id: p.photo_id,
      isExisting: true
    }))
  }
}

const cancelEdit = () => {
  editIssueId.value = null
  issueForm.value = { description: '', severity: '一般', location: '', photos: [] }
}

const saveEditIssue = async (item, issue) => {
  if (!issueForm.value.description.trim()) {
    showToast('请填写问题描述')
    return
  }
  item.saving = true
  try {
    // 1. 更新问题描述
    await updateIssue(recordId, issue.issue_id, {
      description: issueForm.value.description,
      severity: issueForm.value.severity
    })

    // 2. 并行上传新照片
    const uploadTasks = issueForm.value.photos
      .filter(p => p.file)
      .map(async (photo) => {
        try {
          const photoRes = await uploadPhoto(recordId, issue.issue_id, photo.file, photo.metadata || {})
          return {
            photo_id: photoRes.photo_id,
            file_path: photoRes.file_path,
            blobUrl: URL.createObjectURL(photo.file)
          }
        } catch (e) {
          console.error('上传照片失败', e)
          return null
        }
      })
    const uploadedNew = (await Promise.all(uploadTasks)).filter(Boolean)
    const existingPhotos = issueForm.value.photos
      .filter(p => p.isExisting)
      .map(p => ({ photo_id: p.photo_id, blobUrl: p.url }))
    const newPhotos = [...existingPhotos, ...uploadedNew]

    // 3. 更新本地状态
    issue.description = issueForm.value.description
    issue.severity = issueForm.value.severity
    issue.photos = newPhotos
    editIssueId.value = null
    showSuccessToast('修改已保存')
  } catch (e) {
    showToast(e.response?.data?.detail || '修改失败')
  } finally {
    item.saving = false
  }
}

const onDeleteIssue = async (item, issue) => {
  try {
    if (dialogInstance) {
      dialogInstance.close()
    }
    dialogInstance = showConfirmDialog({ title: '确认', message: '确定删除该问题？相关照片也会一并删除。' })
    await dialogInstance
  } catch { return }

  try {
    await deleteIssue(recordId, issue.issue_id)
    // 恢复检查项为待检查状态
    item.status = 'pending'
    item.has_issue = false
    item.qualified = false
    item.checked = false
    item.issues = []
    editIssueId.value = null
    showSuccessToast('问题已删除')
  } catch (e) {
    showToast(e.response?.data?.detail || '删除失败')
  }
}

const submitIssue = async (item) => {
  if (!issueForm.value.description.trim()) {
    closeToast()
    showToast('请填写问题描述')
    return
  }

  item.saving = true
  try {
    // ===== 离线路径 =====
    if (!navigator.onLine) {
      const tempId = await saveOfflineIssue({
        item_id: item.item_id,
        item_name: item.item_name,
        description: issueForm.value.description,
        severity: issueForm.value.severity,
        photos: issueForm.value.photos,
        item_status: 'checked'
      })

      // 即时更新 UI（临时 ID + blob URL）
      const offlinePhotos = []
      for (const photo of issueForm.value.photos) {
        if (photo.file) {
          offlinePhotos.push({
            photo_id: `TMP-PHO-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
            blobUrl: URL.createObjectURL(photo.file),
            isOffline: true
          })
        }
      }

      item.status = 'checked'
      item.has_issue = true
      item.qualified = false
      item.checked = true
      item.isOffline = true
      item.issues = [{
        issue_id: tempId,
        description: issueForm.value.description,
        severity: issueForm.value.severity,
        photos: offlinePhotos,
        isOffline: true
      }]
      expandedId.value = null
      closeToast()
      showSuccessToast('已保存到本地（离线模式）')
      scheduleCleanup()
      return
    }

    // ===== 在线路径（原有逻辑不变） =====
    // 1. 创建问题（仅调用一次 createIssue）
    const issueRes = await createIssue(recordId, {
      item_id: item.item_id,
      item_name: item.item_name,
      description: issueForm.value.description,
      severity: issueForm.value.severity
    })

    // 2. 并行上传所有照片
    const photoTasks = issueForm.value.photos
      .filter(p => p.file)
      .map(async (photo) => {
        try {
          const photoRes = await uploadPhoto(recordId, issueRes.issue_id, photo.file, photo.metadata || {})
          return {
            photo_id: photoRes.photo_id,
            file_path: photoRes.file_path,
            blobUrl: URL.createObjectURL(photo.file)
          }
        } catch (e) {
          console.error('上传照片失败', e)
          return null
        }
      })
    const uploadedPhotos = (await Promise.all(photoTasks)).filter(Boolean)

    // 3. 更新检查项状态（不传 issue_description，避免后端重复创建 Issue）
    await updateItemStatus(recordId, item.item_id, { status: 'checked' })

    // 4. 更新本地状态
    item.status = 'checked'
    item.has_issue = true
    item.qualified = false
    item.checked = true
    item.issues = [{
      issue_id: issueRes.issue_id,
      description: issueForm.value.description,
      severity: issueForm.value.severity,
      photos: uploadedPhotos
    }]
    expandedId.value = null
    closeToast()
    showSuccessToast('问题已记录')
    scheduleCleanup()

    // 提交问题后刷新 AI 引导（可能发现新问题需要调整建议）
    loadGuideTips(taskId.value, moduleName.value)

    // 在线提交成功后，检查是否有积压的离线数据需要同步
    trySyncNow()
  } catch (e) {
    // 网络错误 → 尝试离线保存
    if (!e.response) {
      try {
        const tempId = await saveOfflineIssue({
          item_id: item.item_id,
          item_name: item.item_name,
          description: issueForm.value.description,
          severity: issueForm.value.severity,
          photos: issueForm.value.photos,
          item_status: 'checked'
        })

        const offlinePhotos = []
        for (const photo of issueForm.value.photos) {
          if (photo.file) {
            offlinePhotos.push({
              photo_id: `TMP-PHO-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
              blobUrl: URL.createObjectURL(photo.file),
              isOffline: true
            })
          }
        }

        item.status = 'checked'
        item.has_issue = true
        item.qualified = false
        item.checked = true
        item.isOffline = true
        item.issues = [{
          issue_id: tempId,
          description: issueForm.value.description,
          severity: issueForm.value.severity,
          photos: offlinePhotos,
          isOffline: true
        }]
        expandedId.value = null
        showSuccessToast('已保存到本地（离线模式）')
        scheduleCleanup()
        return
      } catch (dbError) {
        console.error('离线保存也失败:', dbError)
        showToast('本地存储空间不足，请清理浏览器缓存或连接网络后重试')
        scheduleCleanup()
        return
      }
    }
    showToast(e.response?.data?.detail || '保存失败')
    scheduleCleanup()
  } finally {
    item.saving = false
  }
}

const completeInspection = async () => {
  if (completing.value) return  // 防止重复点击

  // 检查是否所有检查项都已完成
  const uncheckedItems = items.value.filter(i => i.status === 'pending')
  if (uncheckedItems.length > 0) {
    const itemList = uncheckedItems.map((item, idx) => `${idx + 1}. ${item.item_name}`).join('\n')
    try {
      if (dialogInstance) {
        dialogInstance.close()
      }
      dialogInstance = showConfirmDialog({
        title: '检查未完成',
        message: `以下 ${uncheckedItems.length} 项检查尚未完成，请继续检查：\n\n${itemList}`,
        confirmButtonText: '我知道了',
        showCancelButton: false
      })
      await dialogInstance
    } catch { /* ignore */ }
    return
  }

  // 检查是否有未同步的离线数据
  if (offlinePendingCount.value > 0) {
    try {
      if (dialogInstance) {
        dialogInstance.close()
      }
      dialogInstance = showConfirmDialog({
        title: '提示',
        message: `还有 ${offlinePendingCount.value} 条离线记录未同步到服务器。网络恢复后可自动同步。\n\n确认完成检查？`
      })
      await dialogInstance
    } catch { return }
  }

  completing.value = true
  try {
    const res = await completeRecord(recordId)
    completing.value = false
    if (res.all_modules_done) {
      showSuccessToast('所有模块检查完成，AI评分已自动启动')
    } else {
      showSuccessToast('模块检查完成')
    }
    // 清除共享状态（异步，不阻塞）
    import('../../utils/inspectionState').then(m => m.clearInspectionState(recordId))
    // 延迟跳转，给 Toast 留出动画时间；不再强制 closeToast() 打断动画
    setTimeout(() => {
      router.replace(`/task/${taskId.value}`)
    }, 300)
    // 2.5s 后兜底清理残留遮罩
    scheduleCleanup()
  } catch (e) {
    completing.value = false
    if (!e.response) {
      showToast('无网络连接，无法完成检查。请连接网络后重试')
    } else {
      const detail = e.response?.data?.detail
      if (detail) {
        showToast(detail.length > 50 ? detail.substring(0, 50) + '...' : detail)
      } else {
        showToast('提交失败')
      }
    }
  }
}

const onBack = () => {
  import('../../utils/inspectionState').then(m => m.clearInspectionState(recordId))
  router.back()
}

const switchToCardMode = () => {
  // 切换前保存当前状态到共享层，确保卡片模式能读取最新数据
  const shared = getInspectionState(recordId)
  shared.items.value = items.value
  shared.taskId.value = taskId.value
  shared.moduleName.value = moduleName.value
  shared.isCompleted.value = isCompleted.value
  shared.loaded.value = true
  router.replace(`/inspection-card/${recordId}`)
}

// ===== ID 替换回调：同步成功后替换临时ID为服务器ID =====
setIdReplacedCallback((tempIssueId, realIssueId, photoIds) => {
  for (const item of items.value) {
    if (!item.issues) continue
    for (const issue of item.issues) {
      if (issue.issue_id === tempIssueId) {
        issue.issue_id = realIssueId
        issue.isOffline = false
        // 替换照片ID
        if (photoIds.length > 0 && issue.photos) {
          for (let i = 0; i < issue.photos.length && i < photoIds.length; i++) {
            issue.photos[i].photo_id = photoIds[i]
            issue.photos[i].isOffline = false
          }
        }
      }
    }
    // 如果 item 的离线标记也关联这个 tempId，清除
    if (item.isOffline && item.issues?.some(i => i.issue_id === realIssueId)) {
      item.isOffline = false
    }
  }
})

// ===== 合格项同步完成回调 =====
setQualifiedSyncedCallback((itemId) => {
  const item = items.value.find(i => i.item_id === itemId)
  if (item) {
    item.isOffline = false
  }
})

onMounted(() => fetchRecord())

onUnmounted(() => {
  // 使用 Vant API 正确关闭弹窗，避免破坏 Vant 内部单例状态
  closeToast()
  forceOverlayCleanup()
  if (imagePreviewInstance) {
    imagePreviewInstance.close()
    imagePreviewInstance = null
  }
  if (dialogInstance) {
    dialogInstance.close()
    dialogInstance = null
  }
})
</script>

<style scoped>
/* AI 检查引导 */
.guide-section {
  margin: 8px 12px;
  background: linear-gradient(135deg, var(--blue-bg), var(--ok-bg));
  border-radius: 10px;
  border: 1px solid #bfdbfe;
  overflow: hidden;
}
.guide-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
}
.guide-title {
  font-size: 13px;
  font-weight: 600;
  color: #0c7168;
}
.guide-content {
  padding: 0 12px 10px;
  border-top: 1px solid #dbeafe;
}
.guide-tip {
  margin-top: 8px;
  font-size: 12px;
  color: #374151;
}
.guide-tag {
  margin-right: 4px;
  vertical-align: middle;
}
.guide-msg {
  vertical-align: middle;
  font-size: 12px;
}
.guide-items {
  margin-top: 4px;
  padding-left: 8px;
}
.guide-item-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 0;
  font-size: 11px;
  color: #6b7280;
}
.guide-item-id {
  color: var(--blue);
  font-weight: 500;
  min-width: 60px;
}
.guide-item-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.guide-focus {
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed #d1d5db;
}
.guide-focus-title {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 4px;
}
.guide-focus-item {
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  margin: 2px 4px 2px 0;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  color: #1f2937;
  cursor: pointer;
}
.guide-focus-item:active {
  background: var(--blue-bg);
}

.fetch-error-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  text-align: center;
}
.fetch-error-msg {
  margin-top: 8px;
  font-size: 13px;
  color: var(--err);
  line-height: 1.5;
  word-break: break-all;
}

.inspection-page {
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

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 20px 20px;
}

/* 渐变顶部 */
.header-info {
  position: relative;
  overflow: hidden;
}

.header-bg {
  position: absolute;
  inset: 0;
  background: var(--blue);
}

.header-content {
  position: relative;
  padding: 16px;
  color: #fff;
}

.progress-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.progress-label {
  font-size: 13px;
  opacity: 0.85;
}

.progress-pct {
  font-size: 20px;
  font-weight: 700;
}

.action-row {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.items-list {
  padding: 12px 14px 8px;
}

/* ===== 检查项卡（原型 .m-card 形态：编号chip + 名称 + 合格/有问题按钮） ===== */
.chk-card {
  background: var(--bg-card);
  border: 1px solid var(--ink-200);
  border-radius: 12px;
  margin-bottom: 10px;
  padding: 13px 14px;
  overflow: hidden;
}

.chk-card.item-issue {
  border-color: var(--err-border);
}

.chk-head {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  cursor: pointer;
}

.chk-id {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 700;
  font-family: var(--mono);
  color: var(--brand-ink);
  background: var(--blue-bg);
  border-radius: 5px;
  padding: 2px 6px;
  margin-top: 1px;
}

.chk-info {
  flex: 1;
  min-width: 0;
}

.chk-name {
  font-size: 14.5px;
  font-weight: 700;
  color: var(--ink-900);
  line-height: 1.45;
}

.chk-method {
  font-size: 12px;
  color: var(--ink-500);
  margin-top: 3px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 合格 / 有问题（原型 m-check-btn） */
.m-check-row {
  display: flex;
  gap: 8px;
  margin-top: 11px;
}

.m-check-btn {
  flex: 1;
  height: 38px;
  border-radius: var(--r);
  border: 1px solid var(--ink-200);
  background: var(--bg-card);
  font-family: var(--sans);
  font-size: 14px;
  font-weight: 600;
  color: var(--ink-600);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.12s;
}

.m-check-btn:active { transform: scale(0.98); }

.m-check-btn.pass.on {
  background: var(--ok-bg);
  border-color: #b9e2cc;
  color: var(--ok-strong);
}

.m-check-btn.fail.on {
  background: var(--err-bg);
  border-color: #f6c6c8;
  color: var(--err-strong);
}

/* 检查标准详情 */
.standard-section {
  padding: 0 14px 12px;
  border-top: 1px solid #f0f0f0;
  background: #fafbfc;
}

.standard-card {
  background: #fff;
  border-radius: 8px;
  padding: 12px;
  margin-top: 10px;
  border: 1px solid #eee;
}

.standard-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--blue);
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #f0f0f0;
}

.standard-text {
  font-size: 14px;
  color: #333;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-all;
}

.standard-meta {
  font-size: 12px;
  color: #666;
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed #eee;
  line-height: 1.6;
}

.standard-label {
  color: #9ba3af;
}

.issue-form, .issue-display {
  padding: 0 14px 14px;
  border-top: 1px solid #f0f0f0;
  background: #fafbfc;
  border-radius: 0 0 10px 10px;
}

.issue-form .van-field {
  margin-top: 8px;
}

.issue-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 10px;
}

.existing-issue {
  padding: 10px 0;
}

.issue-severity-tag {
  margin-bottom: 6px;
}

.issue-desc-label {
  font-size: 12px;
  color: #9ba3af;
  margin-bottom: 4px;
}

.issue-desc-text {
  font-size: 14px;
  color: #333;
  line-height: 1.5;
  background: #fff;
  padding: 8px 10px;
  border-radius: 6px;
  border: 1px solid #eee;
}

.issue-photos-label {
  font-size: 12px;
  color: #9ba3af;
  margin: 10px 0 6px;
}

.photo-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.photo-loading {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #9ba3af;
  background: #f5f5f5;
  border-radius: 4px;
}

.bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 10px 14px calc(10px + env(safe-area-inset-bottom));
  background: var(--bg-card);
  border-top: 1px solid var(--ink-200);
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 12px;
}

.bb-info {
  font-size: 12.5px;
  color: var(--ink-500);
  line-height: 1.5;
  white-space: nowrap;
}

.bb-info b {
  color: var(--ink-900);
  font-variant-numeric: tabular-nums;
}

.bb-issues {
  display: block;
  color: var(--err-strong);
  font-weight: 600;
}

.bb-btn {
  flex: 1;
  height: 42px;
  font-weight: 700;
}
</style>
