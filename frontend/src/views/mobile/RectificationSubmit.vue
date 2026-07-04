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
        <div class="section-title">整改说明 <span class="required">*</span></div>
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
        <div class="section-title">整改完成时间 <span class="required">*</span></div>
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
            title="选择整改完成时间"
            :columns-type="['year', 'month', 'day', 'hour', 'minute']"
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
          :disabled="fileList.length === 0 || !rectificationNote.trim() || !rectificationTime"
          @click="onSubmit"
        >
          提交整改
        </van-button>
      </div>
      </template>

      <!-- 非 pending 状态：只读展示已提交的整改材料 -->
      <template v-if="detail.status !== 'pending'">
        <!-- 已提交整改照片 -->
        <div v-if="detail.rectification_photos && detail.rectification_photos.length" class="section">
          <div class="section-title">整改照片</div>
          <div class="photo-grid">
            <van-image
              v-for="p in detail.rectification_photos"
              :key="p.photo_id"
              width="80"
              height="80"
              radius="6"
              fit="cover"
              :src="getPhotoUrlSync(p.photo_id)"
              @click="previewPhoto(getPhotoUrlSync(p.photo_id))"
            >
              <template #error>
                <div class="photo-loading">加载中...</div>
              </template>
            </van-image>
          </div>
        </div>

        <!-- 整改说明 -->
        <div v-if="detail.rectification_note" class="section">
          <div class="section-title">整改说明</div>
          <div class="info-card">{{ detail.rectification_note }}</div>
        </div>

        <!-- 整改时间 -->
        <div v-if="detail.rectification_time" class="section">
          <div class="section-title">整改完成时间</div>
          <div class="info-card">{{ detail.rectification_time }}</div>
        </div>

        <!-- 审核意见 -->
        <div v-if="detail.review_note" class="section">
          <div class="section-title">审核意见</div>
          <div class="info-card">
            {{ detail.review_note }}
            <span v-if="detail.reviewer_name" class="reviewer-name">（{{ detail.reviewer_name }}）</span>
          </div>
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
import { getAuthToken } from '../../utils/authStorage'

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

// 日期选择
const now = new Date()
const selectedDate = ref([
  String(now.getFullYear()),
  String(now.getMonth() + 1).padStart(2, '0'),
  String(now.getDate()).padStart(2, '0'),
  String(now.getHours()).padStart(2, '0'),
  String(now.getMinutes()).padStart(2, '0')
])
const minDate = new Date(2024, 0, 1)
const maxDate = new Date()

// 照片预览用同步方式（token 参数，和 PC 端一致）
const getPhotoUrlSync = (photoId) => {
  const t = getAuthToken()
  return `/api/v1/records/photos/${photoId}?token=${t}`
}

const previewPhoto = (url) => {
  imagePreviewInstance = showImagePreview([url])
}

// 水印拍摄 / 拍照 / 相册选择 — 仅存本地，提交时统一上传（与巡检一致）
const onWatermarkPhotoAdded = (photoData) => {
  if (fileList.value.length >= 5) {
    showToast('最多上传5张照片')
    return
  }
  fileList.value.push({ ...photoData })
}

const onDeletePhoto = async (file, index) => {
  const entry = fileList.value[index]
  // 已上传到服务器的照片需调API删除
  if (entry.isExisting && entry.photo_id) {
    try {
      await deleteRectificationPhoto(rectificationId, entry.photo_id)
    } catch (e) {
      showToast('删除失败')
      return false
    }
  }
  fileList.value.splice(index, 1)
  return true
}

const onDateConfirm = ({ selectedValues }) => {
  const [y, m, d, h, min] = selectedValues
  rectificationTime.value = `${y}-${m}-${d} ${h}:${min}`
  showTimePicker.value = false
}

const onSubmit = async () => {
  if (fileList.value.length === 0) {
    showToast('请上传至少一张整改照片')
    return
  }
  if (!rectificationNote.value.trim()) {
    showToast('请填写整改说明')
    return
  }
  if (!rectificationTime.value) {
    showToast('请选择整改完成时间')
    return
  }

  submitting.value = true
  try {
    // 提交时统一上传新照片（已有照片跳过）
    for (const photo of fileList.value) {
      if (!photo.isExisting && photo.file) {
        await uploadRectificationPhoto(rectificationId, photo.file, photo.metadata || {})
      }
    }
    // 提交整改（触发AI核查）
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
    // 回填已有整改照片（驳回后重新编辑场景）
    if (res.rectification_photos && res.rectification_photos.length) {
      fileList.value = res.rectification_photos.map(p => ({
        url: getPhotoUrlSync(p.photo_id),
        isExisting: true,
        photo_id: p.photo_id
      }))
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

.reviewer-name {
  font-size: 12px;
  color: #9ba3af;
  margin-left: 4px;
}
</style>
