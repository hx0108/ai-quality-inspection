<template>
  <div class="pc-settings">
    <el-tabs v-model="activeTab" class="styled-tabs">
      <!-- ==================== 用户管理 ==================== -->
      <el-tab-pane label="用户管理" name="users">
        <el-card shadow="never" class="content-card">
          <div class="card-toolbar">
            <el-input v-model="userSearch" placeholder="搜索用户名/姓名/手机号" clearable style="width: 260px" />
            <el-button type="primary" @click="openUserDialog()" class="add-btn">
              <el-icon><Plus /></el-icon> 新增用户
            </el-button>
          </div>
          <el-table :data="filteredUsers" v-loading="userLoading" stripe class="styled-table">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="username" label="用户名" width="120" />
            <el-table-column prop="phone" label="手机号" width="130">
              <template #default="{ row }">{{ row.phone || '—' }}</template>
            </el-table-column>
            <el-table-column prop="real_name" label="姓名" width="120" />
            <el-table-column prop="role" label="角色" width="120">
              <template #default="{ row }">
                <el-tag :type="roleTagType(row.role)">{{ roleLabel(row.role) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="project_name" label="项目归属" min-width="120">
              <template #default="{ row }">{{ row.project_name || '—' }}</template>
            </el-table-column>
            <el-table-column prop="is_active" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'danger'">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="180">
              <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="260" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="openUserDialog(row)">编辑</el-button>
                <el-button link type="primary" size="small" @click="openResetPwdDialog(row)">重置密码</el-button>
                <el-button link :type="row.is_active ? 'warning' : 'success'" size="small" @click="toggleActive(row)">
                  {{ row.is_active ? '禁用' : '启用' }}
                </el-button>
                <el-button link type="danger" size="small" @click="onDeleteUser(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- ==================== 项目管理 ==================== -->
      <el-tab-pane label="项目管理" name="projects">
        <el-card shadow="never" class="content-card">
          <div class="card-toolbar">
            <el-input v-model="projectSearch" placeholder="搜索项目名称" clearable style="width: 240px" />
            <el-button type="primary" @click="openProjectDialog()" class="add-btn">
              <el-icon><Plus /></el-icon> 新增项目
            </el-button>
          </div>
          <el-table :data="filteredProjects" v-loading="projectLoading" stripe class="styled-table">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="name" label="项目名称" min-width="200" />
            <el-table-column prop="code" label="项目编码" width="120" />
            <el-table-column prop="address" label="项目地址" min-width="200" />
            <el-table-column prop="created_at" label="创建时间" width="180">
              <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="openProjectDialog(row)">编辑</el-button>
                <el-button size="small" type="danger" @click="onDeleteProject(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 用户编辑弹窗 -->
    <el-dialog v-model="userDialogVisible" :title="editingUser.id ? '编辑用户' : '新增用户'" width="480px" class="styled-dialog">
      <el-form :model="editingUser" label-width="80px">
        <el-form-item label="用户名" required>
          <el-input v-model="editingUser.username" :disabled="!!editingUser.id" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="editingUser.phone" placeholder="请输入手机号（用于登录）" maxlength="11" />
        </el-form-item>
        <el-form-item :label="editingUser.id ? '新密码' : '密码'" :required="!editingUser.id">
          <el-input v-model="editingUser.password" type="password" show-password
            :placeholder="editingUser.id ? '留空则不修改' : '请输入密码'" />
        </el-form-item>
        <el-form-item label="姓名" required>
          <el-input v-model="editingUser.real_name" />
        </el-form-item>
        <el-form-item label="角色" required>
          <el-select v-model="editingUser.role" style="width: 100%">
            <el-option label="系统管理员" value="admin" />
            <el-option label="检查员" value="inspector" />
            <el-option label="阵地督导" value="site_supervisor" />
            <el-option label="驻场经理" value="field_supervisor" />
            <el-option label="项目人员" value="project_staff" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目归属">
          <el-select v-model="editingUser.project_id" clearable style="width: 100%" placeholder="请选择项目（选填）">
            <el-option v-for="p in projectList" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="onSaveUser" :loading="savingUser">保存</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码弹窗 -->
    <el-dialog v-model="resetPwdVisible" title="重置密码" width="400px" class="styled-dialog">
      <el-form label-width="80px">
        <el-form-item label="用户">
          <span>{{ resetPwdUser.real_name }}（{{ resetPwdUser.username }}）</span>
        </el-form-item>
        <el-form-item label="新密码" required>
          <el-input v-model="resetPwdValue" type="password" show-password placeholder="请输入新密码（至少6位）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetPwdVisible = false">取消</el-button>
        <el-button type="primary" @click="onResetPwd" :loading="resettingPwd">确认重置</el-button>
      </template>
    </el-dialog>

    <!-- 项目编辑弹窗 -->
    <el-dialog v-model="projectDialogVisible" :title="editingProject.id ? '编辑项目' : '新增项目'" width="480px" class="styled-dialog">
      <el-form :model="editingProject" label-width="80px">
        <el-form-item label="项目名称" required>
          <el-input v-model="editingProject.name" />
        </el-form-item>
        <el-form-item label="项目编码">
          <el-input v-model="editingProject.code" />
        </el-form-item>
        <el-form-item label="项目地址">
          <el-input v-model="editingProject.address" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="projectDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="onSaveProject" :loading="savingProject">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUsers, createUser, updateUser, deleteUser } from '../../api/pc'
import { getAllProjects, createProject, updateProject, deleteProject } from '../../api/pc'

const activeTab = ref('users')

// ==================== 用户管理 ====================
const users = ref([])
const userLoading = ref(false)
const userSearch = ref('')
const userDialogVisible = ref(false)
const savingUser = ref(false)
const editingUser = ref({ username: '', password: '', real_name: '', role: 'inspector' })

const filteredUsers = computed(() => {
  if (!userSearch.value) return users.value
  const q = userSearch.value.toLowerCase()
  return users.value.filter(u =>
    u.username.toLowerCase().includes(q) || u.real_name.toLowerCase().includes(q) || (u.phone || '').includes(q)
  )
})

const fetchUsers = async () => {
  userLoading.value = true
  try {
    const res = await getUsers({ page: 1, page_size: 100 })
    users.value = res.items || []
  } catch (e) {
    ElMessage.error('获取用户列表失败')
  } finally {
    userLoading.value = false
  }
}

const openUserDialog = (user = null) => {
  if (user) {
    editingUser.value = { ...user, password: '' }
  } else {
    editingUser.value = { username: '', password: '', phone: '', real_name: '', role: 'inspector', project_id: null }
  }
  userDialogVisible.value = true
}

const onSaveUser = async () => {
  const u = editingUser.value
  if (!u.username || !u.real_name) { ElMessage.warning('请填写必填项'); return }
  savingUser.value = true
  try {
    if (u.id) {
      const data = { real_name: u.real_name, role: u.role, phone: u.phone || null, project_id: u.project_id }
      if (u.password) data.password = u.password
      await updateUser(u.id, data)
      ElMessage.success('用户更新成功')
    } else {
      if (!u.password) { ElMessage.warning('请输入密码'); savingUser.value = false; return }
      await createUser({ username: u.username, password: u.password, real_name: u.real_name, role: u.role, phone: u.phone || null, project_id: u.project_id })
      ElMessage.success('用户创建成功')
    }
    userDialogVisible.value = false
    fetchUsers()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    savingUser.value = false
  }
}

const toggleActive = async (user) => {
  try {
    await updateUser(user.id, { is_active: !user.is_active })
    ElMessage.success(user.is_active ? '已禁用' : '已启用')
    fetchUsers()
  } catch (e) { ElMessage.error('操作失败') }
}

const onDeleteUser = async (user) => {
  try {
    await ElMessageBox.confirm(`确定删除用户「${user.real_name}」？`, '确认', { type: 'warning' })
    await deleteUser(user.id)
    ElMessage.success('删除成功')
    fetchUsers()
  } catch (e) { /* cancel */ }
}

// ==================== 重置密码 ====================
const resetPwdVisible = ref(false)
const resetPwdUser = ref({})
const resetPwdValue = ref('')
const resettingPwd = ref(false)

const openResetPwdDialog = (user) => {
  resetPwdUser.value = user
  resetPwdValue.value = ''
  resetPwdVisible.value = true
}

const onResetPwd = async () => {
  if (!resetPwdValue.value || resetPwdValue.value.length < 6) {
    ElMessage.warning('密码不能少于6位')
    return
  }
  resettingPwd.value = true
  try {
    await updateUser(resetPwdUser.value.id, { password: resetPwdValue.value })
    ElMessage.success('密码重置成功')
    resetPwdVisible.value = false
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '重置失败')
  } finally {
    resettingPwd.value = false
  }
}

const roleLabel = (r) => ({ admin: '管理员', inspector: '检查员', site_supervisor: '阵地督导', field_supervisor: '驻场经理', project_staff: '项目人员' }[r] || r)
const roleTagType = (r) => ({ admin: 'danger', inspector: '', site_supervisor: 'warning', field_supervisor: 'warning', project_staff: 'info' }[r] || '')

// ==================== 项目管理 ====================
const projectList = ref([])
const projectLoading = ref(false)
const projectSearch = ref('')
const projectDialogVisible = ref(false)
const savingProject = ref(false)
const editingProject = ref({ name: '', code: '', address: '' })

const filteredProjects = computed(() => {
  if (!projectSearch.value) return projectList.value
  const q = projectSearch.value.toLowerCase()
  return projectList.value.filter(p => p.name.toLowerCase().includes(q))
})

const fetchProjects = async () => {
  projectLoading.value = true
  try {
    const res = await getAllProjects()
    projectList.value = res.items || []
  } finally {
    projectLoading.value = false
  }
}

const openProjectDialog = (project = null) => {
  if (project) {
    editingProject.value = { ...project }
  } else {
    editingProject.value = { name: '', code: '', address: '' }
  }
  projectDialogVisible.value = true
}

const onSaveProject = async () => {
  if (!editingProject.value.name) { ElMessage.warning('请填写项目名称'); return }
  savingProject.value = true
  try {
    if (editingProject.value.id) {
      await updateProject(editingProject.value.id, editingProject.value)
      ElMessage.success('项目更新成功')
    } else {
      await createProject(editingProject.value)
      ElMessage.success('项目创建成功')
    }
    projectDialogVisible.value = false
    fetchProjects()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    savingProject.value = false
  }
}

const onDeleteProject = async (project) => {
  try {
    await ElMessageBox.confirm(`确定删除项目「${project.name}」？`, '确认', { type: 'warning' })
    await deleteProject(project.id)
    ElMessage.success('删除成功')
    fetchProjects()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

const formatDate = (iso) => iso ? iso.slice(0, 19).replace('T', ' ') : '-'

onMounted(() => {
  fetchUsers()
  fetchProjects()
})
</script>

<style scoped>
.pc-settings {
  max-width: 1400px;
}

/* ===== Tabs ===== */
.styled-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}

.styled-tabs :deep(.el-tabs__item) {
  font-size: 15px;
  font-weight: 500;
}

.styled-tabs :deep(.el-tabs__active-bar) {
  background: #2563eb;
  height: 3px;
  border-radius: 2px;
}

.styled-tabs :deep(.el-tabs__item.is-active) {
  color: #2563eb;
  font-weight: 600;
}

/* ===== Content Card ===== */
.content-card {
  border-radius: 10px;
}

.card-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.add-btn {
  background: #2563eb;
  border-color: #2563eb;
  border-radius: 6px;
  font-weight: 500;
}

.add-btn:hover {
  background: #1d4ed8;
  border-color: #1d4ed8;
}

/* ===== Table ===== */
.styled-table {
  --el-table-border-color: #e5e7eb;
  --el-table-header-bg-color: #f9fafb;
}

.styled-table :deep(th) {
  font-weight: 600;
  color: #5c6477;
  font-size: 13px;
}

.styled-table :deep(td) {
  font-size: 13px;
  color: #1a1d26;
}

.styled-table :deep(.el-table__row:hover > td) {
  background-color: #f5f7fa !important;
}

/* ===== Dialog ===== */
:deep(.styled-dialog .el-dialog) {
  border-radius: 10px;
  overflow: hidden;
}

:deep(.styled-dialog .el-dialog__header) {
  background: #f9fafb;
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
}

:deep(.styled-dialog .el-dialog__title) {
  font-weight: 600;
  color: #1a1d26;
}
</style>
