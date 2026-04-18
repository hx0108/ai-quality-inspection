<template>
  <div class="card-inspection-page">
    <van-nav-bar :title="moduleName" left-arrow @click-left="onBack">
      <template #right>
        <van-icon name="orders-o" size="18" @click="switchToListMode" title="切换列表模式" />
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

    <!-- 顶部进度 -->
    <div class="progress-header">
      <div class="progress-info">
        <span class="progress-count">{{ checkedCount }} / {{ items.length }} 已检查</span>
        <span class="progress-pct">{{ progress }}%</span>
      </div>
      <van-progress :percentage="progress" stroke-width="6" :show-pivot="false" color="#2563eb" />
    </div>

    <!-- 加载中 -->
    <van-loading v-if="loading && !fetchError" class="loading-center" />

    <!-- 加载错误提示 -->
    <div v-if="fetchError" class="fetch-error-box">
      <van-icon name="warning-o" size="24" color="#dc2626" />
      <div class="fetch-error-msg">{{ fetchError }}</div>
      <van-button type="primary" size="small" @click="fetchRecord" style="margin-top: 8px;">重新加载</van-button>
    </div>

    <!-- 卡片容器 -->
    <div v-else-if="currentItem" class="card-container">
      <div class="item-card" :class="cardClass">
        <!-- 卡片头部：编号 + 状态 -->
        <div class="card-top">
          <span class="card-index">{{ currentIndex + 1 }} / {{ items.length }}</span>
          <van-tag v-if="currentItem.status === 'checked' && currentItem.qualified && !currentItem.has_issue" type="success" size="medium">✅ 已合格</van-tag>
          <van-tag v-else-if="currentItem.has_issue" type="danger" size="medium">❌ 有问题</van-tag>
          <van-tag v-else type="warning" size="medium">待检查</van-tag>
        </div>

        <!-- 检查项名称 -->
        <h2 class="item-name">{{ currentItem.item_name }}</h2>

        <!-- 检查标准 -->
        <div class="standard-box">
          <div class="standard-label">检查标准</div>
          <div class="standard-text">{{ currentItem.check_standard }}</div>
          <div v-if="currentItem.check_method" class="method-row">
            <span class="method-label">检查方法：</span>{{ currentItem.check_method }}
          </div>
          <div v-if="currentItem.scoring_rule" class="method-row">
            <span class="method-label">评分规则：</span>{{ currentItem.scoring_rule }}
          </div>
        </div>

        <!-- AI 检查提示（可折叠） -->
        <div v-if="cardGuideTip || _guideModuleTips.length > 0" class="card-guide-section">
          <div class="card-guide-header" @click="showCardGuide = !showCardGuide">
            <span class="card-guide-title">AI 检查建议</span>
            <van-icon :name="showCardGuide ? 'arrow-up' : 'arrow-down'" size="14" />
          </div>
          <div v-if="showCardGuide" class="card-guide-area">
            <!-- 模块级提示（与列表模式完全一致） -->
            <div v-for="(tip, idx) in _guideModuleTips" :key="idx" class="card-guide-tip">
              <van-tag :type="tip.type === 'recurring' ? 'danger' : tip.type === 'last_check' ? 'warning' : 'primary'" size="small" class="card-guide-tag">
                {{ tip.type === 'recurring' ? '反复出现' : tip.type === 'last_check' ? '上次扣分' : tip.type === 'cross_project' ? '共性问题' : '重点关注' }}
              </van-tag>
              <span class="card-guide-text">{{ tip.message }}</span>
              <div v-if="tip.items && tip.items.length" class="card-guide-items">
                <div v-for="(gi, giIdx) in tip.items.slice(0, 3)" :key="giIdx" class="card-guide-item-row">
                  <span v-if="gi.item_id" class="card-guide-item-id">{{ gi.item_id }}</span>
                  <span class="card-guide-item-text">{{ gi.content || gi.item_name || gi.item_id }}</span>
                  <van-tag v-if="gi.last_score" size="small" type="danger">{{ gi.last_score }}分</van-tag>
                </div>
              </div>
            </div>
            <!-- 当前检查项的重点提示 -->
            <div v-if="cardGuideTip" class="card-guide-tip card-guide-item-tip">
              <van-tag :type="cardGuideTip.type === 'recurring' ? 'danger' : cardGuideTip.type === 'last_check' ? 'warning' : 'primary'" size="small">
                {{ cardGuideTip.type === 'recurring' ? '反复出现' : cardGuideTip.type === 'last_check' ? '上次扣分' : '提示' }}
              </van-tag>
              <span class="card-guide-text">{{ cardGuideTip.message }}</span>
            </div>
            <!-- 重点检查项列表（与列表模式一致） -->
            <div v-if="_guideFocusItems.length > 0" class="card-guide-focus">
              <div class="card-guide-focus-title">重点检查项：</div>
              <div v-for="fi in _guideFocusItems.slice(0, 5)" :key="fi.item_id" class="card-guide-focus-item">
                {{ fi.item_id }} {{ fi.item_name }}
                <van-tag v-if="fi.priority === 'high'" size="small" type="danger">高</van-tag>
              </div>
            </div>
          </div>
        </div>

        <!-- ===== 已有问题：展示详情 ===== -->
        <div v-if="currentItem.has_issue && !showForm" class="issue-display">
          <div v-for="issue in currentItem.issues" :key="issue.issue_id" class="issue-detail">
            <div class="issue-severity">
              <van-tag :type="issue.severity === '严重' ? 'danger' : issue.severity === '轻微' ? 'default' : 'warning'" size="medium">
                {{ issue.severity || '一般' }}
              </van-tag>
            </div>
            <div class="issue-desc">{{ issue.description }}</div>
            <div v-if="issue.photos && issue.photos.length" class="issue-photos">
              <van-image
                v-for="photo in issue.photos"
                :key="photo.photo_id"
                :src="photo.blobUrl"
                width="72" height="72" fit="cover" radius="6"
                @click="previewPhoto(issue, photo)"
              >
                <template #error><div class="photo-loading">加载中</div></template>
              </van-image>
            </div>
            <div v-if="!isCompleted" class="issue-edit-bar">
              <van-button size="small" type="primary" plain @click="startEditIssue(issue)">编辑</van-button>
              <van-button size="small" type="danger" plain @click="onDeleteIssue(currentItem, issue)">删除</van-button>
            </div>
          </div>
        </div>

        <!-- ===== 问题录入表单 ===== -->
        <div v-if="showForm" class="issue-form">
          <van-field
            v-model="issueForm.description"
            rows="2"
            autosize
            type="textarea"
            label="问题描述"
            placeholder="请描述发现的问题..."
          >
            <template #button>
              <button class="voice-btn" @click="toggleVoice" :class="{ active: isListening }" :disabled="!voiceSupported">
                🎤
              </button>
            </template>
          </van-field>
          <div v-if="voiceSupported && isListening" class="voice-hint">正在录音，请说话...</div>
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
          <div class="form-actions">
            <van-button size="small" @click="cancelForm">取消</van-button>
            <van-button size="small" type="danger" @click="submitIssue" :loading="saving">保存 → 下一项</van-button>
          </div>
        </div>

        <!-- ===== 操作按钮（无问题时显示） ===== -->
        <div v-if="!currentItem.has_issue && !showForm && !isCompleted" class="action-buttons">
          <button class="btn-pass" @click="markQualified" :disabled="saving">
            <span class="btn-icon">✅</span>
            <span class="btn-text">合格</span>
          </button>
          <button class="btn-fail" @click="openForm">
            <span class="btn-icon">❌</span>
            <span class="btn-text">有问题</span>
          </button>
        </div>

        <!-- 已完成的项可重新操作 -->
        <div v-if="currentItem.qualified && !currentItem.has_issue && !showForm && !isCompleted" class="undo-bar">
          <van-button size="mini" type="default" plain @click="undoQualified(currentItem)">撤销合格</van-button>
        </div>

        <!-- ===== 导航 ===== -->
        <div class="nav-row">
          <button class="nav-btn" @click="goPrev" :disabled="currentIndex === 0">
            ← 上一项
          </button>
          <button class="nav-btn" @click="goNextPending" :disabled="checkedCount === items.length">
            下一项待检 →
          </button>
          <button class="nav-btn" @click="goNext" :disabled="currentIndex === items.length - 1">
            下一项 →
          </button>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!loading" class="empty-state">
      <van-empty description="暂无检查项" />
    </div>

    <!-- 底部完成栏 -->
    <div class="bottom-bar">
      <van-button
        :type="isCompleted ? 'success' : 'primary'"
        block
        round
        @click="completeInspection"
        :disabled="isCompleted"
        :loading="completing"
      >
        {{ isCompleted ? '检查已完成' : `完成检查 (${progress}%)` }}
      </van-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { showToast, showSuccessToast, showConfirmDialog, showImagePreview, closeToast } from 'vant'
