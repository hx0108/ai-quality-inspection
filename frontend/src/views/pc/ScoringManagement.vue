<template>
  <div class="scoring-page">
    <el-skeleton v-if="loading" :rows="6" animated class="loading-wrap" />

    <template v-else>
      <!-- 页面头部 -->
      <div class="phdr">
        <div>
          <h1>评分复核</h1>
          <div class="phdr-sub">AI评分复核与人工修正</div>
        </div>
      </div>

      <!-- KPI 统计卡片 -->
      <div class="kpi-row cols-4">
        <div class="kpi">
          <div class="kpi-icon" style="background:var(--warn-bg);color:var(--warn)">
            <el-icon :size="18"><Warning /></el-icon>
          </div>
          <div class="kpi-body">
            <span class="kpi-label">待复核</span>
            <span class="kpi-val">{{ stats.pending_count || 0 }}<span class="kpi-unit">件</span></span>
          </div>
        </div>
        <div class="kpi">
          <div class="kpi-icon" style="background:var(--ok-bg);color:var(--ok)">
            <el-icon :size="18"><CircleCheck /></el-icon>
          </div>
          <div class="kpi-body">
            <span class="kpi-label">已复核</span>
            <span class="kpi-val">{{ stats.reviewed_count || 0 }}<span class="kpi-unit">件</span></span>
          </div>
        </div>
        <div class="kpi">
          <div class="kpi-icon" style="background:var(--blue-bg);color:var(--blue)">
            <el-icon :size="18"><Edit /></el-icon>
          </div>
          <div class="kpi-body">
            <span class="kpi-label">已修改</span>
            <span class="kpi-val">{{ stats.edited_count || 0 }}<span class="kpi-unit">件</span></span>
          </div>
        </div>
        <div class="kpi">
          <div class="kpi-icon" style="background:var(--bg-muted);color:var(--ink-600)">
            <el-icon :size="18"><DataLine /></el-icon>
          </div>
          <div class="kpi-body">
            <span class="kpi-label">低置信度占比</span>
            <span class="kpi-val">{{ stats.low_confidence_rate || 0 }}<span class="kpi-unit">%</span></span>
          </div>
        </div>
      </div>

      <!-- 筛选栏 -->
      <div class="filters">
        <div class="radio-group">
          <div class="radio-btn" :class="{ on: activeTab === 'pending' }" @click="activeTab = 'pending'; onTabChange()">待复核</div>
          <div class="radio-btn" :class="{ on: activeTab === 'reviewed' }" @click="activeTab = 'reviewed'; onTabChange()">已复核</div>
          <div class="radio-btn" :class="{ on: activeTab === 'edited' }" @click="activeTab = 'edited'; onTabChange()">已修改</div>
        </div>
        <select class="f-sel" v-model="filterModule" @change="fetchData">
          <option value="">按模块筛选</option>
          <option v-for="m in moduleOptions" :key="m" :value="m">{{ m }}</option>
        </select>
      </div>

      <!-- 评分表格 -->
      <div class="card">
        <table class="tbl">
          <thead>
            <tr>
              <th>任务ID</th>
              <th>项目</th>
              <th>模块</th>
              <th>检查项</th>
              <th>AI评分</th>
              <th>置信度</th>
              <th>评分时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="tableLoading">
              <td colspan="8" style="text-align:center;padding:40px;color:var(--ink-400)">加载中...</td>
            </tr>
            <tr v-else-if="items.length === 0">
              <td colspan="8" style="text-align:center;padding:40px;color:var(--ink-400)">暂无数据</td>
            </tr>
            <tr v-for="row in items" :key="row.scoring_id || row.task_id">
              <td>{{ row.task_id }}</td>
              <td style="text-align:left;font-family:var(--sans);font-weight:600;color:var(--ink-900)">{{ row.project_name || '-' }}</td>
              <td>{{ row.module_name || '-' }}</td>
              <td style="text-align:left">{{ row.item_name || '-' }}</td>
              <td><span class="sp" :class="scoreClass(row.score)">{{ row.score }}</span></td>
              <td><span class="kt" :class="confidenceClass(row.confidence_score)">{{ row.confidence_score }}</span></td>
              <td>{{ row.scored_at || '-' }}</td>
              <td>
                <button class="act" @click="openReview(row)">复核</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="pagi">
          <div class="pagi-info">共 <b>{{ total }}</b> 条</div>
          <div class="pagi-btns">
            <button class="pg" :disabled="page <= 1" @click="goPage(page - 1)"><svg viewBox="0 0 16 16"><path d="M10 3L5 8l5 5"/></svg></button>
            <button v-for="p in pageNumbers" :key="p" class="pg" :class="{ on: p === page }" @click="goPage(p)">{{ p }}</button>
            <button class="pg" :disabled="page >= totalPages" @click="goPage(page + 1)"><svg viewBox="0 0 16 16"><path d="M6 3l5 5-5 5"/></svg></button>
          </div>
        </div>
      </div>

      <!-- 复核弹窗 -->
      <el-dialog v-model="reviewVisible" title="评分复核" width="600px" destroy-on-close>
        <div v-if="reviewItem" class="review-form">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="模块">{{ reviewItem.module_name }}</el-descriptions-item>
            <el-descriptions-item label="检查项">{{ reviewItem.item_name }}</el-descriptions-item>
            <el-descriptions-item label="项目">{{ reviewItem.project_name }}</el-descriptions-item>
            <el-descriptions-item label="置信度">
              <el-tag :type="reviewItem.confidence_score >= 0.6 ? 'warning' : 'danger'" size="small">
                {{ reviewItem.confidence_score }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>

          <div class="review-section">
            <div class="review-label">AI评分依据</div>
            <div class="review-content">{{ reviewItem.scoring_basis || '无' }}</div>
          </div>

          <div class="review-section">
            <div class="review-label">改进建议</div>
            <div class="review-content">{{ reviewItem.improvement_suggestion || '无' }}</div>
          </div>

          <el-divider />

          <el-form label-position="top">
            <el-form-item label="修改评分">
              <el-input-number v-model="reviewScore" :min="0" :max="5" :step="0.5" :precision="1" style="width:200px" />
            </el-form-item>
            <el-form-item label="复核备注">
              <el-input v-model="reviewNote" type="textarea" :rows="2" placeholder="可选：说明修改原因" />
            </el-form-item>
          </el-form>
        </div>

        <template #footer>
          <el-button @click="confirmReview(false)">确认AI评分</el-button>
          <el-button type="primary" @click="confirmReview(true)">修改并提交</el-button>
        </template>
      </el-dialog>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Warning, CircleCheck, Edit, DataLine } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getAllPendingReviews, editScore } from '../../api/scoring'

