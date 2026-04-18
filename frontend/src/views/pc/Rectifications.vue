<template>
  <div class="page-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">整改闭环</h2>
        <p class="page-desc">问题整改跟踪、AI核查与审核管理</p>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar-card">
      <div class="filter-fields">
        <el-select v-model="projectFilter" placeholder="选择项目" clearable class="filter-select" @change="fetchData">
          <el-option v-for="p in projectList" :key="p" :label="p" :value="p" />
        </el-select>
        <el-select v-model="moduleFilter" placeholder="选择模块" clearable class="filter-select" @change="fetchData">
          <el-option v-for="m in moduleList" :key="m" :label="m" :value="m" />
        </el-select>
        <el-input v-model="keyword" placeholder="搜索问题/检查项" clearable style="width: 200px" @clear="fetchData" @keyup.enter="fetchData">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-radio-group v-model="statusFilter" @change="onStatusRadioChange" size="small">
          <el-radio-button label="">全部</el-radio-button>
          <el-radio-button label="pending">待整改</el-radio-button>
          <el-radio-button label="ai_rejected">AI驳回</el-radio-button>
          <el-radio-button label="pending_review">待审核</el-radio-button>
          <el-radio-button label="ai_approved">AI通过</el-radio-button>
          <el-radio-button label="approved">已通过</el-radio-button>
        </el-radio-group>
      </div>
      <div class="filter-actions">
        <el-button text @click="doExport" :loading="exporting">
          <el-icon style="margin-right:4px"><Download /></el-icon>导出Excel
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card" :class="{ active: activeStat === 'all' }" @click="clickStat('all')">
        <div class="stat-num">{{ baseFilteredItems.length }}</div>
        <div class="stat-label">当前记录</div>
      </div>
      <div class="stat-card warn" :class="{ active: activeStat === 'pending' }" @click="clickStat('pending')">
        <div class="stat-num">{{ baseFilteredItems.filter(i => i.status === 'pending').length }}</div>
        <div class="stat-label">待整改</div>
      </div>
      <div class="stat-card review" :class="{ active: activeStat === 'ai_rejected' }" @click="clickStat('ai_rejected')">
        <div class="stat-num">{{ baseFilteredItems.filter(i => i.status === 'ai_rejected').length }}</div>
        <div class="stat-label">AI驳回</div>
      </div>
      <div class="stat-card warn" :class="{ active: activeStat === 'pending_review' }" @click="clickStat('pending_review')">
        <div class="stat-num">{{ baseFilteredItems.filter(i => i.status === 'pending_review').length }}</div>
        <div class="stat-label">待审核</div>
      </div>
      <div class="stat-card success" :class="{ active: activeStat === 'passed' }" @click="clickStat('passed')">
        <div class="stat-num">{{ baseFilteredItems.filter(i => ['ai_approved', 'approved'].includes(i.status)).length }}</div>
        <div class="stat-label">已通过</div>
      </div>
    </div>

    <!-- 分组视图 -->
    <div class="table-card">
      <div v-if="loading" v-loading="true" style="min-height: 200px" />
      <el-empty v-else-if="groupedItems.length === 0" description="暂无整改记录" />

      <div v-else class="grouped-view">
        <el-collapse v-model="expandedProjects" class="project-collapse">
          <el-collapse-item
            v-for="group in groupedItems"
            :key="group.project_name"
            :name="group.project_name"
          >
            <template #title>
              <div class="project-title">
                <span class="project-name-text">{{ group.project_name }}</span>
                <el-tag size="small" type="info" style="margin-left: 12px">{{ group.totalModules }} 模块</el-tag>
                <el-tag size="small" style="margin-left: 6px">{{ group.totalIssues }} 问题</el-tag>
                <span class="project-status-summary">
                  <span v-if="group.pending" class="status-count warn">{{ group.pending }}待整改</span>
                  <span v-if="group.ai_rejected" class="status-count review">{{ group.ai_rejected }}AI驳回</span>
                  <span v-if="group.approved" class="status-count success">{{ group.approved }}已通过</span>
                </span>
              </div>
            </template>

            <el-collapse
              :model-value="getExpandedModuleArray(group.project_name)"
              @change="(val) => setExpandedModules(group.project_name, val)"
              class="module-collapse"
            >
              <el-collapse-item
                v-for="mod in group.modules"
                :key="mod.module_name"
                :name="mod.module_name"
              >
                <template #title>
                  <div class="module-title">
                    <span class="module-name-text">{{ mod.module_name }}</span>
                    <el-tag size="small" type="info" style="margin-left: 8px">{{ mod.items.length }} 项</el-tag>
                    <span v-if="mod.pending" class="module-badge warn">{{ mod.pending }}待整改</span>
                  </div>
                </template>

                <el-table
                  :data="mod.items"
                  stripe
                  size="small"
                  class="inner-table"
                  :header-cell-style="{ background: '#F8FAFC', color: '#475569', fontWeight: 500, fontSize: '14px' }"
                >
                  <el-table-column prop="task_id" label="任务ID" min-width="200" show-overflow-tooltip>
                    <template #default="{ row }">
                      <span class="id-text">{{ row.task_id }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="item_name" label="检查项" min-width="160" show-overflow-tooltip />
                  <el-table-column prop="description" label="问题描述" min-width="200" show-overflow-tooltip />
                  <el-table-column prop="severity" label="严重程度" width="100" align="center">
                    <template #default="{ row }">
                      <el-tag :type="row.severity === '严重' ? 'danger' : 'warning'" size="small">{{ row.severity }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="AI置信度" width="110" align="center">
                    <template #default="{ row }">
                      <template v-if="row.ai_result">
                        <el-tag :type="row.ai_result.suggestion === '通过' ? 'success' : 'danger'" size="small">
                          {{ row.ai_result.confidence_score }}分
                        </el-tag>
                      </template>
                      <span v-else class="text-muted">-</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="状态" width="100" align="center">
                    <template #default="{ row }">
                      <el-tag :type="getStatusType(row.status)" size="small">{{ getStatusText(row.status) }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="200" align="center">
                    <template #default="{ row }">
                      <div class="action-btns">
                        <el-button
                          v-if="row.status === 'pending'"
                          type="warning" link size="small"
                          @click="openSubmit(row)"
                        >上传整改</el-button>
                        <el-button type="primary" link size="small" @click="openDetail(row)">查看</el-button>
                        <el-button
                          v-if="row.status === 'ai_rejected' && !authStore.isProjectStaff"
                          type="success" link size="small"
                          @click="openReview(row)"
                        >审核</el-button>
                        <el-button
                          v-if="row.status === 'pending_review' && !authStore.isProjectStaff"
                          type="success" link size="small"
                          @click="openReview(row)"
                        >审核</el-button>
                        <el-button
                          v-if="row.status === 'ai_rejected' && authStore.isProjectStaff"
                          type="warning" link size="small"
                          @click="openAppeal(row)"
                        >申诉</el-button>
                        <el-button
                          v-if="!authStore.isProjectStaff && !['pending'].includes(row.status)"
                          type="primary" link size="small"
                          @click="doRecheck(row)"
                        >重新核查</el-button>
                      </div>
                    </template>
                  </el-table-column>
                </el-table>
              </el-collapse-item>
            </el-collapse>
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>

    <!-- ★ 整改提交弹窗（上传整改照片+说明+时间） -->
    <el-dialog v-model="showSubmit" title="上传整改材料" width="750px" top="5vh" :close-on-click-modal="false">
      <div v-if="current" class="submit-content">
        <!-- 原问题信息 -->
        <div class="submit-issue-info">
          <div class="submit-section-title">原问题信息</div>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="项目">{{ current.project_name }}</el-descriptions-item>
            <el-descriptions-item label="模块">{{ current.module_name }}</el-descriptions-item>
            <el-descriptions-item label="检查项">{{ current.item_name }}</el-descriptions-item>
            <el-descriptions-item label="严重程度">
              <el-tag :type="current.severity === '严重' ? 'danger' : 'warning'" size="small">{{ current.severity }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="问题描述" :span="2">{{ current.description }}</el-descriptions-item>
          </el-descriptions>
          <div v-if="current.issue_photos && current.issue_photos.length" style="margin-top:10px">
            <div class="submit-section-title">原问题照片</div>
            <div class="photo-grid">
              <el-image
                v-for="p in current.issue_photos" :key="p.photo_id"
                :src="getPhotoUrl(p.photo_id)" fit="cover"
                style="width:120px;height:90px;border-radius:6px"
                :preview-src-list="current.issue_photos.map(p => getPhotoUrl(p.photo_id))"
              />
            </div>
          </div>
          <div v-if="current.review_note && current.status === 'pending'" class="reject-notice">
            <el-icon color="#ee0a24"><WarningFilled /></el-icon>
            <span>上次驳回原因：{{ current.review_note }}</span>
          </div>
        </div>

        <!-- 整改材料表单 -->
        <div class="submit-form">
          <div class="submit-section-title">整改材料 <span style="color:#ee0a24;font-size:12px">（*为必填）</span></div>

          <el-form label-position="top" size="default">
            <el-form-item label="整改照片 *" required>
              <el-upload
                v-model:file-list="submitFileList"
                action=""
                :auto-upload="false"
                accept=".jpg,.jpeg,.png,.gif"
                list-type="picture-card"
                :limit="5"
                :on-exceed="() => ElMessage.warning('最多上传5张照片')"
              >
                <el-icon size="24"><Plus /></el-icon>
              </el-upload>
              <div class="upload-tip">请上传含有水印的整改照片（jpg/png/gif，最多5张）</div>
            </el-form-item>

            <el-form-item label="整改说明">
              <el-input v-model="submitNote" type="textarea" :rows="3" placeholder="请描述整改情况（选填）" maxlength="500" show-word-limit />
            </el-form-item>

            <el-form-item label="整改完成时间 *">
              <el-date-picker
                v-model="submitTime"
                type="datetime"
                placeholder="选择整改完成时间"
                format="YYYY-MM-DD HH:mm"
                value-format="YYYY-MM-DD HH:mm"
                style="width:100%"
              />
            </el-form-item>
          </el-form>
        </div>
      </div>

      <template #footer>
        <el-button @click="showSubmit = false">取消</el-button>
        <el-button type="primary" :loading="submitting" :disabled="submitFileList.length === 0" @click="doSubmit">
          提交整改
        </el-button>
      </template>
    </el-dialog>

    <!-- 审核弹窗 -->
    <el-dialog v-model="showReview" title="整改审核" width="900px" top="5vh">
      <div v-if="current" class="review-content">
        <div class="review-grid">
          <div class="review-side">
            <div class="review-side-title">原问题</div>
            <div class="review-info">
              <p><strong>项目：</strong>{{ current.project_name }}</p>
              <p><strong>模块：</strong>{{ current.module_name }}</p>
              <p><strong>检查项：</strong>{{ current.item_name }}</p>
              <p><strong>问题描述：</strong>{{ current.description }}</p>
              <p><strong>位置：</strong>{{ current.location || '未指定' }}</p>
            </div>
            <div v-if="current.issue_photos && current.issue_photos.length" class="review-photos">
              <div class="review-photos-title">原问题照片</div>
              <div class="photo-grid">
                <el-image v-for="p in current.issue_photos" :key="p.photo_id" :src="getPhotoUrl(p.photo_id)" fit="cover" style="width:120px;height:90px;border-radius:6px" :preview-src-list="current.issue_photos.map(p => getPhotoUrl(p.photo_id))" />
              </div>
            </div>
          </div>
          <div class="review-side">
            <div class="review-side-title">整改结果</div>
            <div class="review-info">
              <p><strong>整改说明：</strong>{{ current.rectification_note || '无' }}</p>
              <p><strong>整改时间：</strong>{{ current.rectification_time || '未填写' }}</p>
            </div>
            <div v-if="current.rectification_photos && current.rectification_photos.length" class="review-photos">
              <div class="review-photos-title">整改照片</div>
              <div class="photo-grid">
                <el-image v-for="p in current.rectification_photos" :key="p.photo_id" :src="getPhotoUrl(p.photo_id)" fit="cover" style="width:120px;height:90px;border-radius:6px" :preview-src-list="current.rectification_photos.map(p => getPhotoUrl(p.photo_id))" />
              </div>
            </div>
          </div>
        </div>
        <div v-if="current.ai_result" class="ai-result-card">
          <div class="ai-header">
            <el-icon><Cpu /></el-icon>
            <span>AI 核查结果</span>
            <el-tag :type="current.ai_result.suggestion === '通过' ? 'success' : 'danger'" size="small">
              {{ current.ai_result.suggestion }} | 置信度 {{ current.ai_result.confidence_score }}分
            </el-tag>
          </div>
          <div class="ai-body">
            <p v-if="current.ai_result.watermark_info"><strong>水印信息：</strong>{{ current.ai_result.watermark_info }}</p>
            <p><strong>分析：</strong>{{ current.ai_result.analysis }}</p>
          </div>
        </div>
        <div class="review-actions">
          <el-input v-model="reviewNote" type="textarea" :rows="2" placeholder="审核意见（驳回时必填）" />
          <div class="review-btns">
            <el-button type="success" @click="doReview(true)">通过</el-button>
            <el-button type="danger" @click="doReview(false)">驳回</el-button>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 详情弹窗 -->
    <el-dialog v-model="showDetail" title="整改详情" width="700px" top="5vh">
      <div v-if="current" class="detail-content">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="项目">{{ current.project_name }}</el-descriptions-item>
          <el-descriptions-item label="模块">{{ current.module_name }}</el-descriptions-item>
          <el-descriptions-item label="检查项">{{ current.item_name }}</el-descriptions-item>
          <el-descriptions-item label="严重程度">
            <el-tag :type="current.severity === '严重' ? 'danger' : 'warning'" size="small">{{ current.severity }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="问题描述" :span="2">{{ current.description }}</el-descriptions-item>
          <el-descriptions-item label="整改说明" :span="2">{{ current.rectification_note || '无' }}</el-descriptions-item>
          <el-descriptions-item label="整改时间">{{ current.rectification_time || '未填写' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(current.status)" size="small">{{ getStatusText(current.status) }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
        <div class="detail-photos">
          <div class="detail-photo-section">
            <div class="detail-photo-title">原问题照片</div>
            <div class="photo-grid">
              <el-image v-for="p in (current.issue_photos || [])" :key="p.photo_id" :src="getPhotoUrl(p.photo_id)" fit="cover" style="width:120px;height:90px;border-radius:6px" :preview-src-list="(current.issue_photos || []).map(p => getPhotoUrl(p.photo_id))" />
            </div>
          </div>
          <div class="detail-photo-section">
            <div class="detail-photo-title">整改照片</div>
            <div class="photo-grid">
              <el-image v-for="p in (current.rectification_photos || [])" :key="p.photo_id" :src="getPhotoUrl(p.photo_id)" fit="cover" style="width:120px;height:90px;border-radius:6px" :preview-src-list="(current.rectification_photos || []).map(p => getPhotoUrl(p.photo_id))" />
            </div>
          </div>
        </div>
        <div v-if="current.ai_result" class="ai-result-card">
          <div class="ai-header">
            <el-icon><Cpu /></el-icon>
            <span>AI 核查结果</span>
            <el-tag :type="current.ai_result.suggestion === '通过' ? 'success' : 'danger'" size="small">
              {{ current.ai_result.suggestion }} | {{ current.ai_result.confidence_score }}分
            </el-tag>
          </div>
          <div class="ai-body">
            <p v-if="current.ai_result.watermark_info"><strong>水印信息：</strong>{{ current.ai_result.watermark_info }}</p>
            <p><strong>分析：</strong>{{ current.ai_result.analysis }}</p>
          </div>
        </div>
        <div v-if="current.review_note" class="review-record">
          <strong>审核意见：</strong>{{ current.review_note }}
          <span v-if="current.reviewer_name">（{{ current.reviewer_name }}）</span>
        </div>
      </div>
    </el-dialog>

    <!-- 申诉弹窗 -->
    <el-dialog v-model="showAppeal" title="提交申诉" width="400px">
      <el-input v-model="appealNote" type="textarea" :rows="3" placeholder="请说明申诉理由" />
      <template #footer>
        <el-button @click="showAppeal = false">取消</el-button>
        <el-button type="primary" @click="doAppeal" :disabled="!appealNote.trim()">提交申诉</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Cpu, Search, Plus, WarningFilled, Download } from '@element-plus/icons-vue'
import { useAuthStore } from '../../stores/auth'
import {
  getAllRectifications,
  reviewRectification,
  recheckRectification,
  appealRectification,
  uploadRectificationPhoto,
  submitRectification,
  exportRectificationsExcel
} from '../../api/rectification'

const loading = ref(false)
const authStore = useAuthStore()
const items = ref([])
const statusFilter = ref('')
const activeStat = ref('')
const projectFilter = ref('')
const moduleFilter = ref('')
const keyword = ref('')
const projectList = ref([])
const moduleList = ref([])
const showReview = ref(false)
const showDetail = ref(false)
const showSubmit = ref(false)
const showAppeal = ref(false)
const current = ref(null)
const reviewNote = ref('')
const appealNote = ref('')

// 整改提交表单
const submitFileList = ref([])
const submitNote = ref('')
const submitTime = ref('')
const submitting = ref(false)
const exporting = ref(false)

// 分组展开状态
const expandedProjects = ref([])
const expandedModuleSets = ref({})  // { projectName: Set<moduleName> }

// 基础筛选：仅项目/模块/关键词（统计卡片始终使用此数据，不受状态筛选影响）
const baseFilteredItems = computed(() => {
  let list = items.value
  if (projectFilter.value) list = list.filter(i => i.project_name === projectFilter.value)
  if (moduleFilter.value) list = list.filter(i => i.module_name === moduleFilter.value)
  if (keyword.value) {
    const kw = keyword.value.toLowerCase()
    list = list.filter(i =>
      (i.description || '').toLowerCase().includes(kw) ||
      (i.item_name || '').toLowerCase().includes(kw) ||
      (i.project_name || '').toLowerCase().includes(kw) ||
      (i.task_id || '').toLowerCase().includes(kw)
    )
  }
  return list
})

// 表格数据：在基础筛选之上额外应用状态筛选
const filteredItems = computed(() => {
  let list = baseFilteredItems.value
  if (statusFilter.value) {
    if (statusFilter.value === 'passed') {
      list = list.filter(i => ['ai_approved', 'approved'].includes(i.status))
    } else {
      list = list.filter(i => i.status === statusFilter.value)
    }
  }
  return list
})

const clickStat = (stat) => {
  if (activeStat.value === stat) {
    // 再次点击取消筛选
    activeStat.value = ''
    statusFilter.value = ''
  } else {
    activeStat.value = stat
    statusFilter.value = stat === 'all' ? '' : stat
  }
  autoExpand()
}

// 状态单选按钮切换时同步 activeStat
const onStatusRadioChange = (val) => {
  activeStat.value = val || ''
  autoExpand()
}

const groupedItems = computed(() => {
  const groups = {}
  for (const item of filteredItems.value) {
    const proj = item.project_name || '未分配'
    const mod = item.module_name || '未分配'
    if (!groups[proj]) groups[proj] = {}
    if (!groups[proj][mod]) groups[proj][mod] = []
    groups[proj][mod].push(item)
  }
  return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b)).map(([project_name, modules]) => {
    const allItems = Object.values(modules).flat()
    return {
      project_name,
      modules: Object.entries(modules).sort(([a], [b]) => a.localeCompare(b)).map(([module_name, items]) => ({
        module_name,
        items,
        total: items.length,
        pending: items.filter(i => i.status === 'pending').length,
      })),
      totalIssues: allItems.length,
      totalModules: Object.keys(modules).length,
      pending: allItems.filter(i => i.status === 'pending').length,
      ai_rejected: allItems.filter(i => i.status === 'ai_rejected').length,
      approved: allItems.filter(i => ['ai_approved', 'approved'].includes(i.status)).length,
    }
  })
})

const getExpandedModuleArray = (projectName) => {
  const s = expandedModuleSets.value[projectName]
  return s ? [...s] : []
}

const setExpandedModules = (projectName, val) => {
  expandedModuleSets.value = { ...expandedModuleSets.value, [projectName]: new Set(val) }
}

const getStatusType = (s) => {
  const m = { pending: 'info', submitted: '', ai_approved: 'success', ai_rejected: 'warning', pending_review: 'warning', approved: 'success' }
  return m[s] || 'info'
}
const getStatusText = (s) => {
  const m = { pending: '待整改', submitted: 'AI核查中', ai_approved: 'AI通过', ai_rejected: 'AI驳回', pending_review: '待审核', approved: '已通过' }
  return m[s] || s
}
const getPhotoUrl = (pid) => {
  const t = localStorage.getItem('token')
  return `/api/v1/records/photos/${pid}?token=${t}`
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getAllRectifications({ statusFilter: statusFilter.value || undefined })
    items.value = res.items || []
    const ps = new Set(), ms = new Set()
    items.value.forEach(i => { if (i.project_name) ps.add(i.project_name); if (i.module_name) ms.add(i.module_name) })
    projectList.value = [...ps].sort()
    moduleList.value = [...ms].sort()

    // 自动展开筛选对应的项目
    autoExpand()
  } catch { ElMessage.error('加载失败') }
  finally { loading.value = false }
}

const autoExpand = () => {
  if (projectFilter.value) {
    expandedProjects.value = [projectFilter.value]
    if (moduleFilter.value) {
      expandedModuleSets.value = { [projectFilter.value]: new Set([moduleFilter.value]) }
    } else {
      const group = groupedItems.value.find(g => g.project_name === projectFilter.value)
      if (group) {
        expandedModuleSets.value = { [projectFilter.value]: new Set(group.modules.map(m => m.module_name)) }
      }
    }
  } else if (moduleFilter.value) {
    for (const group of groupedItems.value) {
      if (group.modules.some(m => m.module_name === moduleFilter.value)) {
        expandedProjects.value = [group.project_name]
        expandedModuleSets.value = { [group.project_name]: new Set([moduleFilter.value]) }
        break
      }
    }
  }
}

// 打开整改提交弹窗
const openSubmit = (row) => {
  current.value = row
  submitFileList.value = []
  submitNote.value = ''
  submitTime.value = ''
  showSubmit.value = true
}

// 执行整改提交
const doSubmit = async () => {
  if (submitFileList.value.length === 0) {
    ElMessage.warning('请至少上传一张整改照片')
    return
  }
  if (!submitTime.value) {
    ElMessage.warning('请选择整改完成时间')
    return
  }
  submitting.value = true
  try {
    const rid = current.value.rectification_id
    // 1. 逐张上传照片
    for (const f of submitFileList.value) {
      await uploadRectificationPhoto(rid, f.raw)
    }
    // 2. 提交整改（触发AI核查）
    await submitRectification(rid, {
      rectification_note: submitNote.value,
      rectification_time: submitTime.value
    })
    ElMessage.success('整改已提交，AI正在核查中')
    showSubmit.value = false
    fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false
  }
}

const openDetail = (row) => { current.value = row; showDetail.value = true }
const openReview = (row) => { current.value = row; reviewNote.value = ''; showReview.value = true }
const openAppeal = (row) => { current.value = row; appealNote.value = ''; showAppeal.value = true }

const doAppeal = async () => {
  if (!appealNote.value.trim()) return
  try {
    await appealRectification(current.value.rectification_id, { appeal_note: appealNote.value })
    ElMessage.success('申诉已提交')
    showAppeal.value = false
    fetchData()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '申诉失败') }
}

const doRecheck = async (row) => {
  try {
    await recheckRectification(row.rectification_id)
    ElMessage.success('已触发重新AI核查')
    fetchData()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '操作失败') }
}

const doReview = async (approved) => {
  if (!approved && !reviewNote.value.trim()) { ElMessage.warning('驳回时请填写审核意见'); return }
  try {
    await reviewRectification(current.value.rectification_id, { approved, review_note: reviewNote.value })
    ElMessage.success(approved ? '已通过' : '已驳回')
    showReview.value = false
    fetchData()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '操作失败') }
}

