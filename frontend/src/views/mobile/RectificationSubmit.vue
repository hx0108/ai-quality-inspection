<template>
  <div class="submit-page">
    <van-nav-bar title="提交整改" left-arrow @click-left="$router.back()" />

    <div v-if="loading" class="loading-center">
      <van-loading size="24px">加载中...</van-loading>
    </div>

    <div v-else-if="detail" class="submit-content">
      <!-- 原问题信息 -->
      <div class="section">
        <div class="section-title">原问题信息</div>
        <div class="info-card">
          <div class="info-row">
            <span class="label">项目：</span>
            <span>{{ detail.project_name }}</span>
          </div>
          <div class="info-row">
            <span class="label">模块：</span>
            <span>{{ detail.module_name }}</span>
          </div>
          <div class="info-row">
            <span class="label">检查项：</span>
            <span>{{ detail.item_name || detail.item_id }}</span>
          </div>
          <div class="info-row">
            <span class="label">问题描述：</span>
            <span>{{ detail.description }}</span>
          </div>
          <div class="info-row">
            <span class="label">严重程度：</span>
            <van-tag :type="detail.severity === '严重' ? 'danger' : 'warning'" size="small">
              {{ detail.severity }}
            </van-tag>
          </div>
          <div v-if="detail.location" class="info-row">
            <span class="label">位置：</span>
            <span>{{ detail.location }}</span>
          </div>
        </div>

        <!-- 原问题照片 -->
        <div v-if="detail.issue_photos && detail.issue_photos.length" class="photo-section">
          <div class="photo-label">原问题照片</div>
          <div class="photo-grid">
            <van-image
              v-for="p in detail.issue_photos"
              :key="p.photo_id"
              width="80"
              height="80"
              radius="6"
              fit="cover"
              :src="getPhotoUrlSync(p.photo_id)"
              @click="getPhotoUrlSync(p.photo_id) && previewPhoto(getPhotoUrlSync(p.photo_id))"
            >
              <template #error>
                <div class="photo-loading">加载中...</div>
              </template>
            </van-image>
          </div>
        </div>
      </div>

      <!-- 驳回原因 -->
      <div v-if="detail.review_note && detail.status === 'pending'" class="section">
        <div class="reject-card">
          <van-icon name="warning-o" color="#ee0a24" size="16" />
          <span class="reject-text">驳回原因：{{ detail.review_note }}</span>
        </div>
      </div>

      <!-- AI 核查结果 -->
      <div v-if="detail.ai_result" class="section">
        <div class="section-title">
          <van-icon name="shield-o" color="#2563eb" style="margin-right: 4px" />
          AI 核查结果
        </div>
        <div class="ai-card">
          <div class="ai-verdict" :class="detail.ai_result.rectification_qualified ? 'ai-pass' : 'ai-fail'">
            <van-icon :name="detail.ai_result.rectification_qualified ? 'passed' : 'close'" />
            <span>{{ detail.ai_result.rectification_qualified ? '整改合格' : '整改不合格' }}</span>
          </div>
          <div class="ai-row">
            <span class="ai-label">置信度评分</span>
            <div class="ai-score-bar">
              <van-progress :percentage="detail.ai_result.confidence_score || 0"
                :stroke-width="8" :show-pivot="true"
                :color="(detail.ai_result.confidence_score || 0) >= 70 ? '#059669' : '#d97706'" />
            </div>
          </div>
          <div v-if="detail.ai_result.watermark_valid !== undefined" class="ai-row">
            <span class="ai-label">水印验证</span>
            <van-tag :type="detail.ai_result.watermark_valid ? 'success' : 'danger'" size="medium">
              {{ detail.ai_result.watermark_valid ? '水印有效' : '水印无效' }}
            </van-tag>
          </div>
          <div v-if="detail.ai_result.suggestion" class="ai-row">
            <span class="ai-label">AI 建议</span>
            <van-tag :type="detail.ai_result.suggestion === '通过' ? 'success' : 'danger'" size="medium">
              {{ detail.ai_result.suggestion }}
            </van-tag>
          </div>
          <div v-if="detail.ai_result.analysis" class="ai-analysis-text">
            <div class="ai-label" style="margin-bottom: 4px">分析详情</div>
            <p>{{ detail.ai_result.analysis }}</p>
          </div>
          <div v-if="detail.ai_checked_at" class="ai-time">
            AI核查时间：{{ detail.ai_checked_at.slice(0, 16).replace('T', ' ') }}
          </div>
        </div>
      </div>

      <!-- 整改照片上传（仅待整改/已驳回时可操作） -->
      <template v-if="detail.status === 'pending'">
        <div class="section">
          <div class="section-title">整改照片 <span class="required">*</span></div>
        <div class="uploader-wrap">
          <WatermarkCamera
            :current-count="fileList.length"
            :max-count="5"
            :project-name="detail.project_name || ''"
            :project-address="detail.project_address || ''"
            :inspector-name="authStore.user.real_name || ''"
            @photo-added="onWatermarkPhotoAdded"
          />
          <van-uploader
            v-model="fileList"
            :max-count="5"
            :show-upload="false"
            :before-delete="onDeletePhoto"
          />
        </div>
        <div class="upload-tip">支持水印拍摄、拍照、从相册选择（最多5张）</div>
      </div>

      <!-- 整改说明 -->
      <div class="section">
        <div class="section-title">整改说明</div>
        <van-field
          v-model="rectificationNote"
          type="textarea"
          rows="3"
          placeholder="请描述整改情况"
          maxlength="500"
          show-word-limit
        />
      </div>

      <!-- 整改时间 -->
      <div class="section">
        <div class="section-title">整改完成时间</div>
        <van-field
          v-model="rectificationTime"
          is-link
          readonly
          placeholder="选择整改完成时间"
          @click="showTimePicker = true"
        />
        <van-popup v-model:show="showTimePicker" position="bottom" round>
          <van-date-picker
            v-model="selectedDate"
            title="选择日期"
            :min-date="minDate"
            :max-date="maxDate"
            @confirm="onDateConfirm"
            @cancel="showTimePicker = false"
          />
        </van-popup>
      </div>

      <!-- 提交按钮 -->
      <div class="submit-bar">
        <van-button
          type="primary"
          block
          round
          :loading="submitting"
          :disabled="fileList.length === 0"
          @click="onSubmit"
        >
          提交整改
        </van-button>
      </div>
      </template>
    </div>

    <van-empty v-else description="整改记录不存在" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast, showSuccessToast, showImagePreview, closeToast } from 'vant'