import { getRecordDetail, createIssue, completeRecord, uploadPhoto, updateItemStatus, updateIssue, deleteIssue } from '../../api/inspection'
import { getModuleTemplate, getTaskDetail } from '../../api/tasks'
import { getFocusItems } from '../../api/guide'
import { useOfflineSync } from '../../utils/syncManager'
import { getInspectionState } from '../../utils/inspectionState'
import { forceOverlayCleanup, scheduleCleanup } from '../../utils/overlayGuard'
import OfflineBanner from '../../components/OfflineBanner.vue'
import WatermarkCamera from '../../components/WatermarkCamera.vue'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const route = useRoute()

const recordId = route.params.recordId
const authStore = useAuthStore()
const projectName = ref('')
const projectAddress = ref('')
const items = ref([])
const loading = ref(true)
const currentIndex = ref(0)
const completing = ref(false)
const moduleName = ref('')
const taskId = ref('')
const isCompleted = ref(false)
const showForm = ref(false)
const saving = ref(false)
const fetchError = ref(null) // 加载错误信息
const cardGuideTip = ref(null) // 当前卡片的AI提示
const showCardGuide = ref(true) // 可折叠控制
// 从共享状态读取引导数据（与列表模式共用）
const _sharedGuide = getInspectionState(recordId)
const _guideFocusItems = _sharedGuide.guideFocusItems
const _guideModuleTips = _sharedGuide.guideTips
let imagePreviewInstance = null
let dialogInstance = null
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