const loading = ref(true)
const tableLoading = ref(false)
const activeTab = ref('pending')
const filterModule = ref('')
const page = ref(1)
const total = ref(0)
const items = ref([])
const stats = ref({})
const moduleOptions = ref(['保洁管理', '秩序管理', '安全管理', '环境管理', '机电运维', '设施维护', '综合管理', '财务管理'])

const reviewVisible = ref(false)
const reviewItem = ref(null)
const reviewScore = ref(0)
const reviewNote = ref('')

async function fetchData() {
  tableLoading.value = true
  try {
    const res = await getAllPendingReviews({
      page: page.value,
      page_size: 20,
      tab: activeTab.value,
      module_name: filterModule.value || undefined,
    })
    const data = res.data || res
    items.value = data.items || []
    total.value = data.total || 0
    stats.value = data.stats || {}
  } catch (e) {
    console.error('获取评分数据失败:', e)
  } finally {
    tableLoading.value = false
  }
}

function onTabChange() {
  page.value = 1
  fetchData()
}

function openReview(row) {
  reviewItem.value = row
  reviewScore.value = row.score
  reviewNote.value = ''
  reviewVisible.value = true
}

async function confirmReview(withEdit) {
  if (!reviewItem.value) return

  try {
    if (withEdit && reviewScore.value !== reviewItem.value.score) {
      await editScore(reviewItem.value.scoring_id, {
        score: reviewScore.value,
        edit_reason: reviewNote.value || '人工复核修改',
      })
      ElMessage.success('评分已修改')
    } else {
      await editScore(reviewItem.value.scoring_id, {
        score: reviewItem.value.score,
        edit_reason: '人工复核确认',
      })
      ElMessage.success('已确认AI评分')
    }
    reviewVisible.value = false
    fetchData()
  } catch (e) {
    ElMessage.error('操作失败：' + (e.message || '未知错误'))
  }
}

