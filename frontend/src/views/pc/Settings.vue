<template>
  <div class="settings-page">
    <!-- Page header -->
    <div class="phdr">
      <div>
        <h1>系统设置</h1>
      </div>
      <div class="phdr-acts">
        <button class="btn" @click="openChangeMyPwdDialog">
          <svg viewBox="0 0 16 16"><path d="M8 10V6M6 8h4" stroke-width="1.5" fill="none" stroke="currentColor"/><rect x="3" y="7" width="10" height="6" rx="1.5" stroke-width="1.3" fill="none" stroke="currentColor"/></svg>
          修改密码
        </button>
      </div>
    </div>

    <!-- Tab navigation -->
    <div class="set-tabs">
      <button class="set-tab" :class="{ on: activeTab === 'users' }" @click="activeTab = 'users'">用户管理</button>
      <button class="set-tab" :class="{ on: activeTab === 'projects' }" @click="activeTab = 'projects'">项目管理</button>
      <button class="set-tab" :class="{ on: activeTab === 'backup' }" @click="activeTab = 'backup'">数据备份</button>
      <button class="set-tab" :class="{ on: activeTab === 'apikeys' }" @click="activeTab = 'apikeys'">AI模型配置</button>
      <button class="set-tab" :class="{ on: activeTab === 'standards' }" @click="onOpenStandards">检查标准</button>
    </div>

    <!-- ==================== 用户管理 ==================== -->
    <div class="set-panel" :class="{ on: activeTab === 'users' }">
      <div style="margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
        <input class="f-input" v-model="userSearch" placeholder="搜索姓名/手机号" style="min-width: 220px" />
        <button class="btn btn-primary" @click="openUserDialog()" style="margin-left: auto;">
          <svg viewBox="0 0 16 16"><path d="M8 3v10M3 8h10"/></svg>新增用户
        </button>
      </div>
      <div class="card">
        <table class="tbl">
          <thead>
            <tr>
              <th>ID</th><th>手机号</th><th>姓名</th><th>角色</th><th>项目归属</th><th>状态</th><th>创建时间</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="userLoading">
              <td colspan="8" style="text-align:center;padding:40px;color:var(--ink-400)">加载中...</td>
            </tr>
            <tr v-else-if="filteredUsers.length === 0">
              <td colspan="8" style="text-align:center;padding:40px;color:var(--ink-400)">暂无数据</td>
            </tr>
            <tr v-for="row in filteredUsers" :key="row.id">
              <td>{{ row.id }}</td>
              <td style="font-family:var(--mono)">{{ row.phone || '—' }}</td>
              <td style="text-align:left;font-family:var(--sans);font-weight:600;color:var(--ink-900)">{{ row.real_name }}</td>
              <td><span class="kt" :class="roleKtClass(row.role)">{{ roleLabel(row.role) }}</span></td>
              <td style="text-align:left;font-family:var(--sans)">
                <template v-if="['inspector', 'site_supervisor', 'admin'].includes(row.role)">阵地</template>
                <template v-else-if="row.project_names && row.project_names.length">
                  <span v-for="name in row.project_names" :key="name" class="kt kt-blue" style="margin-right:4px">{{ name }}</span>
                </template>
                <template v-else>—</template>
              </td>
              <td><span class="st" :class="row.is_active ? 'st-done' : 'st-pending'">{{ row.is_active ? '启用' : '禁用' }}</span></td>
              <td style="font-family:var(--mono);font-size:12px;color:var(--ink-400)">{{ formatDate(row.created_at) }}</td>
              <td>
                <button class="act" @click="openUserDialog(row)">编辑</button>
                <button class="act" @click="openResetPwdDialog(row)">重置密码</button>
                <button v-if="row.is_active" class="act act-err" @click="toggleActive(row)">禁用</button>
                <button v-else class="act act-ok" @click="toggleActive(row)">启用</button>
                <button class="act act-err" @click="onDeleteUser(row)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ==================== 项目管理 ==================== -->
    <div class="set-panel" :class="{ on: activeTab === 'projects' }">
      <div style="margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
        <input class="f-input" v-model="projectSearch" placeholder="搜索项目名称" style="min-width: 220px" />
        <button class="btn btn-primary" @click="openProjectDialog()" style="margin-left: auto;">
          <svg viewBox="0 0 16 16"><path d="M8 3v10M3 8h10"/></svg>新增项目
        </button>
      </div>
      <div class="card">
        <table class="tbl">
          <thead>
            <tr>
              <th>ID</th><th>项目名称</th><th>项目编码</th><th>项目地址</th><th>创建时间</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="projectLoading">
              <td colspan="6" style="text-align:center;padding:40px;color:var(--ink-400)">加载中...</td>
            </tr>
            <tr v-else-if="filteredProjects.length === 0">
              <td colspan="6" style="text-align:center;padding:40px;color:var(--ink-400)">暂无数据</td>
            </tr>
            <tr v-for="row in filteredProjects" :key="row.id">
              <td>{{ row.id }}</td>
              <td style="text-align:left;font-family:var(--sans);font-weight:600;color:var(--ink-900)">{{ row.name }}</td>
              <td style="font-family:var(--mono)">{{ row.code || '—' }}</td>
              <td style="text-align:left;font-family:var(--sans)">{{ row.address || '—' }}</td>
              <td style="font-family:var(--mono);font-size:12px;color:var(--ink-400)">{{ formatDate(row.created_at) }}</td>
              <td>
                <button class="act" @click="openProjectDialog(row)">编辑</button>
                <button class="act act-err" @click="onDeleteProject(row)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ==================== 数据备份 ==================== -->
    <div class="set-panel" :class="{ on: activeTab === 'backup' }">
      <!-- 状态概览 -->
      <div class="bk-grid">
        <div class="bk-item">
          <div class="bk-label">数据库</div>
          <div class="bk-val">{{ backupStatus.db_size_mb ?? '—' }} MB</div>
          <div class="bk-status">● 正常</div>
        </div>
        <div class="bk-item">
          <div class="bk-label">照片</div>
          <div class="bk-val">{{ backupStatus.photos_size_mb ?? '—' }} MB</div>
          <div class="bk-status">● 正常</div>
        </div>
        <div class="bk-item">
          <div class="bk-label">报告</div>
          <div class="bk-val">{{ backupStatus.reports_size_mb ?? '—' }} MB</div>
          <div class="bk-status">● 正常</div>
        </div>
        <div class="bk-item">
          <div class="bk-label">总数据量</div>
          <div class="bk-val">{{ backupStatus.total_data_size_mb ?? '—' }} MB</div>
          <div class="bk-status">● 正常</div>
        </div>
        <div class="bk-item">
          <div class="bk-label">外部备份</div>
          <div class="bk-val">{{ backupStatus.external_backup_count ?? 0 }} 个</div>
          <div class="bk-status">● 最新</div>
        </div>
        <div class="bk-item">
          <div class="bk-label">最近备份</div>
          <div class="bk-val">{{ backupStatus.last_backup ? backupStatus.last_backup.created_at?.slice(0,19).replace('T',' ') : '无' }}</div>
          <div class="bk-status">● 自动</div>
        </div>
      </div>

      <!-- 筛选与操作 -->
      <div class="filters" style="margin-bottom: 12px">
        <div class="radio-group">
          <button class="radio-btn" :class="{ on: backupTypeFilter === '' }" @click="backupTypeFilter = ''; fetchBackupList()">全部</button>
          <button class="radio-btn" :class="{ on: backupTypeFilter === 'full' }" @click="backupTypeFilter = 'full'; fetchBackupList()">完整备份</button>
          <button class="radio-btn" :class="{ on: backupTypeFilter === 'daily' }" @click="backupTypeFilter = 'daily'; fetchBackupList()">每日DB</button>
          <button class="radio-btn" :class="{ on: backupTypeFilter === 'hourly' }" @click="backupTypeFilter = 'hourly'; fetchBackupList()">每小时DB</button>
          <button class="radio-btn" :class="{ on: backupTypeFilter === 'pre_restore' }" @click="backupTypeFilter = 'pre_restore'; fetchBackupList()">恢复前</button>
        </div>
        <div style="margin-left: auto; display: flex; gap: 6px">
          <button class="btn btn-primary" @click="onCreateBackup('full')" :disabled="creatingBackup">
            {{ creatingBackup ? '备份中...' : '创建完整备份' }}
          </button>
          <button class="btn" @click="onCreateBackup('hourly')" :disabled="creatingBackup">
            {{ creatingBackup ? '备份中...' : '创建DB备份' }}
          </button>
        </div>
      </div>

      <!-- 备份列表 -->
      <div class="card">
        <table class="tbl">
          <thead>
            <tr>
              <th>文件名</th><th>类型</th><th>大小</th><th>创建时间</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="backupLoading">
              <td colspan="5" style="text-align:center;padding:40px;color:var(--ink-400)">加载中...</td>
            </tr>
            <tr v-else-if="backupList.length === 0">
              <td colspan="5" style="text-align:center;padding:40px;color:var(--ink-400)">暂无数据</td>
            </tr>
            <tr v-for="row in backupList" :key="row.filename">
              <td style="text-align:left;font-family:var(--mono);font-size:12px;color:var(--ink-600)">{{ row.filename }}</td>
              <td><span class="kt" :class="backupTypeKtClass(row.type)">{{ backupTypeLabel(row.type) }}</span></td>
              <td style="font-family:var(--mono)">{{ row.size_mb }} MB</td>
              <td style="font-family:var(--mono);font-size:12px;color:var(--ink-400)">{{ row.created_at?.slice(0,19).replace('T',' ') || '-' }}</td>
              <td>
                <button class="act act-warn" @click="onRestoreBackup(row)">恢复</button>
                <button class="act act-err" @click="onDeleteBackup(row)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ==================== AI模型配置 ==================== -->
    <div class="set-panel" :class="{ on: activeTab === 'apikeys' }">
      <div style="margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
        <span style="font-size: 14px; color: var(--ink-400);">管理 AI 模型的 API 密钥，修改后立即生效，无需重启服务</span>
        <button class="btn" @click="fetchApiKeys" style="margin-left: auto;">
          <svg viewBox="0 0 16 16" style="width:14px;height:14px"><path d="M8 1v2M8 13v2M1 8h2M13 8h2" stroke="currentColor" stroke-width="1.5" fill="none"/></svg>
          刷新
        </button>
      </div>
      <div class="card">
        <table class="tbl">
          <thead>
            <tr>
              <th>模型</th><th>API 密钥</th><th>状态</th><th>更新时间</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="apiKeysLoading">
              <td colspan="5" style="text-align:center;padding:40px;color:var(--ink-400)">加载中...</td>
            </tr>
            <tr v-else-if="apiKeys.length === 0">
              <td colspan="5" style="text-align:center;padding:40px;color:var(--ink-400)">暂无数据</td>
            </tr>
            <tr v-for="row in apiKeys" :key="row.name">
              <td style="font-weight:600;color:var(--ink-900)">{{ row.display_name }}</td>
              <td style="font-family:var(--mono);font-size:13px;color:var(--ink-500)">{{ row.masked_value || '—' }}</td>
              <td>
                <span class="st" :class="row.is_set ? 'st-done' : 'st-pending'">{{ row.is_set ? '已配置' : '未配置' }}</span>
              </td>
              <td style="font-family:var(--mono);font-size:12px;color:var(--ink-400)">{{ row.updated_at ? row.updated_at.slice(0,19).replace('T',' ') : '—' }}</td>
              <td>
                <button class="act" @click="openApiKeyDialog(row)">编辑</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- API KEY 编辑弹窗 -->
    <el-dialog v-model="apiKeyDialogVisible" title="更新 API 密钥" width="480px" class="styled-dialog">
      <el-form label-width="100px">
        <el-form-item label="模型">
          <span style="font-weight:600">{{ editingApiKey.display_name }}</span>
        </el-form-item>
        <el-form-item label="当前密钥">
          <span style="font-family:var(--mono);color:var(--ink-400)">{{ editingApiKey.masked_value || '未配置' }}</span>
        </el-form-item>
        <el-form-item label="新密钥" required>
          <el-input v-model="newApiKeyValue" type="password" show-password placeholder="请输入新的 API 密钥" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="apiKeyDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="onSaveApiKey" :loading="savingApiKey">确认更新</el-button>
      </template>
    </el-dialog>

    <!-- 用户编辑弹窗 -->
    <el-dialog v-model="userDialogVisible" :title="editingUser.id ? '编辑用户' : '新增用户'" width="480px" class="styled-dialog">
      <el-form :model="editingUser" label-width="80px">
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
          <el-select v-model="editingUser.project_ids" multiple clearable collapse-tags collapse-tags-tooltip style="width: 100%" placeholder="请选择项目（可多选）">
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
          <span>{{ resetPwdUser.real_name }}（{{ resetPwdUser.phone || '无手机号' }}）</span>
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

    <!-- ==================== 检查标准 ==================== -->
    <div class="set-panel" :class="{ on: activeTab === 'standards' }">
      <!-- 导入区 -->
      <div class="card std-import-card">
        <div class="std-import-title">导入检查标准</div>
        <div class="std-import-desc">
          支持 Excel（.xlsx）与 Word（.docx）。规范表格自动识别：每模块一个工作表，或首列为「行动主题」的单表（月度行动标准）；不规则文档由 AI 解析结构。
        </div>
        <div class="std-import-form">
          <input ref="stdFileRef" type="file" accept=".xlsx,.docx" class="std-file-hidden" @change="onStdFileChange" />
          <button class="btn" @click="stdFileRef?.click()">选择文件</button>
          <span class="std-file-name" :class="{ empty: !stdForm.file }">{{ stdForm.file ? stdForm.file.name : '未选择文件' }}</span>
          <input class="std-label-input" v-model="stdForm.label" placeholder="标准名称（如：砺质行动检查标准·9月）" />
          <select class="std-model-sel" v-model="stdForm.scoring_model">
            <option value="auto">计分方式：自动识别</option>
            <option value="point_cap">封顶制（按分值封顶）</option>
            <option value="weighted_5pt">权重制（5分×权重）</option>
          </select>
          <button class="btn btn-primary" style="margin-left:auto" :disabled="!stdForm.file || importingStd" @click="onImportStandard">
            {{ importingStd ? '解析中…' : '导入标准' }}
          </button>
        </div>
        <div v-if="importPreview" class="std-preview">
          <div class="std-preview-ok">
            已识别 {{ importPreview.module_count }} 个模块 / {{ importPreview.items_total }} 个检查项（{{ importPreview.scoring_model === 'point_cap' ? '封顶制' : '权重制' }}），创建任务时即可选择「{{ importPreview.label }}」
          </div>
          <div class="std-preview-mods">
            <span v-for="m in importPreview.modules" :key="m.name" class="ktag" :class="m.role === 'deduction' ? 'ktag-err' : 'ktag-brand'">
              {{ m.name }} · {{ m.item_count }}项{{ m.role === 'deduction' ? ' · 扣分' : '' }}
            </span>
          </div>
        </div>
      </div>

      <!-- 标准列表 -->
      <div class="card">
        <table class="tbl">
          <thead>
            <tr>
              <th>名称</th><th>类型</th><th>计分方式</th><th class="ctr">模块</th><th class="ctr">检查项</th><th>来源文件</th><th>导入时间</th><th class="ctr">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="stdLoading"><td colspan="8" style="text-align:center;padding:40px;color:var(--ink-400)">加载中...</td></tr>
            <tr v-else-if="!standards.length"><td colspan="8" style="text-align:center;padding:40px;color:var(--ink-400)">暂无检查标准</td></tr>
            <tr v-for="s in standards" :key="s.standard_type">
              <td style="font-weight:600">{{ s.label }}</td>
              <td><span class="ktag" :class="s.is_custom ? 'ktag-brand' : 'ktag-muted'">{{ s.is_custom ? '导入' : '内置' }}</span></td>
              <td>{{ s.scoring_model === 'point_cap' ? '封顶制' : '权重制' }}</td>
              <td class="ctr">{{ s.module_count }}</td>
              <td class="ctr">{{ s.items_total ?? '—' }}</td>
              <td style="color:var(--ink-500)">{{ s.source_filename || '—' }}</td>
              <td style="color:var(--ink-500)">{{ s.created_at || '—' }}</td>
              <td class="ctr">
                <button v-if="s.is_custom" class="act act-err" @click="onDeleteStandard(s)">删除</button>
                <span v-else style="color:var(--ink-300)">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 修改密码弹窗 -->
    <el-dialog v-model="changeMyPwdVisible" title="修改密码" width="400px" class="styled-dialog">
      <el-form label-width="80px">
        <el-form-item label="新密码" required>
          <el-input v-model="changeMyPwdValue" type="password" show-password placeholder="至少8位，包含字母和数字" />
        </el-form-item>
        <el-form-item label="确认密码" required>
          <el-input v-model="changeMyPwdConfirm" type="password" show-password placeholder="再次输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="changeMyPwdVisible = false">取消</el-button>
        <el-button type="primary" @click="onChangeMyPwd" :loading="changingMyPwd">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUsers, createUser, updateUser, deleteUser } from '../../api/pc'