// 导出Excel
const doExport = async () => {
  exporting.value = true
  try {
    const res = await exportRectificationsExcel({
      statusFilter: statusFilter.value || undefined,
      projectName: projectFilter.value || undefined,
      moduleName: moduleFilter.value || undefined,
      keyword: keyword.value || undefined
    })
    const blob = new Blob([res], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `整改记录_${new Date().toISOString().slice(0, 10)}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
/* ===== 全局容器 ===== */
.page-container {
  max-width: 1400px;
  padding-bottom: 40px;
}

/* ===== 页面标题 ===== */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header-left {
  display: flex;
  flex-direction: column;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #1a1d26;
  margin: 0;
  line-height: 1.3;
}

.page-desc {
  font-size: 13px;
  color: #9ba3af;
  margin: 4px 0 0;
}

/* ===== 筛选栏 ===== */
.filter-bar-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-radius: 12px;
  padding: 14px 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
  margin-bottom: 16px;
}

.filter-fields {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.filter-select {
  width: 180px;
}

.filter-actions {
  display: flex;
  gap: 8px;
}

/* ===== 统计卡片 ===== */
.stats-row {
  display: flex;
  gap: 14px;
  margin-bottom: 16px;
}

.stat-card {
  flex: 1;
  padding: 16px 20px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  border: 2px solid transparent;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.stat-card.active {
  border-color: #2563eb;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15);
}

.stat-card.warn.active {
  border-color: #dc2626;
  box-shadow: 0 4px 12px rgba(220, 38, 38, 0.15);
}

.stat-card.review.active {
  border-color: #d97706;
  box-shadow: 0 4px 12px rgba(217, 119, 6, 0.15);
}

.stat-card.success.active {
  border-color: #059669;
  box-shadow: 0 4px 12px rgba(5, 150, 105, 0.15);
}

.stat-card.warn {
  background: #FEF2F2;
}

.stat-card.review {
  background: #FFFBEB;
}

.stat-card.success {
  background: #ECFDF5;
}

.stat-num {
  font-size: 28px;
  font-weight: 700;
  color: #1a1d26;
  line-height: 1.2;
}

.stat-card.warn .stat-num {
  color: #dc2626;
}

.stat-card.review .stat-num {
  color: #d97706;
}

.stat-card.success .stat-num {
  color: #059669;
}

.stat-label {
  font-size: 13px;
  color: #9ba3af;
  margin-top: 4px;
}

/* ===== 表格卡片 ===== */
.table-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
  overflow: hidden;
}

/* ===== 分组视图 ===== */
.grouped-view {
  padding: 16px;
}

.project-collapse {
  border: none;
}

.project-collapse :deep(.el-collapse-item__header) {
  background: linear-gradient(135deg, #eff6ff 0%, #f0f9ff 100%);
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  padding: 0 20px;
  margin-bottom: 8px;
  font-size: 16px;
  height: 56px;
  line-height: 56px;
  font-weight: 700;
  color: #1e293b;
}

.project-collapse :deep(.el-collapse-item__header:hover) {
  background: linear-gradient(135deg, #dbeafe 0%, #e0f2fe 100%);
}

.project-collapse :deep(.el-collapse-item__wrap) {
  border: none;
  padding-left: 16px;
}

.project-collapse :deep(.el-collapse-item__content) {
  padding: 4px 0;
}

.project-title {
  display: flex;
  align-items: center;
  width: 100%;
}

.project-name-text {
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
}

.project-status-summary {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

.status-count {
  font-size: 12px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 4px;
}

.status-count.warn { background: #fef3c7; color: #d97706; }
.status-count.review { background: #dbeafe; color: #2563eb; }
.status-count.success { background: #d1fae5; color: #059669; }

/* 模块折叠 */
.module-collapse {
  border: none;
}

.module-collapse :deep(.el-collapse-item__header) {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 0 16px;
  margin-bottom: 4px;
  font-size: 14px;
  height: 48px;
  line-height: 48px;
}

.module-collapse :deep(.el-collapse-item__header:hover) {
  background: #f5f7fa;
}

.module-collapse :deep(.el-collapse-item__wrap) {
  border: none;
}

.module-collapse :deep(.el-collapse-item__content) {
  padding: 8px 0;
}

.module-title {
  display: flex;
  align-items: center;
  width: 100%;
}

.module-name-text {
  font-size: 14px;
  font-weight: 600;
  color: #475569;
}

.module-badge {
  font-size: 12px;
  margin-left: 8px;
  padding: 1px 6px;
  border-radius: 4px;
}

.module-badge.warn { background: #fef3c7; color: #d97706; }

/* 内部表格 */
.inner-table {
  --el-table-border-color: #F1F5F9;
  width: 100%;
}

.inner-table :deep(td) {
  font-size: 14px;
}

/* ===== 表格 ===== */
.styled-table {
  --el-table-border-color: #F1F5F9;
  width: 100%;
}

.styled-table :deep(td) {
  font-size: 16px;
  font-weight: 500;
  color: #1e293b;
  padding: 14px 0;
}

.styled-table :deep(.el-table__row:hover > td) {
  background-color: #F8FAFC !important;
}

.id-text {
  font-size: 15px;
  color: #64748B;
  font-family: "SF Mono", Consolas, monospace;
}

.name-text {
  font-size: 16px;
  font-weight: 500;
  color: #1e293b;
}

.text-muted {
  color: #9ba3af;
}

.action-btns {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
}

/* ===== 整改提交弹窗 ===== */
.submit-content { max-height: 70vh; overflow-y: auto; }
.submit-issue-info { margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #eee; }
.submit-section-title { font-size: 14px; font-weight: 600; color: #1a1d26; margin-bottom: 10px; }
.submit-form { padding-top: 4px; }
.upload-tip { font-size: 12px; color: #9ba3af; margin-top: 4px; }
.reject-notice { margin-top: 10px; padding: 10px 12px; background: #fff5f5; border-radius: 6px; font-size: 13px; color: #ee0a24; display: flex; align-items: center; gap: 6px; }

.photo-grid { display: flex; gap: 6px; flex-wrap: wrap; }

/* ===== 审核弹窗 ===== */
.review-content { max-height: 70vh; overflow-y: auto; }
.review-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.review-side { background: #f5f7fa; border-radius: 8px; padding: 14px; }
.review-side-title { font-size: 14px; font-weight: 600; color: #1a1d26; margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid #e5e7eb; }
.review-info p { font-size: 13px; color: #5c6477; margin: 4px 0; }
.review-photos { margin-top: 10px; }
.review-photos-title { font-size: 12px; color: #9ba3af; margin-bottom: 6px; }

/* ===== AI 结果 ===== */
.ai-result-card { background: linear-gradient(135deg, #f0f9ff 0%, #eff6ff 100%); border: 1px solid #bfdbfe; border-radius: 8px; padding: 14px; margin-bottom: 16px; }
.ai-header { display: flex; align-items: center; gap: 6px; font-size: 14px; font-weight: 600; color: #2563eb; margin-bottom: 8px; }
.ai-body p { font-size: 13px; color: #5c6477; margin: 4px 0; line-height: 1.6; }

/* ===== 审核操作 ===== */
.review-actions { display: flex; gap: 12px; align-items: flex-end; }
.review-actions .el-input { flex: 1; }
.review-btns { display: flex; gap: 8px; }

/* ===== 详情 ===== */
.detail-content { max-height: 70vh; overflow-y: auto; }
.detail-photos { margin-top: 16px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.detail-photo-section { background: #f5f7fa; border-radius: 8px; padding: 12px; }
.detail-photo-title { font-size: 13px; font-weight: 500; color: #5c6477; margin-bottom: 8px; }
.review-record { margin-top: 12px; padding: 10px; background: #f5f7fa; border-radius: 6px; font-size: 13px; color: #5c6477; }
</style>