onMounted(async () => {
  loading.value = true
  try {
    await fetchData()
  } finally {
    loading.value = false
  }
})

// ===== Template helpers =====
function scoreClass(score) {
  if (score >= 4) return 'sp-hi'
  if (score >= 2.5) return 'sp-mid'
  return 'sp-lo'
}

function confidenceClass(confidence) {
  if (confidence >= 0.85) return 'kt-blue'
  if (confidence >= 0.6) return 'kt-warn'
  return 'kt-err'
}

const totalPages = computed(() => Math.ceil(total.value / 20) || 1)

const pageNumbers = computed(() => {
  const pages = []
  const tp = totalPages.value
  const cur = page.value
  let start = Math.max(1, cur - 1)
  let end = Math.min(tp, start + 2)
  if (end - start < 2) start = Math.max(1, end - 2)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

function goPage(p) {
  if (p < 1 || p > totalPages.value) return
  page.value = p
  fetchData()
}
</script>

<style scoped>
/* ==================== Page Container ==================== */
.scoring-page {
  max-width: 1400px;
  padding-bottom: 40px;
}

.loading-wrap { padding: 40px 0; }

/* ==================== Page Header (prototype .phdr) ==================== */
.phdr {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 20px;
}

.phdr h1 {
  font-size: 22px;
  font-weight: 800;
  color: var(--ink-900);
  letter-spacing: -0.4px;
  margin: 0;
}

.phdr-sub {
  font-size: 13px;
  color: var(--ink-400);
  margin-top: 3px;
}

.phdr-acts {
  display: flex;
  gap: 8px;
}

/* ==================== KPI Row (prototype .kpi-row) ==================== */
.kpi-row {
  display: grid;
  gap: 12px;
  margin-bottom: 20px;
}

.kpi-row.cols-4 {
  grid-template-columns: repeat(4, 1fr);
}

.kpi {
  background: var(--bg-card);
  border: 1px solid var(--ink-100);
  border-radius: var(--r-lg);
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;
  overflow: hidden;
  transition: all 0.15s var(--ease);
  animation: fadeInUp 0.3s var(--ease) both;
}

.kpi:nth-child(2) { animation-delay: 30ms; }
.kpi:nth-child(3) { animation-delay: 60ms; }
.kpi:nth-child(4) { animation-delay: 90ms; }

.kpi::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--ink-200), var(--ink-100));
}

