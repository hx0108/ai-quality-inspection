<template>
  <div class="watermark-camera">
    <!-- 操作按钮 -->
    <div class="action-row">
      <button class="action-btn primary" @click="triggerWatermark" :disabled="loading">
        <van-loading v-if="loading" size="16" color="#fff" />
        <van-icon v-else name="photograph" size="16" />
        <span>水印拍摄</span>
      </button>
      <button class="action-btn" @click="triggerCamera" :disabled="loading">
        <van-icon name="photograph" size="16" />
        <span>拍照</span>
      </button>
      <button class="action-btn" @click="triggerAlbum" :disabled="loading">
        <van-icon name="photo-o" size="16" />
        <span>相册</span>
      </button>
    </div>

    <!-- 定位精度提示 -->
    <div v-if="locationWarning" class="location-warning">
      {{ locationWarning }}
    </div>

    <!-- 隐藏的文件输入 -->
    <input ref="watermarkInput" type="file" accept="image/*" capture="environment" style="display:none" @change="onWatermarkCapture" />
    <input ref="cameraInput" type="file" accept="image/*" capture="environment" style="display:none" @change="onDirectCapture" />
    <input ref="albumInput" type="file" accept="image/*" multiple style="display:none" @change="onAlbumSelect" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { showToast } from 'vant'
import { getFreshLocation } from '../utils/geolocation'
import { addWatermark } from '../utils/watermark'
import { signPhotoMeta } from '../utils/photoSigner'

const props = defineProps({
  maxCount: { type: Number, default: 5 },
  currentCount: { type: Number, default: 0 },
  projectName: { type: String, default: '' },
  projectAddress: { type: String, default: '' },
  inspectorName: { type: String, default: '' }
})

const emit = defineEmits(['photo-added'])

const loading = ref(false)
const locationWarning = ref('')
const watermarkInput = ref(null)
const cameraInput = ref(null)
const albumInput = ref(null)

const canAdd = (count = 1) => {
  if (props.currentCount + count > props.maxCount) {
    showToast(`最多上传${props.maxCount}张照片`)
    return false
  }
  return true
}

const triggerWatermark = () => {
  if (!canAdd()) return
  locationWarning.value = ''
  watermarkInput.value.click()
}

const triggerCamera = () => {
  if (!canAdd()) return
  cameraInput.value.click()
}

const triggerAlbum = () => {
  if (!canAdd()) return
  albumInput.value.click()
}

// 水印拍摄 — 强制刷新GPS定位，收集完整metadata
const onWatermarkCapture = async (e) => {
  const file = e.target.files?.[0]
  if (!file) return

  loading.value = true
  try {
    const captureTime = new Date()

    // 1. 强制刷新GPS定位（不走缓存）
    let latitude = null
    let longitude = null
    let address = ''
    let accuracy = null

    try {
      const loc = await getFreshLocation()
      latitude = loc.latitude
      longitude = loc.longitude
      address = loc.address
      accuracy = loc.accuracy
    } catch (err) {
      console.warn('高德定位失败:', err)
    }

    // 2. 过滤无效地址
    if (address === '定位失败' || address.match(/^\d+\.\d+,?\s*\d*\.\d*$/)) {
      address = ''
    }

    // 3. 定位精度提示
    locationWarning.value = ''
    if (accuracy !== null && accuracy > 100) {
      locationWarning.value = `定位精度 ${Math.round(accuracy)}米，建议在开阔区域拍摄`
    } else if (latitude === null) {
      locationWarning.value = '定位失败，照片将不含位置信息'
    }

    // 4. 添加水印（含水印经纬度 + 拍摄时间）
    const watermarkedBlob = await addWatermark(file, {
      projectName: props.projectName,
      address: address,
      latitude: latitude,
      longitude: longitude,
      inspectorName: props.inspectorName,
      captureTime: captureTime
    })

    // 5. 生成防篡改签名
    const meta = {
      latitude,
      longitude,
      address,
      capture_time: captureTime.toISOString(),
      inspector_name: props.inspectorName
    }
    const watermarkHash = await signPhotoMeta(meta, watermarkedBlob)
    meta.watermark_hash = watermarkHash

    // 6. 创建 File 对象
    const watermarkedFile = new File([watermarkedBlob], `watermark_${Date.now()}.jpg`, { type: 'image/jpeg' })
    const url = URL.createObjectURL(watermarkedBlob)

    // 7. 发射事件：文件 + URL + 元数据
    emit('photo-added', {
      file: watermarkedFile,
      url,
      metadata: meta
    })
  } catch (err) {
    showToast('水印拍摄失败，请重试')
  } finally {
    loading.value = false
    watermarkInput.value.value = ''
  }
}

// 普通拍照
const onDirectCapture = (e) => {
  const file = e.target.files?.[0]
  if (!file) return
  const url = URL.createObjectURL(file)
  emit('photo-added', { file, url, metadata: {} })
  cameraInput.value.value = ''
}

// 相册选择
const onAlbumSelect = (e) => {
  const files = Array.from(e.target.files || [])
  const remaining = props.maxCount - props.currentCount
  const toAdd = files.slice(0, remaining)
  if (files.length > remaining) {
    showToast(`已选择前${remaining}张，最多${props.maxCount}张`)
  }
  for (const file of toAdd) {
    const url = URL.createObjectURL(file)
    emit('photo-added', { file, url, metadata: {} })
  }
  albumInput.value.value = ''
}
</script>

<style scoped>
.watermark-camera {
  width: 100%;
}

.action-row {
  display: flex;
  gap: 8px;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  flex: 1;
  height: 36px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  background: #fff;
  color: #5c6477;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-btn.primary {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}

.action-btn:not(:disabled):active {
  transform: scale(0.97);
}

.location-warning {
  margin-top: 6px;
  padding: 6px 10px;
  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: 6px;
  font-size: 12px;
  color: #d46b08;
  line-height: 1.4;
}
</style>
