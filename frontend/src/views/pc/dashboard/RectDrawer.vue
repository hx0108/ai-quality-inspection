<template>
  <el-drawer v-model="drawerVisible" title="整改记录列表" size="65%" :destroy-on-close="true" @close="$emit('update:visible', false)">
    <div class="drawer-filter">
      <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 130px" @change="loadRectList">
        <el-option label="全部" value="" />
        <el-option label="待整改" value="pending" />
        <el-option label="已提交" value="submitted" />
        <el-option label="已通过" value="approved" />
        <el-option label="已驳回" value="rejected" />
      </el-select>
      <el-input v-model="keyword" placeholder="搜索关键词..." clearable style="width: 200px; margin-left: 10px" @clear="loadRectList" @keyup.enter="loadRectList" />
      <el-button style="margin-left:auto" @click="$emit('export')">
        <el-icon style="margin-right:4px"><Download /></el-icon>导出
      </el-button>
    </div>
    <el-table :data="list" stripe size="small" v-loading="loading" row-key="rectification_id" class="drawer-table">
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="issue-expand">
            <div class="expand-row"><span class="expand-label">问题描述：</span>{{ row.description }}</div>
            <div class="expand-row" v-if="row.location"><span class="expand-label">问题位置：</span>{{ row.location }}</div>
            <div class="expand-row" v-if="row.issue_photos && row.issue_photos.length">
              <span class="expand-label">问题照片：</span>
              <div class="expand-photos">
                <el-image v-for="photo in row.issue_photos" :key="photo.photo_id || photo" :src="getPhotoUrl(photo)" :preview-src-list="row.issue_photos.map(p => getPhotoUrl(p))" fit="cover" style="width: 72px; height: 72px; border-radius: 4px; margin-right: 6px" />
              </div>
            </div>
            <div class="expand-row" v-if="row.rectification_photos && row.rectification_photos.length">
              <span class="expand-label">整改照片：</span>
              <div class="expand-photos">
                <el-image v-for="photo in row.rectification_photos" :key="photo.photo_id || photo" :src="getPhotoUrl(photo)" :preview-src-list="row.rectification_photos.map(p => getPhotoUrl(p))" fit="cover" style="width: 72px; height: 72px; border-radius: 4px; margin-right: 6px" />
              </div>
            </div>
            <div class="expand-row" v-if="row.rectification_note">
              <span class="expand-label">整改说明：</span>{{ row.rectification_note }}
            </div>
            <div class="expand-row" v-if="row.ai_result">
              <span class="expand-label">AI核查：</span>
              <el-tag :type="row.ai_result === 'pass' ? 'success' : 'danger'" size="small">{{ row.ai_result === 'pass' ? '通过' : '未通过' }}</el-tag>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="project_name" label="项目" width="120" />
      <el-table-column prop="module_name" label="模块" width="100" />
      <el-table-column prop="item_name" label="检查项" width="130" />
      <el-table-column prop="description" label="问题描述" show-overflow-tooltip />
      <el-table-column prop="severity" label="严重程度" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="row.severity === '严重' ? 'danger' : row.severity === '轻微' ? 'info' : 'warning'" size="small">{{ row.severity }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="getRectStatusType(row.status)" size="small">{{ getRectStatusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
    </el-table>
  </el-drawer>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { getAllRectifications } from '../../../api/rectification'

const props = defineProps({
  visible: Boolean
})

const emit = defineEmits(['update:visible', 'export'])

const drawerVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

const list = ref([])
const loading = ref(false)
const statusFilter = ref('')
const keyword = ref('')

function getRectStatusType(s) {
  return { pending: 'warning', submitted: '', ai_approved: 'success', ai_rejected: 'danger', approved: 'success', rejected: 'danger' }[s] || 'info'
}
function getRectStatusText(s) {
  return { pending: '待整改', submitted: '已提交', ai_approved: 'AI通过', ai_rejected: 'AI驳回', approved: '已通过', rejected: '已驳回' }[s] || s
}
function getPhotoUrl(photo) {
  if (typeof photo === 'string') return `/api/v1/records/photos/${photo}`
  const pid = photo.photo_id || photo.file_path?.split('/')?.pop()?.split('.')[0]
  return pid ? `/api/v1/records/photos/${pid}` : ''
}

const loadRectList = async () => {
  loading.value = true
  try {
    const params = { page_size: 200 }
    if (statusFilter.value) params.status = statusFilter.value
    const res = await getAllRectifications(params)
    list.value = res.items || []
  } catch (e) {
    console.error('加载整改列表失败:', e)
  } finally {
    loading.value = false
  }
}

watch(() => props.visible, (v) => {
  if (v) loadRectList()
})

defineExpose({ list })
</script>