.kpi:first-child::before { background: linear-gradient(90deg, var(--warn), #fbbf24); }
.kpi:nth-child(2)::before { background: linear-gradient(90deg, var(--ok), #34d399); }
.kpi:nth-child(3)::before { background: linear-gradient(90deg, var(--blue), #60a5fa); }
.kpi:nth-child(4)::before { background: linear-gradient(90deg, var(--ink-600), #a78bfa); }

.kpi:hover {
  border-color: var(--ink-200);
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.kpi-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.kpi-body { flex: 1; min-width: 0; }

.kpi-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-400);
  display: block;
  margin-bottom: 6px;
}

.kpi-val {
  font-family: var(--mono);
  font-size: 32px;
  font-weight: 700;
  color: var(--ink-900);
  display: block;
  line-height: 1;
  letter-spacing: -1.5px;
}

.kpi-unit {
  font-family: var(--mono);
  font-size: 16px;
  font-weight: 500;
  color: var(--ink-400);
}

/* ==================== Filters (prototype .filters) ==================== */
.filters {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

/* ==================== Radio Group (prototype .radio-group) ==================== */
.radio-group {
  display: flex;
  border: 1px solid var(--ink-100);
  border-radius: var(--r);
  overflow: hidden;
}

.radio-btn {
  padding: 7px 16px;
  font-size: 13px;
  font-weight: 500;
  color: var(--ink-600);
  cursor: pointer;
  background: var(--bg-card);
  border: none;
  border-right: 1px solid var(--ink-100);
  font-family: var(--sans);
  transition: all 0.12s;
  user-select: none;
}

.radio-btn:last-child {
  border-right: none;
}

.radio-btn:hover {
  background: var(--bg-muted);
}

.radio-btn.on {
  background: var(--blue);
  color: #fff;
  font-weight: 600;
}

/* ==================== Select (prototype .f-sel) ==================== */
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
  transition: all 0.12s;
  appearance: none;
  -webkit-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 16 16'%3E%3Cpath d='M4 6l4 4 4-4' stroke='%23a1a1aa' fill='none' stroke-width='1.8'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
}

.f-sel:hover {
  border-color: var(--ink-200);
}

/* ==================== Card (prototype .card) ==================== */
.card {
  background: var(--bg-card);
  border: 1px solid var(--ink-100);
  border-radius: var(--r-lg);
  overflow: hidden;
  animation: fadeInUp 0.3s var(--ease) 0.05s both;
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
  padding: 10px 10px;
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
  transition: background 0.08s;
}

.tbl tbody tr:hover {
  background: var(--bg);
}

/* ==================== Score pills (prototype .sp) ==================== */
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

.sp-hi {
  background: var(--ok-bg);
  color: var(--ok);
}

.sp-mid {
  background: var(--warn-bg);
  color: var(--warn);
}

.sp-lo {
  background: var(--err-bg);
  color: var(--err);
}

/* ==================== Tags (prototype .kt) ==================== */
.kt {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 12px;
  font-weight: 600;
}

.kt-blue {
  background: var(--blue-bg);
  color: var(--blue);
}

.kt-warn {
  background: var(--warn-bg);
  color: var(--warn);
}

.kt-muted {
  background: var(--bg-muted);
  color: var(--ink-600);
}

.kt-err {
  background: var(--err-bg);
  color: var(--err);
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

.act-ok {
  color: var(--ok);
}

.act-ok:hover {
  background: var(--ok-bg);
}

.act-err {
  color: var(--err);
}

.act-err:hover {
  background: var(--err-bg);
}

/* ==================== Pagination (prototype .pagi) ==================== */
.pagi {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-top: 1px solid var(--ink-100);
}

.pagi-info {
  font-size: 12px;
  color: var(--ink-400);
}

.pagi-info b {
  color: var(--ink-800);
}

.pagi-btns {
  display: flex;
  gap: 3px;
}

.pg {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--r-sm);
  font-size: 13px;
  font-weight: 500;
  color: var(--ink-600);
  cursor: pointer;
  border: 1px solid var(--ink-100);
  background: var(--bg-card);
  transition: all 0.1s;
  font-family: var(--sans);
}

.pg:hover:not(:disabled) {
  background: var(--bg-muted);
}

.pg.on {
  background: var(--blue);
  color: #fff;
  border-color: var(--blue);
}

.pg:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pg svg {
  width: 12px;
  height: 12px;
  stroke: currentColor;
  fill: none;
  stroke-width: 2;
}

/* ==================== Review Section ==================== */
.review-section {
  margin-top: 16px;
}

.review-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-400);
  margin-bottom: 6px;
}

.review-content {
  font-size: 13px;
  color: var(--ink-900);
  background: var(--bg-muted);
  padding: 10px 12px;
  border-radius: var(--r);
  line-height: 1.6;
}

/* ==================== Animations ==================== */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ==================== Responsive ==================== */
@media (max-width: 900px) {
  .kpi-row.cols-4 { grid-template-columns: repeat(2, 1fr); }
  .filters { flex-direction: column; align-items: flex-start; }
  .radio-group { width: 100%; }
  .radio-btn { flex: 1; text-align: center; }
}
</style>
