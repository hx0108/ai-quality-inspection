<template>
  <div class="report-list-page">
    <van-nav-bar title="品质报告">
      <template #right>
        <van-icon name="user-o" size="20" @click="showUser = true" />
      </template>
    </van-nav-bar>

    <!-- 项目筛选 -->
    <div class="filter-bar">
      <van-dropdown-menu active-color="var(--blue)">
        <van-dropdown-item v-model="projectFilter" :options="projectOptions" @change="filterReports" />
      </van-dropdown-menu>
    </div>

    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <van-list
        v-model:loading="loading"
        :finished="finished"
        finished-text="没有更多了"
        @load="onLoad"
      >
        <van-empty v-if="!loading && filteredReports.length === 0" description="暂无检查报告">
          <template #image>
            <van-icon name="description" size="80" color="#dcdee0" />
          </template>
        </van-empty>

        <div v-else class="report-cards">
          <div
            v-for="report in filteredReports"
            :key="report.report_id"
            class="rp-card"
            @click="goToReport(report)"
          >
            <div class="rp-top">
              <span class="rp-title">{{ report.project_name || '未知项目' }} · 品质检查报告</span>
              <span class="sp-pill" :class="getScoreClass(report.total_score)">
                {{ report.total_score?.toFixed(1) }}
              </span>
            </div>
            <div class="rp-meta">
              <span class="rp-id">{{ report.report_id }}</span>
              <span>{{ formatDate(report.generated_at) }}</span>
              <span class="rp-link">查看报告</span>
            </div>
          </div>
        </div>
      </van-list>
    </van-pull-refresh>

    <MobileTabbar />

    <MobileUserSheet v-model:show="showUser" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import MobileUserSheet from '../../components/MobileUserSheet.vue'
import MobileTabbar from '../../components/MobileTabbar.vue'
import { getReportList } from '../../api/report'

const router = useRouter()

const reports = ref([])
const loading = ref(false)
const finished = ref(false)  // 初始为 false，让 onLoad 可以执行
const refreshing = ref(false)
const showUser = ref(false)
const page = ref(1)
const projectFilter = ref('')
let loadLock = false  // 防止并发重复加载

const projectOptions = computed(() => {
  const projects = [...new Set(reports.value.map(r => r.project_name).filter(Boolean))].sort()
  return [{ text: '全部项目', value: '' }, ...projects.map(p => ({ text: p, value: p }))]
})

const filteredReports = computed(() => {
  if (!projectFilter.value) return reports.value
  return reports.value.filter(r => r.project_name === projectFilter.value)
})

const filterReports = () => {
  // computed 自动处理
}

const onLoad = async () => {
  if (loadLock || finished.value) return
  loadLock = true
  try {
    const res = await getReportList({ page: page.value, page_size: 20 })
    console.log('[ReportList] API response:', res)
    const items = res.items || []
    reports.value = page.value === 1 ? items : [...reports.value, ...items]
    finished.value = reports.value.length >= res.total
    page.value++
    if (res.total === 0) {
      console.log('[ReportList] No reports found')
    }
  } catch (e) {
    console.error('[ReportList] Fetch error:', e)
    finished.value = true
  } finally {
    loading.value = false
    loadLock = false
  }
}

const onRefresh = async () => {
  page.value = 1
  finished.value = true  // 重置，等 onLoad 判断
  reports.value = []
  await onLoad()
  refreshing.value = false
}

const goToReport = (report) => {
  router.push(`/report/${report.task_id}`)
}

const onBack = () => {
  router.push('/tasks')
}

const formatDate = (isoStr) => {
  if (!isoStr) return ''
  return isoStr.slice(0, 10)
}

const getScoreClass = (score) => {
  if (!score) return 'sp-na'
  if (score >= 90) return 'sp-hi'
  if (score >= 70) return 'sp-mid'
  return 'sp-lo'
}

onMounted(() => {
  onLoad()
})
</script>

<style scoped>
.report-list-page {
  min-height: 100vh;
  background: #f5f7fa;
  padding-bottom: 60px;
}

.filter-bar {
  position: sticky;
  top: 0;
  z-index: 10;
}

.report-group {
  margin: 12px;
}

.report-group :deep(.van-cell) {
  border-radius: 10px;
  margin-bottom: 8px;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.04);
}

.report-title {
  font-weight: 600;
  font-size: 15px;
  color: #1a1d26;
}

.report-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #9ba3af;
  margin-top: 4px;
  white-space: nowrap;
  overflow: hidden;
}

.report-meta span {
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 1;
  min-width: 0;
}

.score-excellent {
  color: var(--ok-strong);
  font-weight: bold;
  font-size: 18px;
}

.score-good {
  color: var(--blue);
  font-weight: bold;
  font-size: 18px;
}

.score-normal {
  color: var(--orange);
  font-weight: bold;
  font-size: 18px;
}

.score-poor {
  color: var(--err);
  font-weight: bold;
  font-size: 18px;
}

/* ===== 报告卡（原型形态） ===== */
.report-cards { padding: 10px 14px; }

.rp-card {
  background: var(--bg-card);
  border: 1px solid var(--ink-200);
  border-radius: 12px;
  padding: 13px 14px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: transform 0.12s;
}
.rp-card:active { transform: scale(0.98); }

.rp-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.rp-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink-900);
  line-height: 1.45;
  min-width: 0;
}

.rp-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  font-size: 12px;
  color: var(--ink-500);
  font-variant-numeric: tabular-nums;
}

.rp-id { font-family: var(--mono); font-size: 11px; color: var(--ink-400); }

.rp-link {
  margin-left: auto;
  color: var(--blue);
  font-weight: 600;
}

/* 分数胶囊（三档） */
.sp-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  height: 22px;
  padding: 0 6px;
  border-radius: 6px;
  font-size: 12.5px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}
.sp-pill.sp-hi { background: #edf6f0; color: var(--ok-strong); }
.sp-pill.sp-mid { background: #faf5e9; color: var(--warn-strong); }
.sp-pill.sp-lo { background: var(--err-bg); color: var(--err-strong); }
.sp-pill.sp-na { background: transparent; color: var(--ink-300); border: 1px dashed var(--ink-200); }
</style>