import { getAllProjects, createProject, updateProject, deleteProject } from '../../api/pc'
import { getBackupStatus, listBackups, createBackup, restoreBackup, deleteBackup as deleteBackupApi } from '../../api/backup'
import { changePassword } from '../../api/auth'
import { getApiKeys, updateApiKey } from '../../api/settings'
import { getStandardList, importStandard, deleteStandard } from '../../api/standards'

const activeTab = ref('users')

// ==================== 用户管理 ====================
const users = ref([])
const userLoading = ref(false)
const userSearch = ref('')
const userDialogVisible = ref(false)
const savingUser = ref(false)
const editingUser = ref({ username: '', password: '', real_name: '', role: 'inspector', project_ids: [] })

const filteredUsers = computed(() => {
  if (!userSearch.value) return users.value
  const q = userSearch.value.toLowerCase()
  return users.value.filter(u =>
    u.real_name.toLowerCase().includes(q) || (u.phone || '').includes(q)
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
    editingUser.value = { ...user, password: '', project_ids: user.project_ids || [] }
  } else {
    editingUser.value = { username: '', password: '', phone: '', real_name: '', role: 'inspector', project_ids: [] }
  }
  userDialogVisible.value = true
}

const onSaveUser = async () => {
  const u = editingUser.value
  if (!u.real_name) { ElMessage.warning('请填写必填项'); return }
  savingUser.value = true
  try {
    if (u.id) {
      const data = { real_name: u.real_name, role: u.role, phone: u.phone || null, project_ids: u.project_ids || [] }
      if (u.password) data.password = u.password
      await updateUser(u.id, data)
      ElMessage.success('用户更新成功')
    } else {
      if (!u.password) { ElMessage.warning('请输入密码'); savingUser.value = false; return }
      const generatedUsername = u.phone ? 'u_' + u.phone.slice(-4) + '_' + Math.floor(100 + Math.random() * 900) : 'u_' + Date.now()
      await createUser({ username: generatedUsername, password: u.password, real_name: u.real_name, role: u.role, phone: u.phone || null, project_ids: u.project_ids || [] })
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
const roleKtClass = (r) => ({ admin: 'kt-blue', inspector: 'kt-teal', site_supervisor: 'kt-warn', field_supervisor: 'kt-teal', project_staff: 'kt-muted' }[r] || 'kt-muted')

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

// ==================== 数据备份 ====================
const backupStatus = ref({})
const backupList = ref([])
const backupLoading = ref(false)
const backupTypeFilter = ref('')
const creatingBackup = ref(false)

const backupTypeLabel = (t) => ({ full: '完整备份', daily: '每日DB', hourly: '每小时DB', pre_restore: '恢复前' }[t] || t)
const backupTypeTag = (t) => ({ full: '', daily: 'success', hourly: 'warning', pre_restore: 'info' }[t] || '')
const backupTypeKtClass = (t) => ({ full: 'kt-teal', daily: 'kt-blue', hourly: 'kt-muted', pre_restore: 'kt-muted' }[t] || 'kt-muted')

const fetchBackupStatus = async () => {
  try {
    backupStatus.value = await getBackupStatus()
  } catch (e) { /* silent */ }
}

const fetchBackupList = async () => {
  backupLoading.value = true
  try {
    const res = await listBackups({ type: backupTypeFilter.value || undefined })
    backupList.value = res.items || []
  } catch (e) {
    ElMessage.error('获取备份列表失败')
  } finally {
    backupLoading.value = false
  }
}

const onCreateBackup = async (type) => {
  creatingBackup.value = true
  try {
    const res = await createBackup({ type })
    ElMessage.success(res.message || '备份创建成功')
    fetchBackupStatus()
    fetchBackupList()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建备份失败')
  } finally {
    creatingBackup.value = false
  }
}

const onRestoreBackup = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要从「${row.filename}」恢复？此操作将覆盖当前数据。系统会先自动创建恢复前备份。`,
      '确认恢复',
      { type: 'warning', confirmButtonText: '确认恢复', cancelButtonText: '取消' }
    )
    const res = await restoreBackup({ filename: row.filename, backup_type: row.type })
    ElMessage.success(res.message || '恢复成功')
    fetchBackupStatus()
    fetchBackupList()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '恢复失败')
  }
}

const onDeleteBackup = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除备份「${row.filename}」？`, '确认', { type: 'warning' })
    await deleteBackupApi(row.filename, row.type)
    ElMessage.success('删除成功')
    fetchBackupStatus()
    fetchBackupList()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

// ==================== 修改密码（自助） ====================
const changeMyPwdVisible = ref(false)
const changeMyPwdValue = ref('')
const changeMyPwdConfirm = ref('')
const changingMyPwd = ref(false)

const openChangeMyPwdDialog = () => {
  changeMyPwdValue.value = ''
  changeMyPwdConfirm.value = ''
  changeMyPwdVisible.value = true
}

const onChangeMyPwd = async () => {
  if (!changeMyPwdValue.value || changeMyPwdValue.value.length < 8) {
    ElMessage.warning('密码长度不能少于8位')
    return
  }
  if (!/[a-zA-Z]/.test(changeMyPwdValue.value) || !/\d/.test(changeMyPwdValue.value)) {
    ElMessage.warning('密码需包含字母和数字')
    return
  }
  if (changeMyPwdValue.value !== changeMyPwdConfirm.value) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  changingMyPwd.value = true
  try {
    await changePassword({ new_password: changeMyPwdValue.value })
    ElMessage.success('密码修改成功')
    changeMyPwdVisible.value = false
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '修改失败')
  } finally {
    changingMyPwd.value = false
  }
}

onMounted(() => {
  fetchUsers()
  fetchProjects()
  fetchBackupStatus()
  fetchBackupList()
  fetchApiKeys()
})

// ==================== 检查标准 ====================
const stdFileRef = ref(null)
const stdForm = ref({ file: null, label: '', scoring_model: 'auto' })
const importingStd = ref(false)
const importPreview = ref(null)
const standards = ref([])
const stdLoading = ref(false)

const onOpenStandards = () => {
  activeTab.value = 'standards'
  fetchStandards()
}

const onStdFileChange = (e) => {
  const f = e.target.files?.[0]
  if (!f) return
  if (!/\.(xlsx|docx)$/i.test(f.name)) {
    ElMessage.error('仅支持 .xlsx 或 .docx 文件')
    e.target.value = ''
    return
  }
  stdForm.value.file = f
  if (!stdForm.value.label) {
    stdForm.value.label = f.name.replace(/\.(xlsx|docx)$/i, '')
  }
}

const fetchStandards = async () => {
  stdLoading.value = true
  try {
    const res = await getStandardList()
    standards.value = res.items || []
  } catch (e) {
    console.error('获取检查标准列表失败:', e)
  } finally {
    stdLoading.value = false
  }
}

const onImportStandard = async () => {
  if (!stdForm.value.file) return
  importingStd.value = true
  importPreview.value = null
  try {
    const fd = new FormData()
    fd.append('file', stdForm.value.file)
    fd.append('label', stdForm.value.label || stdForm.value.file.name.replace(/\.(xlsx|docx)$/i, ''))
    fd.append('scoring_model', stdForm.value.scoring_model)
    const res = await importStandard(fd)
    importPreview.value = res
    ElMessage.success(`导入成功：${res.module_count} 个模块 / ${res.items_total} 个检查项`)
    stdForm.value = { file: null, label: '', scoring_model: 'auto' }
    if (stdFileRef.value) stdFileRef.value.value = ''
    fetchStandards()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '导入失败：无法识别该文件的标准结构')
  } finally {
    importingStd.value = false
  }
}

const onDeleteStandard = async (s) => {
  try {
    await ElMessageBox.confirm(`确定删除「${s.label}」？正被检查任务使用的标准不可删除。`, '删除检查标准', { type: 'warning' })
  } catch { return }
  try {
    await deleteStandard(s.standard_type)
    ElMessage.success('已删除')
    fetchStandards()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

// ==================== AI 模型配置 ====================
const apiKeys = ref([])
const apiKeysLoading = ref(false)
const apiKeyDialogVisible = ref(false)
const editingApiKey = ref({})
const newApiKeyValue = ref('')
const savingApiKey = ref(false)

const fetchApiKeys = async () => {
  apiKeysLoading.value = true
  try {
    const res = await getApiKeys()
    apiKeys.value = res.keys || []
  } catch (e) {
    ElMessage.error('获取 API 密钥失败')
  } finally {
    apiKeysLoading.value = false
  }
}

const openApiKeyDialog = (row) => {
  editingApiKey.value = { ...row }
  newApiKeyValue.value = ''
  apiKeyDialogVisible.value = true
}

const onSaveApiKey = async () => {
  if (!newApiKeyValue.value || newApiKeyValue.value.length < 4) {
    ElMessage.warning('请输入有效的 API 密钥')
    return
  }
  savingApiKey.value = true
  try {
    await updateApiKey({
      key_name: editingApiKey.value.name,
      new_value: newApiKeyValue.value
    })
    ElMessage.success('API 密钥更新成功，已立即生效')
    apiKeyDialogVisible.value = false
    fetchApiKeys()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '更新失败')
  } finally {
    savingApiKey.value = false
  }
}
</script>

<style scoped>
/* ==================== Page Container ==================== */
.settings-page {
  max-width: 1400px;
  padding-bottom: 40px;
}

/* ==================== Page Header (prototype .phdr) ==================== */

/* ==================== Settings Tabs (prototype .set-tabs) ==================== */
.set-tabs {
  display: inline-flex;
  gap: 2px;
  margin-bottom: 18px;
  padding: 2px;
  background: var(--bg-muted);
  border: 1px solid var(--ink-200);
  border-radius: var(--r);
}

.set-tab {
  padding: 0 14px;
  height: 28px;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--ink-600);
  cursor: pointer;
  border: none;
  background: transparent;
  border-radius: var(--r-sm);
  font-family: var(--sans);
  transition: all 0.12s;
}

.set-tab:hover {
  color: var(--ink-900);
}

.set-tab.on {
  background: var(--bg-card);
  color: var(--ink-900);
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(22, 22, 28, 0.08);
}

/* ==================== Panel toggle ==================== */
.set-panel {
  display: none;
}

/* ===== 检查标准导入 ===== */
.std-import-card {
  padding: 16px 18px;
  margin-bottom: 14px;
}

.std-import-title {
  font-size: 14.5px;
  font-weight: 700;
  color: var(--ink-900);
}

.std-import-desc {
  font-size: 12.5px;
  color: var(--ink-500);
  margin-top: 5px;
  line-height: 1.7;
}

.std-import-form {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 13px;
  flex-wrap: wrap;
}

.std-file-hidden {
  display: none;
}

.std-file-name {
  font-size: 12.5px;
  color: var(--ink-700);
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.std-file-name.empty {
  color: var(--ink-400);
}

.std-label-input {
  height: 32px;
  padding: 0 10px;
  border: 1px solid var(--ink-200);
  border-radius: var(--r);
  background: var(--bg-card);
  font-family: var(--sans);
  font-size: 13px;
  color: var(--ink-900);
  outline: none;
  min-width: 260px;
  flex: 1;
}

.std-label-input:focus {
  border-color: var(--blue);
  box-shadow: var(--focus-ring);
}

.std-model-sel {
  height: 32px;
  padding: 0 10px;
  border: 1px solid var(--ink-200);
  border-radius: var(--r);
  background: var(--bg-card);
  font-family: var(--sans);
  font-size: 13px;
  color: var(--ink-800);
  outline: none;
}

.std-preview {
  margin-top: 13px;
  padding: 12px 14px;
  background: var(--ok-bg);
  border: 1px solid #b9e2cc;
  border-radius: var(--r);
}

.std-preview-ok {
  font-size: 13px;
  font-weight: 600;
  color: var(--ok-strong);
}

.std-preview-mods {
  display: flex;
  gap: 6px;
  margin-top: 9px;
  flex-wrap: wrap;
}

.set-panel.on {
  display: block;
  animation: pgIn 0.25s var(--ease);
}

@keyframes pgIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}

/* ==================== Buttons (prototype .btn) ==================== */

/* ==================== Input (prototype .f-input) ==================== */
.f-input {
  padding: 7px 12px;
  border-radius: var(--r);
  font-size: 13px;
  font-weight: 400;
  color: var(--ink-800);
  border: 1px solid var(--ink-100);
  background: var(--bg-card);
  font-family: var(--sans);
  transition: all 0.12s;
  min-width: 180px;
  outline: none;
}

.f-input::placeholder {
  color: var(--ink-400);
}

.f-input:hover {
  border-color: var(--ink-200);
}

.f-input:focus {
  border-color: var(--blue);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

/* ==================== Card (prototype .card) ==================== */
.card {
  background: var(--bg-card);
  border: 1px solid var(--ink-100);
  border-radius: var(--r-lg);
  overflow: hidden;
  margin-bottom: 14px;
}

/* ==================== Table (prototype .tbl) ==================== */
.tbl {
  width: 100%;
  border-collapse: collapse;
}

.tbl th {
  font-size: 12px;
  font-weight: 700;
  color: var(--ink-400);
  letter-spacing: 0.3px;
  text-align: center;
  padding: 10px;
  background: var(--bg-muted);
  border-bottom: 1px solid var(--ink-100);
}

.tbl th:first-child {
  text-align: left;
  padding-left: 20px;
}

.tbl td {
  font-size: 14px;
  font-weight: 500;
  text-align: center;
  padding: 12px 10px;
  border-bottom: 1px solid var(--ink-100);
  color: var(--ink-600);
}

.tbl td:first-child {
  text-align: left;
  padding-left: 20px;
  font-family: var(--mono);
  font-size: 12px;
  color: var(--ink-400);
}

.tbl tbody tr {
  cursor: pointer;
  transition: background 0.08s;
}

.tbl tbody tr:hover {
  background: var(--bg);
}

/* ==================== Tags (prototype .kt) ==================== */
.kt {
  font-size: 11px;
  font-family: var(--mono);
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 3px;
}

.kt-blue {
  background: var(--blue-bg);
  color: var(--blue);
}

.kt-teal {
  background: var(--teal-50);
  color: var(--teal-700);
}

.kt-warn {
  background: var(--warn-bg);
  color: var(--warn);
}

.kt-err {
  background: var(--err-bg);
  color: var(--err);
}

.kt-muted {
  background: var(--bg-muted);
  color: var(--ink-600);
}

/* ==================== Status pills (prototype .st) ==================== */
.st {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.st-done {
  background: var(--ok-bg);
  color: var(--ok);
}

.st-pending {
  background: var(--bg-muted);
  color: var(--ink-400);
}

/* ==================== Action buttons (prototype .act) ==================== */
.act {
  font-size: 12px;
  font-weight: 600;
  color: var(--blue);
  cursor: pointer;
  border: none;
  background: none;
  font-family: var(--sans);
  padding: 4px 8px;
  border-radius: var(--r-sm);
  transition: background 0.1s;
}

.act:hover {
  background: var(--blue-bg);
}

.act + .act {
  margin-left: 2px;
}

.act-warn {
  color: var(--warn);
}

.act-warn:hover {
  background: var(--warn-bg);
}

.act-err {
  color: var(--err);
}

.act-err:hover {
  background: var(--err-bg);
}

.act-ok {
  color: var(--ok);
}

.act-ok:hover {
  background: var(--ok-bg);
}

/* ==================== Filters bar (prototype .filters) ==================== */
.filters {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

/* ==================== Radio group (prototype .radio-group) ==================== */
.radio-group {
  display: flex;
  gap: 2px;
  background: var(--bg-muted);
  border-radius: var(--r);
  padding: 3px;
}

.radio-btn {
  padding: 5px 12px;
  border-radius: var(--r-sm);
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-400);
  cursor: pointer;
  border: none;
  background: none;
  font-family: var(--sans);
  transition: all 0.12s;
}

.radio-btn:hover {
  color: var(--ink-600);
}

.radio-btn.on {
  background: var(--bg-card);
  color: var(--blue);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

/* ==================== Backup grid (prototype .bk-grid) ==================== */
.bk-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 18px;
}

.bk-item {
  background: var(--bg-muted);
  border-radius: var(--r);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.bk-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-400);
}

.bk-val {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink-800);
}

.bk-status {
  font-size: 12px;
  font-weight: 600;
  color: var(--ok);
}

/* ==================== Dialog ==================== */
:deep(.styled-dialog .el-dialog) {
  border-radius: var(--r-lg);
  overflow: hidden;
}

:deep(.styled-dialog .el-dialog__header) {
  background: var(--bg-muted);
  padding: 16px 20px;
  border-bottom: 1px solid var(--ink-200);
}

:deep(.styled-dialog .el-dialog__title) {
  font-weight: 600;
  color: var(--ink-900);
}

/* ==================== Responsive ==================== */
@media (max-width: 1200px) {
  .bk-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
