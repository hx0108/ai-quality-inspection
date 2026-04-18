<template>
  <div class="report-list-page">
    <van-nav-bar title="品质报告">
      <template #right>
        <van-icon name="user-o" size="20" @click="showUser = true" />
      </template>
    </van-nav-bar>

    <!-- 项目筛选 -->
    <div class="filter-bar">
      <van-dropdown-menu active-color="#2563eb">
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

        <van-cell-group v-else inset class="report-group">
          <van-cell
            v-for="report in filteredReports"
            :key="report.report_id"
            is-link
            @click="goToReport(report)"
          >
            <template #title>
              <div class="report-title">{{ report.project_name || '未知项目' }}</div>
            </template>
            <template #label>
              <div class="report-meta">
                <span>{{ report.report_id }}</span>
                <span>{{ formatDate(report.generated_at) }}</span>
              </div>
            </template>
            <template #value>
              <span :class="getScoreClass(report.total_score)">
                {{ report.total_score?.toFixed(2) }}
              </span>
            </template>
          </van-cell>
        </van-cell-group>
      </van-list>
    </van-pull-refresh>

    <van-tabbar v-model="activeTab" route>
      <van-tabbar-item icon="chart-trending-o" to="/dashboard">概览</van-tabbar-item>
      <van-tabbar-item icon="home-o" to="/tasks">任务</van-tabbar-item>
      <van-tabbar-item icon="todo-list-o" to="/reports">报告</van-tabbar-item>
      <van-tabbar-item icon="shield-o" to="/rectification">整改</van-tabbar-item>
      <van-tabbar-item icon="bar-chart-o" to="/analysis-mobile">分析</van-tabbar-item>
    </van-tabbar>

    <van-action-sheet v-model:show="showUser" title="个人信息">
      <div class="user-info">
        <van-cell title="用户名" :value="user.username" />
        <van-cell title="姓名" :value="user.real_name" />
        <van-cell title="角色" :value="getRoleText(user.role)" />
        <van-button block type="danger" @click="onLogout" style="margin-top: 20px">
          退出登录
        </van-button>
      </div>
    </van-action-sheet>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { getReportList } from '../../api/report'

const router = useRouter()
const authStore = useAuthStore()

const reports = ref([])
const loading = ref(false)
const finished = ref(false)  // 初始为 false，让 onLoad 可以执行
const refreshing = ref(false)
const activeTab = ref(2)
const showUser = ref(false)
const page = ref(1)
const projectFilter = ref('')
let loadLock = false  // 防止并发重复加载

const user = computed(() => authStore.user)

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

const onLogout = () => {
  authStore.logout()
}

const formatDate = (isoStr) => {
  if (!isoStr) return ''
  return isoStr.slice(0, 10)
}

const getScoreClass = (score) => {
  if (!score) return ''
  if (score >= 90) return 'score-excellent'
  if (score >= 80) return 'score-good'
  if (score >= 60) return 'score-normal'
  return 'score-poor'
}

const getRoleText = (role) => {
  const map = {
    admin: '管理员',
    inspector: '检查员',
    site_supervisor: '阵地督导',
    field_supervisor: '驻场经理',
    project_staff: '项目人员'
  }
  return map[role] || role
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
  color: #059669;
  font-weight: bold;
  font-size: 18px;
}

.score-good {
  color: #2563eb;
  font-weight: bold;
  font-size: 18px;
}

.score-normal {
  color: #d97706;
  font-weight: bold;
  font-size: 18px;
}

.score-poor {
  color: #dc2626;
  font-weight: bold;
  font-size: 18px;
}

.user-info {
  padding: 16px;
}
</style>