import {
  getRectificationDetail,
  submitRectification,
  uploadRectificationPhoto,
  deleteRectificationPhoto
} from '../../api/rectification'
import WatermarkCamera from '../../components/WatermarkCamera.vue'
import { useAuthStore } from '../../stores/auth'

const route = useRoute()
const router = useRouter()
const rectificationId = route.params.id
const authStore = useAuthStore()

const loading = ref(true)
const detail = ref(null)
const fileList = ref([])
let imagePreviewInstance = null
const rectificationNote = ref('')
const rectificationTime = ref('')
const showTimePicker = ref(false)
const submitting = ref(false)
const uploadedPhotoIds = ref([])

// 日期选择
const now = new Date()
const selectedDate = ref([
  String(now.getFullYear()),
  String(now.getMonth() + 1).padStart(2, '0'),
  String(now.getDate()).padStart(2, '0')
])
const minDate = new Date(2024, 0, 1)
const maxDate = new Date()

const photoSignCache = new Map() // photoId -> {url, expires_at}

const getPhotoUrl = async (photoId) => {
  // 检查缓存是否有效
  const cached = photoSignCache.get(photoId)
  if (cached && Date.now() < cached.expires_at) {
    return cached.url
  }
  // 获取签名
  try {
    const res = await request.get(`/records/photos/${photoId}/sign`)
    const url = `/api/v1/records/photos/${photoId}?sign=${res.sign}&expires=${res.expires}`
    photoSignCache.set(photoId, { url, expires_at: (parseInt(res.expires) - 30) * 1000 })
    return url
  } catch {
    // 降级：使用 Bearer header（不暴露在URL中）
    return null
  }
}

// 照片预览用同步方式（token 参数，和 PC 端一致）
const getPhotoUrlSync = (photoId) => {
  const t = localStorage.getItem('token')
  return `/api/v1/records/photos/${photoId}?token=${t}`
}

const previewPhoto = (url) => {
  imagePreviewInstance = showImagePreview([url])
}

const onOversize = () => {
  showToast('照片大小不能超过10MB')
}

const onAfterRead = async (file) => {
  const files = Array.isArray(file) ? file : [file]
  for (const f of files) {
    f.status = 'uploading'
    try {
      const res = await uploadRectificationPhoto(rectificationId, f.file)
      f.status = 'done'
      uploadedPhotoIds.value.push(res.photo_id)
    } catch (e) {
      f.status = 'failed'
      f.message = '上传失败'
      showToast('照片上传失败')
    }
  }
}

// 水印拍摄 / 拍照 / 相册选择 — 即时上传
const onWatermarkPhotoAdded = async (photoData) => {
  const entry = { ...photoData, status: 'uploading' }
  fileList.value.push(entry)
  try {
    const res = await uploadRectificationPhoto(rectificationId, photoData.file, photoData.metadata || {})
    entry.status = 'done'
    uploadedPhotoIds.value.push(res.photo_id)
  } catch (e) {
    entry.status = 'failed'
    entry.message = '上传失败'
    showToast('照片上传失败')
  }
}

