<template>
  <div class="scoring-page">
    <van-nav-bar title="AI 智能评分" left-arrow @click-left="onBack" />

    <div class="scoring-content">
      <!-- 总分卡片 -->
      <div class="total-score-card">
        <div class="total-score-bg"></div>
        <div class="total-score-body">
          <div class="total-score-label">
            项目总分
            <span class="scored-count">{{ scoredCount }}/{{ totalModuleCount }} 模块已评分</span>
          </div>
          <div class="total-score-number" :class="getScoreClass(totalScore)">
            {{ totalScore.toFixed(2) }}
          </div>
          <div class="total-score-unit">分</div>
        </div>
      </div>

      <!-- 8个模块状态列表 -->
      <div class="module-status-list">
        <div v-for="mod in moduleList" :key="mod.module_name"
          class="module-status-card"
          :class="`module-${mod.scoring_status}`"
          @click="onModuleClick(mod)"
        >
          <div class="module-status-row">
            <div class="module-info">
              <span class="module-name">{{ mod.module_name }}</span>
              <van-tag size="small" :type="getModuleTagType(mod.scoring_status)">
                {{ getModuleStatusText(mod.scoring_status) }}
              </van-tag>
            </div>
            <div class="module-score-area">
              <span v-if="mod.pct_score !== null" class="module-score" :class="getScoreClass(mod.pct_score)">
                {{ mod.pct_score.toFixed(2) }}
              </span>
              <van-loading v-else-if="mod.scoring_status === 'scoring'" size="18" color="#2563eb" />
              <span v-else class="module-score-pending">—</span>
            </div>
          </div>
          <div v-if="mod.scoring_status === 'scoring'" class="module-progress">
            <van-progress :percentage="100" :stroke-width="4" color="#2563eb" :show-pivot="false" />
            <span class="scoring-hint">AI 评分中...</span>
          </div>
          <div v-if="mod.scoring_status === 'failed'" class="module-error">
            评分失败，可点击重新评分
          </div>
        </div>
      </div>

      <!-- 模块评分明细弹窗 -->
      <van-action-sheet v-model:show="showDetail" :title="detailModuleName" class="detail-sheet">
        <div class="detail-content" v-if="detailItems.length > 0">
          <div class="detail-module-score">
            模块得分：
            <span :class="getScoreClass(detailModuleScore)">{{ detailModuleScore.toFixed(2) }}</span> 分
          </div>
          <div v-for="item in detailItems" :key="item.scoring_id" class="detail-item">
            <div class="detail-item-header">
              <div class="detail-item-name">
                {{ item.item_name }}
                <van-tag v-if="item.is_fallback" type="warning" size="small" style="margin-left:4px">系统预评分</van-tag>
              </div>
              <div class="detail-item-score" @click.stop="openEditScore(item)">
                <span :class="getItemScoreClass(item.score)">{{ Number(item.score).toFixed(2) }}</span>
                <span class="detail-item-unit">/ 5</span>
                <van-icon v-if="item.is_edited" name="edit" size="12" color="#2563eb" />
              </div>
            </div>
            <div v-if="item.is_skipped" class="detail-item-skipped">已跳过</div>
            <!-- 详细信息 -->
            <div v-if="!item.is_skipped" class="detail-item-info">
              <div v-if="item.check_standard" class="info-row">
                <span class="info-label">检查标准：</span>
                <span class="info-value">{{ item.check_standard }}</span>
              </div>
              <div v-if="item.check_method" class="info-row">
                <span class="info-label">检查方法：</span>
                <span class="info-value">{{ item.check_method }}</span>
              </div>
              <div v-if="item.scoring_rule" class="info-row">
                <span class="info-label">评分规则：</span>
                <span class="info-value">{{ item.scoring_rule }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">权重：</span>
                <span class="info-value">{{ Number(item.weight).toFixed(4) }}</span>
              </div>
              <div v-if="item.scoring_basis" class="info-row">
                <span class="info-label">评分依据：</span>
                <span class="info-value">{{ item.scoring_basis }}</span>
              </div>
              <!-- 问题点 -->
              <div v-if="item.issues && item.issues.length > 0" class="issues-section">
                <div class="info-label" style="margin-bottom: 4px;">问题点：</div>
                <div v-for="issue in item.issues" :key="issue.issue_id" class="issue-card">
                  <div class="issue-desc">
                    <van-tag v-if="issue.severity" size="small" :type="issue.severity === '严重' ? 'danger' : issue.severity === '轻微' ? 'default' : 'warning'">
                      {{ issue.severity }}
                    </van-tag>
                    <span class="issue-text">{{ issue.description }}</span>
                  </div>
                  <div v-if="issue.location" class="issue-location">
                    位置：{{ issue.location }}
                  </div>
                  <!-- 问题照片 -->
                  <div v-if="issue.photos && issue.photos.length > 0" class="issue-photos">
                    <template v-for="photo in issue.photos" :key="photo.photo_id">
                      <img v-if="!photo._error"
                        :src="`/api/v1/records/photos/${photo.photo_id}?token=${authToken}`"
                        class="issue-photo"
                        @click="previewPhoto(photo)"
                        @error="photo._error = true"
                      />
                      <div v-else class="photo-error">加载失败</div>
                    </template>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <van-empty v-else description="暂无评分数据" />
      </van-action-sheet>

      <!-- 图片预览 -->
      <van-image-preview v-model:show="showPhotoPreview" :images="previewImages" :start-position="previewIndex" />

      <!-- 编辑分数弹窗 -->
      <van-dialog v-model:show="showEditScore" title="修改评分" show-cancel-button
        :before-close="onSaveScore"
      >
        <div class="edit-form">
          <div class="edit-item-name">{{ editingItem?.item_name }}</div>
          <van-field v-model="editForm.score" type="number" label="分数" placeholder="0-5"
            :rules="[{ validator: val => val >= 0 && val <= 5, message: '分数必须在0-5之间' }]" />
          <van-field v-model="editForm.scoring_basis" rows="3" autosize type="textarea" label="评分依据" />
          <van-field label="修改原因">
            <template #input>
              <van-radio-group v-model="editForm.edit_reason" direction="horizontal">
                <van-radio name="ai_score_too_high" icon-size="14px">AI偏高</van-radio>
                <van-radio name="ai_score_too_low" icon-size="14px">AI偏低</van-radio>
                <van-radio name="fixed_on_site" icon-size="14px">已整改</van-radio>
                <van-radio name="inspection_error" icon-size="14px">记录有误</van-radio>
                <van-radio name="other" icon-size="14px">其他</van-radio>
              </van-radio-group>
            </template>
          </van-field>
        </div>
      </van-dialog>

      <!-- 底部操作 -->
      <div class="action-bar" v-if="scoredCount > 0">
        <van-button type="primary" block round @click="onExportExcel" :loading="exporting" class="export-btn">
          导出评分结果
        </van-button>
        <van-button plain block round @click="generateReport" style="margin-top: 8px;">
          生成报告
        </van-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { showToast, showSuccessToast, closeToast } from 'vant'
import { getModuleScoringStatus, getModuleDetail, editScore, rescoreModule, exportScoringExcel } from '../../api/scoring'
import { generateReport as apiGenerateReport } from '../../api/report'
import { getAuthToken } from '../../utils/authStorage'
import { usePolling } from '../../composables/usePolling'

const router = useRouter()
const route = useRoute()
const taskId = route.params.taskId
const authToken = computed(() => getAuthToken())

const moduleList = ref([])
const totalScore = ref(0)
const scoredCount = ref(0)
const totalModuleCount = ref(8)
// 统一轮询管理：自动在卸载/路由离开时清理（修复手势返回泄漏）
const { schedule: schedulePoll, stop: stopPoll } = usePolling()

// 明细弹窗
const showDetail = ref(false)
const detailModuleName = ref('')
const detailItems = ref([])
const detailModuleScore = ref(0)

// 编辑弹窗
const showEditScore = ref(false)
const editingItem = ref(null)
const editForm = ref({ score: '', scoring_basis: '', edit_reason: '' })

// 照片预览
const showPhotoPreview = ref(false)
const previewImages = ref([])
const previewIndex = ref(0)

// 导出
const exporting = ref(false)

// 所有模块的评分结果缓存
const resultsCache = ref({})

const onModuleClick = async (mod) => {
  if (mod.scoring_status === 'completed') {
    detailModuleName.value = mod.module_name
    detailModuleScore.value = mod.pct_score || 0
    // 从缓存取，或按需加载模块详情（含照片）
    if (resultsCache.value[mod.module_name] && resultsCache.value[mod.module_name].length > 0) {
      detailItems.value = resultsCache.value[mod.module_name]
    } else {
      try {
        const res = await getModuleDetail(taskId, mod.module_name)
        const items = res.items || []
        resultsCache.value[mod.module_name] = items
        detailItems.value = items
      } catch (e) {
        console.error('加载模块详情失败', e)
        detailItems.value = []
      }
    }
    showDetail.value = true
  } else if (mod.scoring_status === 'failed') {
    try {
      await rescoreModule(taskId, mod.module_name)
      showToast('重新评分已启动')
      startPolling()
    } catch (e) {
      showToast('启动重新评分失败')
    }
  } else if (mod.scoring_status === 'scoring') {
    showToast('该模块正在评分中，请稍候')
  } else if (mod.scoring_status === 'pending') {
    if (mod.inspection_status === 'completed') {
      showToast('该模块等待评分中')
    } else {
      showToast('该模块检查尚未完成')
    }
  }
}

const previewPhoto = (photo) => {
  previewImages.value = [`/api/v1/records/photos/${photo.photo_id}?token=${authToken.value}`]
  previewIndex.value = 0
  showPhotoPreview.value = true
}

const openEditScore = (item) => {
  editingItem.value = item
  editForm.value = {
    score: String(Number(item.score).toFixed(2)),
    scoring_basis: item.scoring_basis || '',
    edit_reason: ''
  }
  showEditScore.value = true
}

const onSaveScore = async (action) => {
  if (action === 'cancel') return true
  const score = parseFloat(editForm.value.score)
  if (isNaN(score) || score < 0 || score > 5) {
    showToast('分数必须在0-5之间')
    return false
  }
  try {
    await editScore(editingItem.value.scoring_id, {
      score,
      scoring_basis: editForm.value.scoring_basis,
      edit_reason: editForm.value.edit_reason || undefined
    })
    // 清除模块详情缓存，强制下次重新从后端加载
    resultsCache.value = {}
    showSuccessToast('评分已更新')
    await fetchModuleStatus()
    return true
  } catch (e) {
    showToast(e.response?.data?.detail || '修改失败')
    return false
  }
}

const onExportExcel = async () => {
  exporting.value = true
  try {
    const blob = await exportScoringExcel(taskId)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `AI评分结果_${taskId}.xlsx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    showSuccessToast('导出成功')
  } catch (e) {
    showToast('导出失败')
  } finally {
    exporting.value = false
  }
}

const generateReport = async () => {
  try {
    await apiGenerateReport(taskId)
    showSuccessToast('报告生成已启动')
    // 延迟跳转，等待Toast动画完成，防止弹窗DOM残留
    await new Promise(r => setTimeout(r, 300))
    router.push(`/report/${taskId}`)
  } catch (e) {
    showToast(e.response?.data?.detail || '生成报告失败')
  }
}

const fetchModuleStatus = async () => {
  try {
    const res = await getModuleScoringStatus(taskId)
    moduleList.value = res.modules || []
    totalScore.value = res.current_total_score || 0
    scoredCount.value = res.scored_module_count || 0
    totalModuleCount.value = res.total_module_count || 8
  } catch (e) {
    console.error('获取模块状态失败', e)
  }
}


let pollingCount = 0
let pollingActive = false
const startPolling = () => {
  if (pollingActive) return
  pollingActive = true
  pollingCount = 0
  const doPoll = async () => {
    await fetchModuleStatus()
    const hasScoring = moduleList.value.some(m => m.scoring_status === 'scoring')
    if (!hasScoring) {
      pollingActive = false
      stopPoll()
      // 清空缓存，下次点击模块时重新加载
      resultsCache.value = {}
      return
    }
    // 动态间隔：前5次1秒，之后逐渐增加到4秒
    pollingCount++
    const interval = pollingCount <= 5 ? 1000 : Math.min(4000, 1000 + (pollingCount - 5) * 600)
    schedulePoll(doPoll, interval)
  }
  schedulePoll(doPoll, 1000)
}

const getModuleTagType = (status) => {
  const map = { completed: 'success', scoring: 'primary', failed: 'danger', pending: 'default' }
  return map[status] || 'default'
}

const getModuleStatusText = (status) => {
  const map = { completed: '已评分', scoring: '评分中', failed: '评分失败', pending: '待评分' }
  return map[status] || status
}

const getItemScoreClass = (score) => {
  if (Number(score) >= 5) return 'item-score-full'
  if (Number(score) >= 3) return 'item-score-warn'
  return 'item-score-low'
}

const getScoreClass = (score) => {
  if (score >= 90) return 'score-excellent'
  if (score >= 80) return 'score-good'
  if (score >= 60) return 'score-normal'
  return 'score-poor'
}

const onBack = () => router.back()

onMounted(async () => {
  await fetchModuleStatus()
  const hasScoring = moduleList.value.some(m => m.scoring_status === 'scoring')
  if (hasScoring) startPolling()
})

onUnmounted(() => {
  // 定时器清理已由 usePolling 自动处理
  // 使用 Vant API 正确关闭弹窗，避免破坏 Vant 内部单例状态
  closeToast()
})
</script>

<style scoped>
.scoring-page {
  min-height: 100vh;
  background: #f5f7fa;
  padding-bottom: 140px;
}

.scoring-content {
  padding: 12px;
}

/* 总分卡片 */
.total-score-card {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

.total-score-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
}

.total-score-body {
  position: relative;
  padding: 20px 24px;
  text-align: center;
  color: #fff;
}

.total-score-label {
  font-size: 13px;
  opacity: 0.6;
  margin-bottom: 6px;
}

.scored-count {
  font-size: 11px;
  opacity: 0.5;
  margin-left: 8px;
}

.total-score-number {
  font-size: 42px;
  font-weight: 700;
  line-height: 1.2;
}

.total-score-unit {
  font-size: 14px;
  opacity: 0.5;
  margin-top: 2px;
}

/* 模块列表 */
.module-status-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.module-status-card {
  background: #fff;
  border-radius: 10px;
  padding: 14px 16px;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.04);
  transition: transform 0.15s, box-shadow 0.15s;
  cursor: pointer;
}

.module-status-card:active {
  transform: scale(0.98);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.module-status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.module-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.module-name {
  font-size: 14px;
  font-weight: 600;
  color: #1a1d26;
}

.module-score-area {
  display: flex;
  align-items: center;
}

.module-score {
  font-size: 18px;
  font-weight: 700;
}

.module-score-pending {
  color: #9ba3af;
  font-size: 16px;
}

.module-progress {
  margin-top: 10px;
}

.scoring-hint {
  display: block;
  text-align: center;
  font-size: 12px;
  color: #2563eb;
  margin-top: 4px;
}

.module-error {
  font-size: 12px;
  color: #dc2626;
  margin-top: 6px;
}

/* 状态色条 */
.module-completed { border-left: 3px solid #059669; }
.module-scoring { border-left: 3px solid #2563eb; }
.module-failed { border-left: 3px solid #dc2626; }
.module-pending { border-left: 3px solid #9ba3af; }

/* 明细弹窗 */
.detail-content {
  padding: 0 16px 16px;
}

.detail-module-score {
  text-align: center;
  font-size: 15px;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 12px;
}

.detail-item {
  background: #fafbfc;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
  border-left: 3px solid #2563eb;
}

.detail-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-item-name {
  font-size: 13px;
  font-weight: 500;
  color: #1a1d26;
  flex: 1;
  margin-right: 8px;
  line-height: 1.4;
}

.detail-item-score {
  display: flex;
  align-items: center;
  gap: 2px;
  cursor: pointer;
}

.detail-item-unit {
  font-size: 12px;
  color: #9ba3af;
}

.detail-item-skipped {
  font-size: 12px;
  color: #9ba3af;
  margin-top: 4px;
}

/* 详细信息区域 */
.detail-item-info {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #eee;
}

.info-row {
  font-size: 12px;
  line-height: 1.6;
  margin-bottom: 2px;
  display: flex;
}

.info-label {
  color: #909399;
  white-space: nowrap;
  flex-shrink: 0;
}

.info-value {
  color: #333;
  flex: 1;
  word-break: break-all;
}

/* 问题点 */
.issues-section {
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed #e8e8e8;
}

.issue-card {
  background: #fff;
  border-radius: 6px;
  padding: 8px;
  margin-bottom: 6px;
  border-left: 2px solid #d97706;
}

.issue-desc {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 12px;
  color: #333;
  line-height: 1.5;
}

.issue-text {
  flex: 1;
}

.issue-location {
  font-size: 11px;
  color: #909399;
  margin-top: 2px;
}

.issue-photos {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.issue-photo {
  width: 60px;
  height: 60px;
  border-radius: 4px;
  object-fit: cover;
  cursor: pointer;
  border: 1px solid #eee;
}

.photo-error {
  width: 60px;
  height: 60px;
  border-radius: 4px;
  background: #fef2f2;
  color: #dc2626;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  border: 1px solid #fecaca;
}

/* 编辑表单 */
.edit-form {
  padding: 16px;
}

.edit-item-name {
  font-size: 14px;
  font-weight: 600;
  color: #1a1d26;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
}

/* 分数颜色 */
.score-excellent { color: #059669; font-weight: bold; }
.score-good { color: #2563eb; font-weight: bold; }
.score-normal { color: #d97706; font-weight: bold; }
.score-poor { color: #dc2626; font-weight: bold; }

.item-score-full { color: #059669; font-weight: bold; }
.item-score-warn { color: #d97706; font-weight: bold; }
.item-score-low { color: #dc2626; font-weight: bold; }

/* 底部操作栏 */
.action-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 12px 16px;
  background: #fff;
  box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.06);
}

.export-btn {
  background: #2563eb;
  border-color: transparent;
}
</style>
