<template>
  <div class="pc-page">
    <div class="tasks-content">
          <!-- 操作栏 -->
          <el-card shadow="never" class="toolbar">
            <el-row :gutter="20" align="middle">
              <el-col :span="4">
                <el-select v-model="filterStatus" placeholder="状态筛选" clearable>
                  <el-option label="待检查" value="pending" />
                  <el-option label="进行中" value="in_progress" />
                  <el-option label="已完成" value="completed" />
                </el-select>
              </el-col>
              <el-col :span="4">
                <el-button type="primary" @click="showCreateDialog = true">
                  <el-icon><Plus /></el-icon> 创建任务
                </el-button>
              </el-col>
            </el-row>
          </el-card>
          
          <!-- 任务列表 -->
          <el-card shadow="never" class="task-list">
            <el-table :data="filteredTasks" style="width: 100%" v-loading="loading">
              <el-table-column prop="task_id" label="任务编号" width="150" />
              <el-table-column prop="project_name" label="项目名称" />
              <el-table-column prop="check_date" label="检查日期" width="120" />
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="getStatusType(row.status)">{{ getStatusName(row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="total_score" label="得分" width="100">
                <template #default="{ row }">
                  <span v-if="row.total_score !== null">{{ row.total_score.toFixed(1) }}</span>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="创建时间" width="180">
                <template #default="{ row }">
                  {{ formatDate(row.created_at) }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="200" fixed="right">
                <template #default="{ row }">
                  <el-button type="primary" link @click="viewTask(row)">查看</el-button>
                  <el-button type="primary" link @click="generateTaskReport(row)" v-if="row.status === 'completed'">
                    生成报告
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
    </div>

    <!-- 创建任务对话框 -->
    <el-dialog v-model="showCreateDialog" title="创建检查任务" width="600px">
      <el-form :model="taskForm" label-width="100px">
        <el-form-item label="选择项目" required>
          <el-select v-model="taskForm.project_id" placeholder="请选择项目" style="width: 100%">
            <el-option 
              v-for="project in projects" 
              :key="project.id" 
              :label="project.name" 
              :value="project.id" 
            />
          </el-select>
        </el-form-item>
        <el-form-item label="检查日期" required>
          <el-date-picker 
            v-model="taskForm.inspection_date" 
            type="date" 
            placeholder="选择日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="分配检查员">
          <div class="assignment-list">
            <div v-for="(assign, index) in taskForm.assignments" :key="index" class="assignment-item">
              <el-select v-model="assign.module_id" placeholder="选择模块" style="width: 200px">
                <el-option 
                  v-for="module in modules" 
                  :key="module.module_id" 
                  :label="module.module_name" 
                  :value="module.module_id" 
                />
              </el-select>
              <el-input v-model="assign.user_name" placeholder="检查员" style="width: 150px; margin-left: 10px;" disabled />
              <el-button type="danger" link @click="removeAssignment(index)" style="margin-left: 10px;">删除</el-button>
            </div>
            <el-button type="primary" link @click="addAssignment">+ 添加分配</el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createTask" :loading="creating">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../../stores/auth'
import { getTasks, createTask as createTaskApi, getProjects } from '../../api/tasks'
import { getModules } from '../../api/inspection'
import { generateReport } from '../../api/report'

const router = useRouter()
const authStore = useAuthStore()

const activeMenu = computed(() => router.currentRoute.value.path)
const loading = ref(false)
const tasks = ref([])
const projects = ref([])
const modules = ref([])
const filterStatus = ref('')

const showCreateDialog = ref(false)
const creating = ref(false)
const taskForm = ref({
  project_id: null as number | null,
  inspection_date: '',
  assignments: [] as Array<{ module_id: number | null; user_id: number; user_name: string; module_name: string }>
})

const filteredTasks = computed(() => {
  if (!filterStatus.value) return tasks.value
  return tasks.value.filter(t => t.status === filterStatus.value)
})

const getStatusName = (status: string) => {
  const names: Record<string, string> = {
    pending: '待检查',
    in_progress: '进行中',
    completed: '已完成'
  }
  return names[status] || status
}

const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    pending: 'warning',
    in_progress: '',
    completed: 'success'
  }
  return types[status] || 'info'
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

const handleCommand = (command: string) => {
  if (command === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}

const viewTask = (task) => {
  router.push(`/pc/report/${task.id}`)
}

const generateTaskReport = async (task) => {
  try {
    await generateReport(task.id)
    ElMessage.success('报告生成成功')
  } catch (error) {
    ElMessage.error('报告生成失败')
  }
}

const addAssignment = () => {
  taskForm.value.assignments.push({
    module_id: null,
    user_id: authStore.user?.id || 1,
    user_name: authStore.user?.real_name || '',
    module_name: ''
  })
}

const removeAssignment = (index: number) => {
  taskForm.value.assignments.splice(index, 1)
}

const createTask = async () => {
  if (!taskForm.value.project_id) {
    ElMessage.warning('请选择项目')
    return
  }
  if (!taskForm.value.inspection_date) {
    ElMessage.warning('请选择检查日期')
    return
  }
  
  creating.value = true
  try {
    const dateStr = typeof taskForm.value.inspection_date === 'string' 
      ? taskForm.value.inspection_date 
      : new Date(taskForm.value.inspection_date).toISOString().split('T')[0]
    
    const assignments = taskForm.value.assignments.length > 0 
      ? taskForm.value.assignments.filter(a => a.module_id).map(a => ({
          user_id: a.user_id,
          module_id: a.module_id!,
          module_name: modules.value.find(m => m.module_id === a.module_id)?.module_name || ''
        }))
      : modules.value.slice(0, 3).map(m => ({
          user_id: authStore.user?.id || 1,
          module_id: m.module_id,
          module_name: m.module_name
        }))
    
    await createTaskApi({
      project_id: taskForm.value.project_id,
      inspection_date: dateStr,
      assignments: assignments
    })
    ElMessage.success('任务创建成功')
    showCreateDialog.value = false
    taskForm.value = {
      project_id: null,
      inspection_date: '',
      assignments: []
    }
    loadTasks()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '任务创建失败')
  } finally {
    creating.value = false
  }
}

const loadTasks = async () => {
  loading.value = true
  try {
    const res = await getTasks()
    tasks.value = res.items || []
  } catch (error) {
    console.error('加载任务失败', error)
  } finally {
    loading.value = false
  }
}

const loadProjects = async () => {
  try {
    const res = await getProjects()
    projects.value = res.items || []
  } catch (error) {
    console.error('加载项目失败', error)
  }
}

const loadModules = async () => {
  try {
    modules.value = await getModules()
  } catch (error) {
    console.error('加载模块失败', error)
  }
}

onMounted(() => {
  loadTasks()
  loadProjects()
  loadModules()
})
</script>

<style scoped>
.sidebar {
  background: #304156;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #263445;
}

.logo h1 {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
}

.sidebar-menu {
  border-right: none;
  background: transparent;
}

.header {
  background: #fff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.user-name {
  font-size: 14px;
  color: #333;
}

.main-content {
  background: #f5f5f5;
  padding: 20px;
}

.toolbar {
  margin-bottom: 20px;
}

.task-list {
  margin-bottom: 20px;
}

.assignment-list {
  width: 100%;
}

.assignment-item {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}
</style>