// ===== 语音输入 =====
const SpeechRecognition = typeof window !== 'undefined'
  ? (window.SpeechRecognition || window.webkitSpeechRecognition)
  : null
const voiceSupported = !!SpeechRecognition
const isListening = ref(false)
let recognition = null

if (voiceSupported) {
  recognition = new SpeechRecognition()
  recognition.lang = 'zh-CN'
  recognition.continuous = false
  recognition.interimResults = true
  recognition.onresult = (event) => {
    let transcript = ''
    for (let i = event.resultIndex; i < event.results.length; i++) {
      transcript += event.results[i][0].transcript
    }
    issueForm.value.description = issueForm.value.description.slice(0, -_pendingText.length) + transcript
    if (event.results[event.results.length - 1].isFinal) {
      _pendingText = ''
    } else {
      _pendingText = transcript
    }
  }
  recognition.onend = () => { isListening.value = false }
  recognition.onerror = () => { isListening.value = false }
}
let _pendingText = ''

const toggleVoice = () => {
  if (!voiceSupported) return
  if (isListening.value) {
    recognition.stop()
    isListening.value = false
  } else {
    _pendingText = ''
    recognition.start()
    isListening.value = true
  }
}

onUnmounted(() => {
  if (recognition && isListening.value) {
    recognition.stop()
  }
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

// ===== 计算属性 =====
const currentItem = computed(() => items.value[currentIndex.value] || null)

const checkedCount = computed(() =>
  items.value.filter(i => i.status === 'checked' || i.status === 'skipped').length
)

const progress = computed(() => {
  if (!items.value.length) return 0
  return Math.round((checkedCount.value / items.value.length) * 100)
})

const cardClass = computed(() => {
  if (!currentItem.value) return ''
  if (currentItem.value.has_issue) return 'card-issue'
  if (currentItem.value.status === 'checked' && currentItem.value.qualified) return 'card-pass'
  return ''
})

// ===== 照片加载 =====
const loadPhotoBlob = async (photoId) => {
  try {
    const token = localStorage.getItem('token')
    const resp = await fetch(`/api/v1/records/photos/${photoId}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!resp.ok) return null
    const blob = await resp.blob()
    return URL.createObjectURL(blob)
  } catch (e) {
    return null
  }
}

const loadAllPhotoBlobs = async () => {
  const tasks = []
  for (const item of items.value) {
    for (const issue of item.issues || []) {
      for (const photo of issue.photos || []) {
        if (!photo.blobUrl && photo.photo_id) {
          tasks.push(loadPhotoBlob(photo.photo_id).then(url => {
            if (url) photo.blobUrl = url
          }))
        }
      }
    }
  }
  await Promise.all(tasks)
}

const previewPhoto = (issue, photo) => {
  const urls = (issue.photos || []).filter(p => p.blobUrl).map(p => p.blobUrl)
  if (!urls.length) return
  const start = Math.max(0, issue.photos.findIndex(p => p.photo_id === photo.photo_id))
  imagePreviewInstance = showImagePreview({ images: urls, startPosition: start, closeable: true })
}

// ===== 数据加载 =====
const fetchRecord = async () => {
  loading.value = true
  fetchError.value = null
  console.log('[InspectionCard] fetchRecord start, recordId:', recordId)

  // 优先从共享状态恢复（从列表模式切换过来时直接用内存数据）
  try {
    const shared = getInspectionState(recordId)
    if (shared.items.value.length > 0) {
      items.value = shared.items.value
      taskId.value = shared.taskId.value
      moduleName.value = shared.moduleName.value
      isCompleted.value = shared.isCompleted.value
      loading.value = false
      // 定位到第一个待检项
      const firstPending = items.value.findIndex(i => i.status === 'pending')
      if (firstPending >= 0) currentIndex.value = firstPending
      // 从共享状态恢复时也需要加载 AI 引导
      if (taskId.value && moduleName.value) {
        loadCardGuideTips(taskId.value, moduleName.value)
      }
      console.log('[InspectionCard] restored from shared state, items:', items.value.length)
      return
    }
  } catch (e) {
    console.error('[InspectionCard] shared state restore error:', e)
    // Continue to API fetch
  }

  try {
    console.log('[InspectionCard] fetching record detail...')
    const data = await getRecordDetail(recordId)
    taskId.value = data.task_id
    moduleName.value = data.module_name
    projectName.value = data.project_name || ''
    projectAddress.value = data.project_address || ''
    isCompleted.value = data.status === 'completed'
    console.log('[InspectionCard] getRecordDetail OK:', data.record_id, 'module:', data.module_name, 'standard_type:', data.standard_type)

    console.log('[InspectionCard] fetching module template...')
    const templateRes = await getModuleTemplate(data.module_name, data.standard_type || 'diecheng')
    const templateItems = templateRes.items || []
    console.log('[InspectionCard] getModuleTemplate OK:', 'total:', templateRes.total, 'items:', templateItems.length)

    if (templateItems.length === 0) {
      fetchError.value = `模板加载结果为空（模块: ${data.module_name}, 标准: ${data.standard_type || 'diecheng'}），请检查模板文件`
      loading.value = false
      return
    }

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

    // 定位到第一个待检项
    const firstPending = items.value.findIndex(i => i.status === 'pending')
    if (firstPending >= 0) currentIndex.value = firstPending

    loadAllPhotoBlobs()

    // 异步加载 AI 检查引导（不阻塞主流程）
    loadCardGuideTips(data.task_id, data.module_name)

    // 合并离线数据
    try {
      const { getPendingOps } = await import('../../utils/offlineDB')
      const pendingOps = await getPendingOps(recordId)
      for (const op of pendingOps) {
        if (op.status === 'synced' || op.status === 'conflict') continue
        const existingItem = items.value.find(i => i.item_id === op.item_id)
        if (!existingItem) continue

        if (op.op_type === 'qualified') {
          existingItem.status = 'checked'
          existingItem.qualified = true
          existingItem.checked = true
          existingItem.isOffline = true
        } else {
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
      console.error('[InspectionCard] 合并离线数据失败:', e)
    }
  } catch (e) {
    console.error('[InspectionCard] fetchRecord error:', e)
    fetchError.value = `加载失败: ${e.message || e}. recordId=${recordId}`
    loading.value = false
  } finally {
    loading.value = false
  }
}

let _cardGuideProjectId = null

// 加载 AI 检查引导（写入共享状态，两种模式共用）
const loadCardGuideTips = async (tid, modName) => {
  // 已有共享数据则直接用，不重复加载
  if (_guideModuleTips.value.length > 0) {
    updateCardGuideTip()
    return
  }
  try {
    if (!_cardGuideProjectId) {
      const taskData = await getTaskDetail(tid)
      _cardGuideProjectId = taskData.project_id
    }
    if (!_cardGuideProjectId) return

    const data = await getFocusItems(_cardGuideProjectId, modName)
    // 写入共享状态
    _guideFocusItems.value = data.focus_items || []
    _guideModuleTips.value = data.tips || []
    updateCardGuideTip()
  } catch (e) {
    console.log('AI引导加载失败（不影响检查流程）:', e)
  }
}

// 根据当前检查项更新提示
const updateCardGuideTip = () => {
  const item = currentItem.value
  if (!item || _guideFocusItems.value.length === 0) {
    cardGuideTip.value = null
    return
  }
  // 查找当前项是否在重点列表中（模糊匹配：前缀或包含）
  const focus = _guideFocusItems.value.find(f => {
    if (!f.item_id || !item.item_id) return false
    return f.item_id === item.item_id ||
           f.item_id.split('-')[0] === item.item_id.split('-')[0]  // 同编号前缀
  })
  if (focus) {
    cardGuideTip.value = {
      type: focus.priority === 'high' ? 'last_check' : focus.priority === 'medium' ? 'recurring' : 'template',
      message: focus.last_score
        ? `上次检查 ${focus.last_score} 分 — ${focus.scoring_basis || '请重点关注'}`
        : `${focus.item_name || item.item_name} — 建议重点关注`
    }
  } else {
    cardGuideTip.value = null
  }
}

// ===== 操作逻辑 =====
const markQualified = async () => {
  const item = currentItem.value
  if (!item || isCompleted.value) return

  item.status = 'checked'
  item.qualified = true
  item.checked = true

  if (!navigator.onLine) {
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
    autoAdvance()
    return
  }

  try {
    await updateItemStatus(recordId, item.item_id, { status: 'checked' })
    trySyncNow()
  } catch (e) {
    if (!e.response) {
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
  autoAdvance()
}

const undoQualified = async (item) => {
  if (item.isOffline) {
    try { await deleteOfflineQualified(item.item_id) } catch (e) { /* ignore */ }
  }
  item.status = 'pending'
  item.qualified = false
  item.checked = false
  item.isOffline = false
}

const openForm = () => {
  issueForm.value = { description: '', severity: '一般', location: '', photos: [] }
  showForm.value = true
}

const onPhotoAdded = (photoData) => {
  if (issueForm.value.photos.length >= 5) {
    showToast('最多上传5张照片')
    return
  }
  issueForm.value.photos.push(photoData)
}

const cancelForm = () => {
  showForm.value = false
  if (isListening.value && recognition) {
    recognition.stop()
  }
}

const submitIssue = async () => {
  const item = currentItem.value
  if (!item) return
  if (!issueForm.value.description.trim()) {
    showToast('请填写问题描述')
    return
  }

  saving.value = true
  try {
    // 离线
    if (!navigator.onLine) {
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
      showForm.value = false
      showToast('已保存到本地（离线模式）')
      scheduleCleanup()
      autoAdvance()
      return
    }

    // 在线：创建问题
    const issueRes = await createIssue(recordId, {
      item_id: item.item_id,
      item_name: item.item_name,
      description: issueForm.value.description,
      severity: issueForm.value.severity
    })

    // 并行上传照片
    const photoTasks = issueForm.value.photos
      .filter(p => p.file)
      .map(async (photo) => {
        try {
          const photoRes = await uploadPhoto(recordId, issueRes.issue_id, photo.file, photo.metadata || {})
          return { photo_id: photoRes.photo_id, file_path: photoRes.file_path, blobUrl: URL.createObjectURL(photo.file) }
        } catch (e) {
          console.error('上传照片失败', e)
          return null
        }
      })
    const uploadedPhotos = (await Promise.all(photoTasks)).filter(Boolean)

    // 更新检查项状态
    await updateItemStatus(recordId, item.item_id, { status: 'checked' })

    // 更新本地状态
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
    showForm.value = false
    closeToast()
    showToast('问题已记录')
    scheduleCleanup()
    trySyncNow()
    autoAdvance()
  } catch (e) {
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
        item.status = 'checked'
        item.has_issue = true
        item.qualified = false
        item.checked = true
        item.isOffline = true
        item.issues = [{
          issue_id: tempId,
          description: issueForm.value.description,
          severity: issueForm.value.severity,
          photos: [],
          isOffline: true
        }]
        showForm.value = false
        showToast('网络异常，已保存到本地')
        scheduleCleanup()
        autoAdvance()
      } catch (dbError) {
        showToast('保存失败')
        scheduleCleanup()
      }
    } else {
      showToast(e.response?.data?.detail || '保存失败')
      scheduleCleanup()
    }
  } finally {
    saving.value = false
  }
}

const startEditIssue = (issue) => {
  issueForm.value = {
    description: issue.description || '',
    severity: issue.severity || '一般',
    location: '',
    photos: (issue.photos || []).map(p => ({ url: p.blobUrl, photo_id: p.photo_id, isExisting: true }))
  }
  showForm.value = true
}

const onDeleteIssue = async (item, issue) => {
  try {
    if (dialogInstance) {
      dialogInstance.close()
    }
    dialogInstance = showConfirmDialog({ title: '确认删除', message: '删除该问题及其所有照片？' })
    await dialogInstance
  } catch { return }

  try {
    await deleteIssue(recordId, issue.issue_id)
    item.has_issue = false
    item.qualified = true
    item.issues = []
    showToast('已删除')
  } catch (e) {
    showToast('删除失败')
  }
}

// ===== 自动跳转到下一个待检项 =====
const autoAdvance = () => {
  // 找当前位置之后的第一个待检项
  for (let i = currentIndex.value + 1; i < items.value.length; i++) {
    if (items.value[i].status === 'pending') {
      currentIndex.value = i
      return
    }
  }
  // 如果后面没有，从头找
  for (let i = 0; i < currentIndex.value; i++) {
    if (items.value[i].status === 'pending') {
      currentIndex.value = i
      return
    }
  }
  // 全部完成，不跳转
}

const goPrev = () => {
  if (currentIndex.value > 0) {
    currentIndex.value--
    showForm.value = false
  }
}

const goNext = () => {
  if (currentIndex.value < items.value.length - 1) {
    currentIndex.value++
    showForm.value = false
  }
}

const goNextPending = () => {
  for (let i = currentIndex.value + 1; i < items.value.length; i++) {
    if (items.value[i].status === 'pending') {
      currentIndex.value = i
      showForm.value = false
      return
    }
  }
  for (let i = 0; i < currentIndex.value; i++) {
    if (items.value[i].status === 'pending') {
      currentIndex.value = i
      showForm.value = false
      return
    }
  }
  showToast('所有检查项已完成')
}

// ===== 完成检查 =====
const completeInspection = async () => {
  if (completing.value) return

  const uncheckedItems = items.value.filter(i => i.status === 'pending')
  if (uncheckedItems.length > 0) {
    const itemList = uncheckedItems.map((item, idx) => `${idx + 1}. ${item.item_name}`).join('\n')
    try {
      if (dialogInstance) {
        dialogInstance.close()
      }
      dialogInstance = showConfirmDialog({
        title: '检查未完成',
        message: `以下 ${uncheckedItems.length} 项尚未完成：\n\n${itemList}`,
        confirmButtonText: '我知道了',
        showCancelButton: false
      })
      await dialogInstance
    } catch { /* ignore */ }
    // 跳转到第一个未完成项
    const idx = items.value.findIndex(i => i.status === 'pending')
    if (idx >= 0) currentIndex.value = idx
    return
  }

  if (offlinePendingCount.value > 0) {
    try {
      if (dialogInstance) {
        dialogInstance.close()
      }
      dialogInstance = showConfirmDialog({
        title: '提示',
        message: `还有 ${offlinePendingCount.value} 条离线记录未同步。确认完成检查？`
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
      showToast('无网络连接，无法完成检查')
    } else {
      const detail = e.response?.data?.detail
      showToast(detail?.length > 50 ? detail.substring(0, 50) + '...' : (detail || '提交失败'))
    }
  }
}

const onBack = () => {
  import('../../utils/inspectionState').then(m => m.clearInspectionState(recordId))
  router.back()
}

const switchToListMode = () => {
  // 切换前保存当前状态到共享层
  const shared = getInspectionState(recordId)
  shared.items.value = JSON.parse(JSON.stringify(items.value))
  shared.taskId.value = taskId.value
  shared.moduleName.value = moduleName.value
  shared.isCompleted.value = isCompleted.value
  shared.loaded.value = true
  router.replace(`/inspection/${recordId}`)
}

// ===== ID 替换回调 =====
setIdReplacedCallback((tempIssueId, realIssueId, photoIds) => {
  for (const item of items.value) {
    if (!item.issues) continue
    for (const issue of item.issues) {
      if (issue.issue_id === tempIssueId) {
        issue.issue_id = realIssueId
        issue.isOffline = false
        if (photoIds.length > 0 && issue.photos) {
          for (let i = 0; i < issue.photos.length && i < photoIds.length; i++) {
            issue.photos[i].photo_id = photoIds[i]
            issue.photos[i].isOffline = false
          }
        }
      }
    }
    if (item.isOffline && item.issues?.some(i => i.issue_id === realIssueId)) {
      item.isOffline = false
    }
  }
})

setQualifiedSyncedCallback((itemId) => {
  const item = items.value.find(i => i.item_id === itemId)
  if (item) item.isOffline = false
})

// 当检查项切换时，更新AI提示
watch(currentIndex, () => {
  updateCardGuideTip()
})

onMounted(() => fetchRecord())
</script>

<style scoped>
/* AI 卡片引导提示（可折叠） */
.card-guide-section {
  margin: 8px 12px 0;
  background: linear-gradient(135deg, #eff6ff, #f0fdf4);
  border-radius: 10px;
  border: 1px solid #bfdbfe;
  overflow: hidden;
}
.card-guide-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
}
.card-guide-title {
  font-size: 13px;
  font-weight: 600;
  color: #1d4ed8;
}
.card-guide-area {
  padding: 0 10px 10px;
  border-top: 1px solid #dbeafe;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.card-guide-tip {
  margin-top: 8px;
  font-size: 12px;
  color: #374151;
}
.card-guide-tag {
  margin-right: 4px;
  vertical-align: middle;
}
.card-guide-text {
  vertical-align: middle;
  font-size: 12px;
}
.card-guide-item-tip {
  background: linear-gradient(135deg, #fef3c7, #fef9c3);
  color: #92400e;
  border: 1px solid #fde68a;
  padding: 6px 10px;
  border-radius: 8px;
  margin-top: 8px;
  display: flex;
  align-items: flex-start;
  gap: 6px;
}
.card-guide-items {
  margin-top: 4px;
  padding-left: 8px;
}
.card-guide-item-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 0;
  font-size: 11px;
  color: #6b7280;
}
.card-guide-item-id {
  color: #2563eb;
  font-weight: 500;
  min-width: 60px;
}
.card-guide-item-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-guide-focus {
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed #d1d5db;
}
.card-guide-focus-title {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 4px;
}
.card-guide-focus-item {
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  margin: 2px 4px 2px 0;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  color: #1f2937;
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
  color: #dc2626;
  line-height: 1.5;
  word-break: break-all;
}

.card-inspection-page {
  min-height: 100vh;
  background: #f0f2f5;
  padding-bottom: 80px;
  display: flex;
  flex-direction: column;
}

.loading-center {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 50vh;
}

/* 进度头部 */
.progress-header {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  padding: 14px 16px;
  color: #fff;
}
.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
}
.progress-count { font-size: 13px; opacity: 0.85; }
.progress-pct { font-size: 22px; font-weight: 700; }

/* 卡片容器 */
.card-container {
  flex: 1;
  padding: 12px;
}

.item-card {
  background: #fff;
  border-radius: 14px;
  padding: 20px 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  transition: border-color 0.2s;
}
.item-card.card-pass { border-left: 5px solid #059669; }
.item-card.card-issue { border-left: 5px solid #dc2626; }

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.card-index {
  font-size: 13px;
  color: #9ba3af;
  font-weight: 500;
}

.item-name {
  font-size: 20px;
  font-weight: 700;
  color: #1a1d26;
  margin: 0 0 14px 0;
  line-height: 1.4;
}

/* 检查标准 */
.standard-box {
  background: #f8fafc;
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 16px;
  border: 1px solid #e2e8f0;
}
.standard-label {
  font-size: 12px;
  color: #2563eb;
  font-weight: 600;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.standard-text {
  font-size: 14px;
  color: #334155;
  line-height: 1.6;
  margin-bottom: 8px;
}
.method-row {
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
}
.method-label {
  color: #475569;
  font-weight: 500;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.btn-pass, .btn-fail {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 16px 8px;
  border-radius: 12px;
  border: 2px solid;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-pass {
  background: #ecfdf5;
  border-color: #059669;
  color: #059669;
}
.btn-pass:active { background: #d1fae5; }
.btn-fail {
  background: #fef2f2;
  border-color: #dc2626;
  color: #dc2626;
}
.btn-fail:active { background: #fee2e2; }
.btn-icon { font-size: 24px; }
.btn-text { font-size: 14px; }

/* 撤销 */
.undo-bar {
  display: flex;
  justify-content: center;
  margin-bottom: 12px;
}

/* 问题展示 */
.issue-display {
  background: #fef2f2;
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 16px;
}
.issue-detail { margin-bottom: 8px; }
.issue-severity { margin-bottom: 4px; }
.issue-desc {
  font-size: 14px;
  color: #1a1d26;
  line-height: 1.5;
  margin-bottom: 8px;
}
.issue-photos {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.issue-edit-bar {
  display: flex;
  gap: 8px;
}
.photo-loading {
  width: 72px;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
  font-size: 12px;
  color: #999;
  border-radius: 6px;
}

/* 问题表单 */
.issue-form {
  background: #fff8f8;
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 16px;
  border: 1px solid #fecaca;
}
.issue-form :deep(.van-field) {
  padding: 8px 0;
}
.issue-form :deep(.van-field__label) {
  width: 5em;
  font-size: 13px;
}
.voice-btn {
  background: none;
  border: 1px solid #ddd;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}
.voice-btn.active {
  background: #2563eb;
  border-color: #2563eb;
}
.voice-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
.voice-hint {
  font-size: 12px;
  color: #2563eb;
  text-align: center;
  padding: 4px 0;
  animation: pulse 1.5s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}

/* 导航 */
.nav-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}
.nav-btn {
  flex: 1;
  padding: 8px 4px;
  background: #f5f7fa;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  color: #475569;
  cursor: pointer;
  transition: all 0.15s;
}
.nav-btn:active { background: #e2e8f0; }
.nav-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 底部栏 */
.bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 10px 16px;
  background: #fff;
  border-top: 1px solid #e5e7eb;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.04);
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 50vh;
}
</style>
