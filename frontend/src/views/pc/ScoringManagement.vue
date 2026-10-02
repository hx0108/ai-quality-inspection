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

      <!-- KPI 统计卡片（原型结构：无图标，标签+大数字+轻量片） -->
      <div class="kpi-row cols-4">
        <div class="kpi">
          <div class="kpi-lbl">待复核</div>
          <div class="kpi-num" :class="{ 'kpi-err': (stats.pending_count || 0) > 0 }">{{ stats.pending_count || 0 }}</div>
          <div class="kpi-tags"><span class="ktag ktag-warn">优先处理</span></div>
        </div>
        <div class="kpi">
          <div class="kpi-lbl">已复核</div>
          <div class="kpi-num">{{ stats.reviewed_count || 0 }}</div>
          <div class="kpi-tags"><span class="ktag ktag-ok">完成</span></div>
        </div>
        <div class="kpi">
          <div class="kpi-lbl">已修改</div>
          <div class="kpi-num">{{ stats.edited_count || 0 }}</div>
          <div class="kpi-tags"><span class="ktag ktag-brand">人工修正</span></div>
        </div>
        <div class="kpi">
          <div class="kpi-lbl">低置信度占比</div>
          <div class="kpi-num">{{ stats.low_confidence_rate || 0 }}<span class="kpi-unit">%</span></div>
          <div class="kpi-tags"><span class="ktag ktag-muted">建议复核</span></div>
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
              <th>Jev 复核</th>
              <th>评分时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="tableLoading">
              <td colspan="9" style="text-align:center;padding:40px;color:var(--ink-400)">加载中...</td>
            </tr>
            <tr v-else-if="items.length === 0">
              <td colspan="9" style="text-align:center;padding:40px;color:var(--ink-400)">暂无数据</td>
            </tr>
            <tr v-for="row in items" :key="row.scoring_id || row.task_id">
              <td>{{ row.task_id }}</td>
              <td style="text-align:left;font-family:var(--sans);font-weight:600;color:var(--ink-900)">{{ row.project_name || '-' }}</td>
              <td>{{ row.module_name || '-' }}</td>
              <td style="text-align:left">{{ row.item_name || '-' }}</td>
              <td><span class="sp" :class="scoreClass(row.score)">{{ row.score }}</span></td>
              <td><span class="kt" :class="confidenceClass(row.confidence_score)">{{ row.confidence_score }}</span></td>
              <td>
                <span v-if="row.jev_direction" class="kt" :class="jevClass(row.jev_direction)">{{ row.jev_direction }} {{ row.jev_confidence != null ? Number(row.jev_confidence).toFixed(2) : '' }}</span>
                <span v-else style="color:var(--ink-300)">—</span>
              </td>
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
            <el-descriptions-item label="Jev 复核" :span="reviewItem.jev_direction ? 1 : 2">
              <template v-if="reviewItem.jev_direction">
                <el-tag :type="reviewItem.jev_direction === '正确' ? 'success' : 'warning'" size="small">
                  {{ reviewItem.jev_direction }}
                </el-tag>
                <span v-if="reviewItem.jev_confidence != null" style="margin-left:6px">给分正确概率 {{ Number(reviewItem.jev_confidence).toFixed(2) }}</span>
              </template>
              <span v-else style="color:var(--ink-300)">未复核（Jev 未启用或无数据）</span>
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
              <el-input-number v-model="reviewScore" :min="reviewMin" :max="reviewMax" :step="0.5" :precision="1" style="width:200px" />
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
const moduleOptions = ref([])  // 动态：从结果数据中聚合实际出现的模块名（兼容任意标准）

// 改分上下限：砺质扣分模块允许负分；计分项上限=单项max_score；蝶城0-5
const reviewMax = computed(() => {
  const it = reviewItem.value
  if (!it) return 5
  if (it.module_role === 'deduction') return 0
  return it.item_max_score ?? it.module_max_score ?? 5
})
const reviewMin = computed(() => (reviewItem.value?.module_role === 'deduction' ? -100 : 0))

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
    // 动态聚合当前结果中出现的模块名（兼容蝶城/非蝶城/砺质）
    const names = [...new Set(items.value.map(i => i.module_name).filter(Boolean))]
    moduleOptions.value = names
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

function jevClass(direction) {
  if (direction === '正确') return 'kt-blue'
  if (direction === '偏低') return 'kt-warn'
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

/* phdr / kpi-row / kpi / ktag 样式由全局 design-upgrade.css v2 提供 */

/* ==================== Filters ==================== */
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
