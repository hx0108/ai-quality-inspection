<template>
  <div class="page-container">
    <!-- Page header -->
    <div class="phdr">
      <div>
        <h1>整改闭环</h1>
        <div class="phdr-sub">问题整改跟踪、AI核查与审核管理</div>
      </div>
      <div class="phdr-acts">
        <button class="btn" @click="doExport" :disabled="exporting">{{ exporting ? '导出中...' : '导出Excel' }}</button>
      </div>
    </div>

    <!-- KPI stats row -->
    <div class="kpi-row cols-5">
      <div class="kpi clickable" :class="{ active: activeStat === 'all' }" @click="clickStat('all')">
        <div class="kpi-lbl">当前记录</div>
        <div class="kpi-num">{{ statsAllCount }}</div>
      </div>
      <div class="kpi clickable" :class="{ active: activeStat === 'pending' }" @click="clickStat('pending')">
        <div class="kpi-lbl">待整改</div>
        <div class="kpi-num">{{ statsPendingCount }}</div>
      </div>
      <div class="kpi clickable" :class="{ active: activeStat === 'ai_rejected' }" @click="clickStat('ai_rejected')">
        <div class="kpi-lbl">AI驳回</div>
        <div class="kpi-num">{{ statsAiRejectedCount }}</div>
      </div>
      <div class="kpi clickable" :class="{ active: activeStat === 'pending_review' }" @click="clickStat('pending_review')">
        <div class="kpi-lbl">待审核</div>
        <div class="kpi-num">{{ statsPendingReviewCount }}</div>
      </div>
      <div class="kpi clickable" :class="{ active: activeStat === 'passed' }" @click="clickStat('passed')">
        <div class="kpi-lbl">已通过</div>
        <div class="kpi-num">{{ statsPassedCount }}</div>
      </div>
    </div>

    <!-- Filters -->
    <div class="filters">
      <select class="f-sel" v-model="projectFilter" @change="fetchData">
        <option value="">选择项目</option>
        <option v-for="p in projectList" :key="p" :value="p">{{ p }}</option>
      </select>
      <select class="f-sel" v-model="moduleFilter" @change="fetchData">
        <option value="">选择模块</option>
        <option v-for="m in moduleList" :key="m" :value="m">{{ m }}</option>
      </select>
      <input class="f-input" v-model="keyword" placeholder="搜索问题/检查项" style="min-width:150px" @keyup.enter="fetchData" />
      <div class="f-sep"></div>
      <div class="radio-group">
        <button class="radio-btn" :class="{ on: statusFilter === '' }" @click="statusFilter = ''; onStatusRadioChange('')">全部</button>
        <button class="radio-btn" :class="{ on: statusFilter === 'pending' }" @click="statusFilter = 'pending'; onStatusRadioChange('pending')">待整改</button>
        <button class="radio-btn" :class="{ on: statusFilter === 'ai_rejected' }" @click="statusFilter = 'ai_rejected'; onStatusRadioChange('ai_rejected')">AI驳回</button>
        <button class="radio-btn" :class="{ on: statusFilter === 'pending_review' }" @click="statusFilter = 'pending_review'; onStatusRadioChange('pending_review')">待审核</button>
        <button class="radio-btn" :class="{ on: statusFilter === 'ai_approved' }" @click="statusFilter = 'ai_approved'; onStatusRadioChange('ai_approved')">AI通过</button>
        <button class="radio-btn" :class="{ on: statusFilter === 'passed' }" @click="statusFilter = 'passed'; onStatusRadioChange('passed')">已通过</button>
      </div>
    </div>

    <!-- Grouped view -->
    <div v-if="loading" style="text-align:center;padding:60px;color:var(--ink-400)">加载中...</div>
    <div v-else-if="groupedItems.length === 0" style="text-align:center;padding:60px;color:var(--ink-400)">暂无整改记录</div>

    <div v-else class="grouped-view">
      <div v-for="group in groupedItems" :key="group.project_name" class="gv-project">
        <!-- Project header -->
        <div class="gv-project-hdr" @click="toggleProject(group.project_name)">
          <div class="gv-project-name" :class="{ open: expandedProjects.includes(group.project_name) }">
            <svg viewBox="0 0 16 16"><path d="M6 3l5 5-5 5"/></svg>
            {{ group.project_name }}
          </div>
          <div class="gv-project-tags">
            <span class="gv-project-tag kt kt-blue">{{ group.totalModules }} 模块</span>
            <span class="gv-project-tag kt kt-muted">{{ group.totalIssues }} 问题</span>
            <span v-if="group.pending" class="gv-project-tag kt kt-err">{{ group.pending }}待整改</span>
            <span v-if="group.approved" class="gv-project-tag kt kt-ok">{{ group.approved }}已通过</span>
          </div>
        </div>
        <!-- Modules (visible when project expanded) -->
        <template v-if="expandedProjects.includes(group.project_name)">
          <div v-for="mod in group.modules" :key="mod.module_name" class="gv-module">
            <!-- Module header -->
            <div class="gv-module-hdr" @click="toggleModule(group.project_name, mod.module_name)">
              <div class="gv-module-name" :class="{ open: getExpandedModuleArray(group.project_name).includes(mod.module_name) }">
                <svg viewBox="0 0 16 16"><path d="M6 3l5 5-5 5"/></svg>
                {{ mod.module_name }}
              </div>
              <span v-if="mod.pending" class="kt kt-err" style="font-size:11px">{{ mod.pending }}待整改</span>
            </div>
            <!-- Table (visible when module expanded) -->
            <template v-if="getExpandedModuleArray(group.project_name).includes(mod.module_name)">
              <table class="tbl">
                <thead>
                  <tr>
                    <th>任务ID</th>
                    <th>检查项</th>
                    <th>问题描述</th>
                    <th>严重程度</th>
                    <th>AI置信度</th>
                    <th>状态</th>
                    <th>整改截止</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in mod.items" :key="row.rectification_id">
                    <td>{{ row.task_id }}</td>
                    <td style="text-align:left;font-family:var(--sans)">{{ row.item_name }}</td>
                    <td style="text-align:left;font-family:var(--sans);max-width:180px">{{ row.description }}</td>
                    <td>
                      <span class="kt" :class="row.severity === '严重' ? 'kt-err' : 'kt-warn'">{{ row.severity }}</span>
                    </td>
                    <td>
                      <template v-if="row.ai_result">
                        <div class="conf-wrap">
                          <div class="conf-bar">
                            <div class="conf-fill" :style="confStyle(row.ai_result)"></div>
                          </div>
                          <span class="conf-val">{{ formatConf(row.ai_result.confidence_score) }}</span>
                        </div>
                      </template>
                      <span v-else style="color:var(--ink-300)">—</span>
                    </td>
                    <td>
                      <span class="st" :class="statusClass(row.status)">{{ getStatusText(row.status) }}</span>
                    </td>
                    <td>
                      <span v-if="row.deadline" :style="{ color: isOverdue(row.deadline) ? 'var(--red)' : isExpiring(row.deadline) ? 'var(--amber)' : 'var(--ink-400)' }">
                        {{ row.deadline }}
                        <span v-if="isOverdue(row.deadline)" style="font-size:11px">已逾期</span>
                        <span v-else-if="isExpiring(row.deadline)" style="font-size:11px">即将到期</span>
                      </span>
                      <span v-else style="color:var(--ink-300)">—</span>
                    </td>
                    <td>
                      <button v-if="row.status === 'pending'" class="act act-warn" @click="openSubmit(row)">上传整改</button>
                      <button class="act" @click="openDetail(row)">查看</button>
                      <button v-if="row.status === 'ai_rejected' && !authStore.isProjectStaff" class="act act-ok" @click="openReview(row)">审核</button>
                      <button v-if="row.status === 'pending_review' && !authStore.isProjectStaff" class="act act-ok" @click="openReview(row)">审核</button>
                      <button v-if="row.status === 'ai_rejected' && authStore.isProjectStaff" class="act act-warn" @click="openAppeal(row)">申诉</button>
                      <button v-if="!authStore.isProjectStaff && !['pending'].includes(row.status)" class="act" @click="doRecheck(row)">重新核查</button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </template>
          </div>
        </template>
      </div>
    </div>

    <!-- Submit dialog -->
    <el-dialog v-model="showSubmit" title="上传整改材料" width="750px" top="5vh" :close-on-click-modal="false">
      <div v-if="current" class="submit-content">
        <div class="submit-issue-info">
          <div class="submit-section-title">原问题信息</div>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="项目">{{ current.project_name }}</el-descriptions-item>
            <el-descriptions-item label="模块">{{ current.module_name }}</el-descriptions-item>
            <el-descriptions-item label="检查项">{{ current.item_name }}</el-descriptions-item>
            <el-descriptions-item label="严重程度">
              <span class="kt" :class="current.severity === '严重' ? 'kt-err' : 'kt-warn'">{{ current.severity }}</span>
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
            <el-icon color="var(--err)"><WarningFilled /></el-icon>
            <span>上次驳回原因：{{ current.review_note }}</span>
          </div>
        </div>

        <div class="submit-form">
          <div class="submit-section-title">整改材料 <span style="color:var(--err);font-size:12px">（*为必填）</span></div>
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
            <el-form-item label="整改说明 *" required>
              <el-input v-model="submitNote" type="textarea" :rows="3" placeholder="请描述整改情况" maxlength="500" show-word-limit />
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
        <el-button type="primary" :loading="submitting" :disabled="submitFileList.length === 0 || !submitNote.trim() || !submitTime" @click="doSubmit">
          提交整改
        </el-button>
      </template>
    </el-dialog>

    <!-- Review dialog -->
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
            <span class="sp" :class="current.ai_result.suggestion === '通过' ? 'sp-hi' : 'sp-lo'">{{ current.ai_result.suggestion }} | 置信度 {{ current.ai_result.confidence_score }}分</span>
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

    <!-- Detail dialog -->
    <el-dialog v-model="showDetail" title="整改详情" width="700px" top="5vh">
      <div v-if="current" class="detail-content">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="项目">{{ current.project_name }}</el-descriptions-item>
          <el-descriptions-item label="模块">{{ current.module_name }}</el-descriptions-item>
          <el-descriptions-item label="检查项">{{ current.item_name }}</el-descriptions-item>
          <el-descriptions-item label="严重程度">
            <span class="kt" :class="current.severity === '严重' ? 'kt-err' : 'kt-warn'">{{ current.severity }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="问题描述" :span="2">{{ current.description }}</el-descriptions-item>
          <el-descriptions-item label="整改说明" :span="2">{{ current.rectification_note || '无' }}</el-descriptions-item>
          <el-descriptions-item label="整改时间">{{ current.rectification_time || '未填写' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <span class="st" :class="statusClass(current.status)">{{ getStatusText(current.status) }}</span>
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
            <span class="sp" :class="current.ai_result.suggestion === '通过' ? 'sp-hi' : 'sp-lo'">{{ current.ai_result.suggestion }} | {{ current.ai_result.confidence_score }}分</span>
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

    <!-- Appeal dialog -->
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
import { getAuthToken } from '../../utils/authStorage'
import {
  getAllRectifications,
  reviewRectification,
  recheckRectification,
  appealRectification,
  uploadRectificationPhoto,
  submitRectification
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

// 统计卡片数据：基于原始完整数据，不受当前筛选影响
const statsAllCount = computed(() => baseFilteredItems.value.length)
const statsPendingCount = computed(() => baseFilteredItems.value.filter(i => i.status === 'pending').length)
const statsAiRejectedCount = computed(() => baseFilteredItems.value.filter(i => i.status === 'ai_rejected').length)
const statsPendingReviewCount = computed(() => baseFilteredItems.value.filter(i => i.status === 'pending_review').length)
const statsPassedCount = computed(() => baseFilteredItems.value.filter(i => ['ai_approved', 'approved'].includes(i.status)).length)

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
  const t = getAuthToken()
  return `/api/v1/records/photos/${pid}?token=${t}`
}

// Template helpers for prototype classes
const statusClass = (s) => {
  const m = { pending: 'st-pending', submitted: 'st-checking', ai_approved: 'st-ai-pass', ai_rejected: 'st-ai-reject', pending_review: 'st-review', approved: 'st-done' }
  return m[s] || 'st-pending'
}
const isOverdue = (deadline) => {
  if (!deadline) return false
  return new Date(deadline) < new Date(new Date().toISOString().slice(0, 10))
}
const isExpiring = (deadline) => {
  if (!deadline) return false
  const diff = (new Date(deadline) - new Date(new Date().toISOString().slice(0, 10))) / 86400000
  return diff > 0 && diff <= 5
}
const formatConf = (score) => {
  if (score == null) return '—'
  const v = parseFloat(score)
  return isNaN(v) ? score : v.toFixed(2)
}
const confStyle = (aiResult) => {
  if (!aiResult || aiResult.confidence_score == null) return {}
  const v = parseFloat(aiResult.confidence_score)
  const pct = Math.round(Math.min(Math.max(v * 100, 0), 100))
  const color = v >= 0.8 ? 'var(--ok)' : v >= 0.5 ? 'var(--warn)' : 'var(--err)'
  return { width: pct + '%', background: color }
}
const toggleProject = (name) => {
  const idx = expandedProjects.value.indexOf(name)
  if (idx >= 0) {
    expandedProjects.value.splice(idx, 1)
  } else {
    expandedProjects.value.push(name)
    // Auto-expand all modules when expanding a project
    const group = groupedItems.value.find(g => g.project_name === name)
    if (group) {
      expandedModuleSets.value = { ...expandedModuleSets.value, [name]: new Set(group.modules.map(m => m.module_name)) }
    }
  }
}
const toggleModule = (projectName, moduleName) => {
  const current = new Set(expandedModuleSets.value[projectName] || [])
  if (current.has(moduleName)) {
    current.delete(moduleName)
  } else {
    current.add(moduleName)
  }
  expandedModuleSets.value = { ...expandedModuleSets.value, [projectName]: current }
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
  if (!submitNote.value.trim()) {
    ElMessage.warning('请填写整改说明')
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
const doExport = () => {
  exporting.value = true
  const params = new URLSearchParams()
  if (statusFilter.value) params.set('status_filter', statusFilter.value)
  if (projectFilter.value) params.set('project_name', projectFilter.value)
  if (moduleFilter.value) params.set('module_name', moduleFilter.value)
  if (keyword.value) params.set('keyword', keyword.value)

  const xhr = new XMLHttpRequest()
  xhr.open('GET', `/api/v1/rectifications/export/excel?${params}`, true)
  xhr.responseType = 'blob'
  xhr.setRequestHeader('Authorization', `Bearer ${getAuthToken()}`)
  xhr.onload = () => {
    exporting.value = false
    if (xhr.status === 200) {
      const blob = xhr.response
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `整改记录_${new Date().toISOString().slice(0, 10)}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
      ElMessage.success('导出成功')
    } else {
      ElMessage.error(`导出失败(${xhr.status})`)
    }
  }
  xhr.onerror = () => {
    exporting.value = false
    ElMessage.error('网络错误，导出失败')
  }
  xhr.send()
}

onMounted(fetchData)
</script>

<style scoped>
/* ===== Page container ===== */
.page-container {
  max-width: 1400px;
  padding-bottom: 40px;
}

/* ===== Page header ===== */

/* ===== Button ===== */

/* ===== KPI row ===== */

/* ===== Tags ===== */
.kt {
  font-size: 11px;
  font-family: var(--mono);
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 3px;
}
.kt-ok { background: var(--ok-bg); color: var(--ok); }
.kt-warn { background: var(--warn-bg); color: var(--warn); }
.kt-err { background: var(--err-bg); color: var(--err); }
.kt-teal { background: var(--teal-50); color: var(--teal-700); }
.kt-muted { background: var(--bg-muted); color: var(--ink-600); }
.kt-blue { background: var(--blue-bg); color: var(--blue); }

/* ===== Filters ===== */
.filters {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.f-sel {
  padding: 7px 28px 7px 12px;
  border-radius: var(--r);
  font-size: 13px;
  font-weight: 500;
  color: var(--ink-600);
  border: 1px solid var(--ink-100);
  background: var(--bg-card);
  cursor: pointer;
  font-family: var(--sans);
  transition: all .12s;
  appearance: none;
  -webkit-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 16 16'%3E%3Cpath d='M4 6l4 4 4-4' stroke='%23a1a1aa' fill='none' stroke-width='1.8'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
}
.f-sel:hover { border-color: var(--ink-200); }
.f-input {
  padding: 7px 12px;
  border-radius: var(--r);
  font-size: 13px;
  font-weight: 400;
  color: var(--ink-800);
  border: 1px solid var(--ink-100);
  background: var(--bg-card);
  font-family: var(--sans);
  transition: all .12s;
  min-width: 180px;
}
.f-input::placeholder { color: var(--ink-400); }
.f-input:hover { border-color: var(--ink-200); }
.f-input:focus { outline: none; border-color: var(--blue); box-shadow: 0 0 0 3px rgba(37,99,235,.1); }
.f-sep { width: 1px; height: 24px; background: var(--ink-100); }

/* ===== Radio group ===== */
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
  transition: all .12s;
}
.radio-btn:hover { color: var(--ink-600); }
.radio-btn.on { background: var(--bg-card); color: var(--blue); box-shadow: 0 1px 2px rgba(0,0,0,.06); }

/* ===== Grouped view ===== */
.grouped-view {
  animation: fadeIn .3s var(--ease) .1s both;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.gv-project {
  background: var(--bg-card);
  border: 1px solid var(--ink-100);
  border-radius: var(--r-lg);
  margin-bottom: 10px;
  overflow: hidden;
}
.gv-project-hdr {
  padding: 12px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  transition: background .12s;
  border-bottom: 1px solid var(--ink-100);
}
.gv-project-hdr:hover { background: var(--bg-hover); }
.gv-project-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink-900);
  display: flex;
  align-items: center;
  gap: 8px;
}
.gv-project-name svg {
  width: 14px;
  height: 14px;
  stroke: var(--ink-400);
  fill: none;
  stroke-width: 2;
  transition: transform .15s;
}
.gv-project-name.open svg { transform: rotate(90deg); }
.gv-project-tags { display: flex; gap: 6px; }
.gv-project-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 3px;
}
.gv-module { border-top: 1px solid var(--ink-100); }
.gv-module-hdr {
  padding: 10px 20px 10px 34px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  transition: background .12s;
  background: var(--bg-muted);
}
.gv-module-hdr:hover { background: var(--bg-hover); }
.gv-module-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-600);
  display: flex;
  align-items: center;
  gap: 6px;
}
.gv-module-name svg {
  width: 12px;
  height: 12px;
  stroke: var(--ink-400);
  fill: none;
  stroke-width: 2;
  transition: transform .15s;
}
.gv-module-name.open svg { transform: rotate(90deg); }

/* ===== Table ===== */
.tbl { width: 100%; border-collapse: collapse; }
.tbl th {
  font-size: 12px;
  font-weight: 700;
  color: var(--ink-400);
  letter-spacing: .3px;
  text-align: center;
  padding: 10px 10px;
  background: var(--bg-muted);
  border-bottom: 1px solid var(--ink-100);
}
.tbl th:first-child { text-align: left; padding-left: 20px; }
.tbl td {
  font-size: 14px;
  font-weight: 500;
  text-align: center;
  padding: 12px 10px;
  border-bottom: 1px solid var(--ink-100);
  color: var(--ink-600);
}
.tbl td:first-child { text-align: left; padding-left: 20px; font-family: var(--mono); font-size: 12px; color: var(--ink-400); }
.tbl tbody tr { cursor: pointer; transition: background .08s; }
.tbl tbody tr:hover { background: var(--bg); }

/* ===== Status tags ===== */
.st {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}
.st-pending { background: var(--bg-muted); color: var(--ink-400); }
.st-progress { background: var(--warn-bg); color: var(--warn); }
.st-done { background: var(--ok-bg); color: var(--ok); }
.st-checking { background: var(--blue-bg); color: var(--blue); }
.st-ai-reject { background: var(--warn-bg); color: var(--warn); }
.st-ai-pass { background: var(--ok-bg); color: var(--ok); }
.st-review { background: var(--warn-bg); color: var(--warn); }

/* ===== Score/Confidence pills ===== */
.sp {
  display: inline-block;
  min-width: 32px;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: var(--mono);
  font-size: 13px;
  font-weight: 700;
  text-align: center;
}
.sp-hi { background: var(--ok-bg); color: var(--ok); }
.sp-mid { background: var(--warn-bg); color: var(--warn); }
.sp-lo { background: var(--err-bg); color: var(--err); }
.sp-na { color: var(--ink-200); }

/* ===== Confidence bar ===== */
.conf-wrap { display: flex; align-items: center; gap: 6px; justify-content: center; }
.conf-bar { width: 60px; height: 6px; background: var(--ink-100); border-radius: 3px; overflow: hidden; }
.conf-fill { height: 100%; border-radius: 3px; }
.conf-val { font-family: var(--mono); font-size: 12px; font-weight: 600; color: var(--ink-600); min-width: 32px; }

/* ===== Action buttons ===== */
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
  transition: background .1s;
}
.act:hover { background: var(--blue-bg); }
.act + .act { margin-left: 2px; }
.act-warn { color: var(--warn); }
.act-warn:hover { background: var(--warn-bg); }
.act-ok { color: var(--ok); }
.act-ok:hover { background: var(--ok-bg); }
.act-err { color: var(--err); }
.act-err:hover { background: var(--err-bg); }

/* ===== Dialogs ===== */
.submit-content { max-height: 70vh; overflow-y: auto; }
.submit-issue-info { margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #eee; }
.submit-section-title { font-size: 14px; font-weight: 600; color: var(--ink-900); margin-bottom: 10px; }
.submit-form { padding-top: 4px; }
.upload-tip { font-size: 12px; color: var(--ink-400); margin-top: 4px; }
.reject-notice { margin-top: 10px; padding: 10px 12px; background: var(--err-bg); border-radius: 6px; font-size: 13px; color: var(--err); display: flex; align-items: center; gap: 6px; }
.photo-grid { display: flex; gap: 6px; flex-wrap: wrap; }

.review-content { max-height: 70vh; overflow-y: auto; }
.review-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 16px; }
.review-side { background: var(--bg-muted); border-radius: 8px; padding: 14px; }
.review-side-title { font-size: 14px; font-weight: 600; color: var(--ink-900); margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid var(--ink-200); }
.review-info p { font-size: 13px; color: var(--ink-600); margin: 4px 0; }
.review-photos { margin-top: 10px; }
.review-photos-title { font-size: 12px; color: var(--ink-400); margin-bottom: 6px; }
.review-actions { display: flex; gap: 12px; align-items: flex-end; }
.review-actions .el-input { flex: 1; }
.review-btns { display: flex; gap: 8px; }

.ai-result-card { background: var(--blue-bg); border: 1px solid var(--blue-bg); border-radius: 8px; padding: 14px; margin-bottom: 16px; }
.ai-header { display: flex; align-items: center; gap: 6px; font-size: 14px; font-weight: 600; color: var(--blue); margin-bottom: 8px; }
.ai-body p { font-size: 13px; color: var(--ink-600); margin: 4px 0; line-height: 1.6; }

.detail-content { max-height: 70vh; overflow-y: auto; }
.detail-photos { margin-top: 16px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.detail-photo-section { background: var(--bg-muted); border-radius: 8px; padding: 12px; }
.detail-photo-title { font-size: 13px; font-weight: 500; color: var(--ink-600); margin-bottom: 8px; }
.review-record { margin-top: 12px; padding: 10px; background: var(--bg-muted); border-radius: 6px; font-size: 13px; color: var(--ink-600); }
</style>
