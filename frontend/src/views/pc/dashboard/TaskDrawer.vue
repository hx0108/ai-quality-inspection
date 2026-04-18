<template>
  <el-drawer v-model="drawerVisible" title="检查任务列表" size="60%" :destroy-on-close="true" @close="$emit('update:visible', false)">
    <div class="drawer-filter">
      <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 140px" @change="loadTaskList">
        <el-option label="全部" value="" />
        <el-option label="待开始" value="pending" />
        <el-option label="进行中" value="in_progress" />
        <el-option label="已完成" value="completed" />
      </el-select>
      <el-select v-model="projectFilter" placeholder="项目筛选" clearable style="width: 160px; margin-left: 10px" @change="loadTaskList">
        <el-option v-for="p in allProjects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-button style="margin-left:auto" @click="$emit('export')">
        <el-icon style="margin-right:4px"><Download /></el-icon>导出
      </el-button>
    </div>
    <el-table :data="list" stripe size="small" v-loading="loading" class="drawer-table">
      <el-table-column prop="task_id" label="任务编号" width="110">
        <template #default="{ row }">{{ row.task_id?.substring(0, 8) }}</template>
      </el-table-column>
      <el-table-column prop="project_name" label="项目名称" />
      <el-table-column prop="check_date" label="检查日期" width="110" align="center" />
      <el-table-column prop="status" label="状态" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)" size="small">{{ getStatusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="total_score" label="总分" width="80" align="center">
        <template #default="{ row }">
          <span v-if="row.total_score != null" :class="getScoreClass(row.total_score)">{{ row.total_score }}</span>
          <span v-else class="text-muted">-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="70" align="center">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="$emit('go-to-task', row.task_id)">查看</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div v-if="total > list.length" class="drawer-pagination">
      <el-pagination small layout="prev, pager, next" :total="total" :page-size="pageSize" v-model:current-page="page" @current-change="loadTaskList" />
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { getTasks } from '../../../api/tasks'

const props = defineProps({
  visible: Boolean,
  allProjects: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:visible', 'go-to-task', 'export'])

const drawerVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const statusFilter = ref('')
const projectFilter = ref('')
const loading = ref(false)

function getStatusType(s) {
  return { pending: 'info', in_progress: '', completed: 'success' }[s] || 'info'
}
function getStatusText(s) {
  return { pending: '待开始', in_progress: '进行中', completed: '已完成' }[s] || s
}
function getScoreClass(score) {
  if (score == null) return ''
  if (score >= 90) return 'score-excellent'
  if (score >= 80) return 'score-good'
  if (score >= 70) return 'score-fair'
  return 'score-poor'
}

const loadTaskList = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (statusFilter.value) params.status = statusFilter.value
    if (projectFilter.value) params.project_id = projectFilter.value
    const res = await getTasks(params)
    list.value = res.items || []
    total.value = res.total || 0
  } catch (e) {
    console.error('加载任务列表失败:', e)
  } finally {
    loading.value = false
  }
}

watch(() => props.visible, (v) => {
  if (v) loadTaskList()
})

defineExpose({ list, loadTaskList })
</script>