const onDeletePhoto = async (file, index) => {
  const photoId = uploadedPhotoIds.value[index]
  if (photoId) {
    try {
      await deleteRectificationPhoto(rectificationId, photoId)
      uploadedPhotoIds.value.splice(index, 1)
      return true
    } catch (e) {
      showToast('删除失败')
      return false
    }
  }
  return true
}

const onDateConfirm = ({ selectedValues }) => {
  rectificationTime.value = selectedValues.join('-')
  showTimePicker.value = false
}

const onSubmit = async () => {
  if (fileList.value.length === 0) {
    showToast('请上传至少一张整改照片')
    return
  }

  // 检查是否有上传失败的
  const hasFailed = fileList.value.some(f => f.status === 'failed')
  if (hasFailed) {
    showToast('有照片上传失败，请删除后重试')
    return
  }

  // 检查是否有正在上传的
  const uploading = fileList.value.some(f => f.status === 'uploading')
  if (uploading) {
    showToast('照片上传中，请等待')
    return
  }

  submitting.value = true
  try {
    await submitRectification(rectificationId, {
      rectification_note: rectificationNote.value,
      rectification_time: rectificationTime.value
    })
    showSuccessToast('整改已提交，AI正在核查中')
    setTimeout(() => router.back(), 1500)
  } catch (e) {
    showToast(e.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false
  }
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getRectificationDetail(rectificationId)
    detail.value = res
    // 回填已提交的数据（驳回后重新编辑）
    if (res.rectification_note) rectificationNote.value = res.rectification_note
    if (res.rectification_time) rectificationTime.value = res.rectification_time
    // 回填已有整改照片
    if (res.rectification_photos && res.rectification_photos.length) {
      fileList.value = res.rectification_photos.map(p => ({
        url: '',
        status: 'uploading',
        photo_id: p.photo_id
      }))
      uploadedPhotoIds.value = res.rectification_photos.map(p => p.photo_id)
      // 异步加载签名URL
      for (const f of fileList.value) {
        const url = await getPhotoUrl(f.photo_id)
        if (url) {
          f.url = url
          f.status = 'done'
        }
      }
    }
  } catch (e) {
    showToast('加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)

onUnmounted(() => {
  closeToast()
  if (imagePreviewInstance) {
    imagePreviewInstance.close()
    imagePreviewInstance = null
  }
})
</script>

<style scoped>
.submit-page {
  min-height: 100vh;
  background: #f5f6fa;
  padding-bottom: 100px;
}

.loading-center {
  display: flex;
  justify-content: center;
  padding: 60px 0;
}

.submit-content {
  padding: 12px;
}

.section {
  background: #fff;
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 10px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1d26;
  margin-bottom: 10px;
}

.required {
  color: #ee0a24;
}

.info-card {
  font-size: 13px;
  color: #5c6477;
}

.info-row {
  margin-bottom: 6px;
  display: flex;
  align-items: flex-start;
  gap: 4px;
}

.info-row .label {
  color: #9ba3af;
  white-space: nowrap;
}

.photo-section {
  margin-top: 10px;
}

.photo-label {
  font-size: 13px;
  color: #9ba3af;
  margin-bottom: 8px;
}

.photo-grid {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.uploader-wrap {
  margin-bottom: 4px;
}

.upload-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  border: 1px dashed #dcdfe6;
  border-radius: 8px;
  gap: 4px;
}

.upload-btn span {
  font-size: 11px;
  color: #9ba3af;
}

.upload-tip {
  font-size: 11px;
  color: #9ba3af;
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
  border-radius: 6px;
}

.reject-card {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 10px;
  background: #fff5f5;
  border-radius: 8px;
  font-size: 13px;
  color: #ee0a24;
}

/* AI 核查结果 */
.ai-card {
  font-size: 13px;
}

.ai-verdict {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  padding: 10px;
  border-radius: 8px;
  margin-bottom: 10px;
}

.ai-pass {
  background: #ecfdf5;
  color: #059669;
}

.ai-fail {
  background: #fef2f2;
  color: #dc2626;
}

.ai-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0;
}

.ai-label {
  color: #64748b;
  font-size: 13px;
}

.ai-score-bar {
  flex: 1;
  margin-left: 12px;
}

.ai-analysis-text {
  margin-top: 8px;
  padding: 8px;
  background: #f8fafc;
  border-radius: 6px;
  font-size: 13px;
  color: #475569;
  line-height: 1.5;
}

.ai-analysis-text p {
  margin: 0;
}

.ai-time {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 8px;
}

.submit-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 12px 16px;
  background: #fff;
  border-top: 1px solid #e5e7eb;
}
</style>
