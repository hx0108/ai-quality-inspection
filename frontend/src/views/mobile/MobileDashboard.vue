<template>
  <div class="dashboard-page">
    <!-- 品牌头（青绿渐变） -->
    <div class="hero">
      <div class="hero-row">
        <div class="hero-brand">
          <div class="brand-mark"><van-icon name="passed" /></div>
          <span class="brand-name">智能品质检查</span>
        </div>
        <div class="hero-acts">
          <van-badge v-if="unreadCount > 0" :content="unreadCount > 99 ? '99+' : unreadCount" max="99">
            <van-icon name="bell" size="20" color="#fff" @click="showNotifications = true" />
          </van-badge>
          <van-icon v-else name="bell" size="20" color="#fff" @click="showNotifications = true" />
          <van-icon name="user-o" size="20" color="#fff" @click="showUser = true" />
        </div>
      </div>
      <div class="hero-greet">
        <div class="greet-line">{{ greeting }}，{{ userName }}</div>
        <div class="greet-sub" @click="showCoverageSheet = true">
          本月覆盖率 {{ summary.coverage_rate || 0 }}% · {{ summary.monthly_checked_projects || 0 }}/{{ summary.total_projects || 0 }} 项目
          <van-icon name="arrow" />
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-center">
      <van-loading size="24px" vertical>加载中...</van-loading>
    </div>

    <template v-else>
      <!-- KPI 2×2 -->
      <div class="m-kpi-grid">
        <div class="m-kpi clickable" @click="openTaskSheet()">
          <div class="l">检查任务</div>
          <div class="v">{{ summary.total_tasks || 0 }}</div>
          <div class="t">
            <span class="ktag ktag-muted">待处理 {{ summary.pending_tasks || 0 }}</span>
            <span class="ktag ktag-brand">进行中 {{ summary.in_progress_tasks || 0 }}</span>
          </div>
        </div>
        <div class="m-kpi clickable" @click="openIssueSheet()">
          <div class="l">问题总数</div>
          <div class="v">{{ summary.total_issues || 0 }}</div>
          <div class="t">
            <span class="ktag ktag-err">严重 {{ summary.serious_issues || 0 }}</span>
            <span class="ktag ktag-warn">一般 {{ summary.general_issues || 0 }}</span>
          </div>
        </div>
        <div class="m-kpi clickable" @click="openRectSheet()">
          <div class="l">待整改</div>
          <div class="v" :class="{ 'v-err': (summary.pending_rectifications || 0) > 0 }">{{ summary.pending_rectifications || 0 }}</div>
          <div class="t"><span class="ktag ktag-muted">已提交 {{ summary.submitted_rectifications || 0 }}</span></div>
        </div>
        <div class="m-kpi clickable" @click="openRectSheet()">
          <div class="l">整改完成率</div>
          <div class="v">{{ summary.rectification_rate || 0 }}<small>%</small></div>
          <div class="t"><span class="ktag ktag-ok">已通过 {{ summary.approved_rectifications || 0 }}</span></div>
        </div>
      </div>

      <!-- 各项目得分 -->
      <div class="m-card">
        <div class="m-card-h"><span class="m-card-t">各项目得分</span><span class="m-card-d">点击查看模块</span></div>
        <div v-if="projectScores.length === 0" class="section-empty">暂无数据</div>
        <div v-else>
          <div v-for="p in projectScores" :key="p.project_name" class="proj-cell clickable" @click="openProjectDetail(p)">
            <span class="proj-ico"><van-icon name="shield-o" /></span>
            <div class="proj-gr">
              <div class="proj-name">{{ p.project_name }}</div>
              <div class="proj-sub">{{ moduleCount(p) }} 个模块</div>
            </div>
            <span class="sp-pill" :class="spClass(p.latest_score)">{{ p.latest_score != null ? Math.round(p.latest_score) : '–' }}</span>
            <van-icon name="arrow" class="proj-arrow" />
          </div>
        </div>
      </div>

      <!-- 问题按模块分布（单色条形） -->
      <div class="m-card">
        <div class="m-card-h"><span class="m-card-t">问题集中模块</span><span class="m-card-d">点击查看明细</span></div>
        <div v-if="issueByModule.length === 0" class="section-empty">暂无数据</div>
        <div v-else class="bar-list">
          <div v-for="(m, i) in topModules" :key="m.module_name" class="bar-row clickable" @click="openIssueSheet(m.module_name)">
            <span class="bar-lbl">{{ m.module_name }}</span>
            <span class="bar-track"><span class="bar-fill" :style="{ width: (m.count / maxModuleCount) * 100 + '%', background: `var(--chart-ramp-${Math.min(i + 1, 5)})` }" /></span>
            <span class="bar-val">{{ m.count }}</span>
          </div>
        </div>
      </div>

      <!-- 整改完成率 -->
      <div class="m-card">
        <div class="m-card-h"><span class="m-card-t">各项目整改完成率</span></div>
        <div v-if="rectStats.length === 0" class="section-empty">暂无数据</div>
        <div v-else ref="rectChartRef" style="width:100%; height:420px;"></div>
      </div>
    </template>

    <!-- 详情弹窗：检查任务 -->
    <van-action-sheet v-model:show="showTaskSheet" title="检查任务">
      <div class="popup-scroll">
        <van-cell v-for="t in popupTasks" :key="t.task_id"
          :title="t.project_name || '未命名项目'"
          :label="t.check_date ? (t.check_date + '  |  ' + (t.completed_modules || 0) + '个模块已完成') : ''"
          is-link @click="showTaskSheet=false; router.push('/tasks')">
          <template #value>
            <van-tag :type="t.status === 'completed' ? 'success' : t.status === 'in_progress' ? 'primary' : 'default'" size="medium">
              {{ t.status === 'completed' ? '已完成' : t.status === 'in_progress' ? '进行中' : '待处理' }}
            </van-tag>
          </template>
        </van-cell>
        <div v-if="popupTasks.length === 0" class="popup-empty">暂无任务</div>
      </div>
    </van-action-sheet>

    <!-- 详情弹窗：覆盖率 -->
    <van-action-sheet v-model:show="showCoverageSheet" title="项目覆盖率">
      <div class="popup-scroll">
        <div class="coverage-section">
          <div class="coverage-label">已检查项目 ({{ checkedProjectNames.length }})</div>
          <van-cell v-for="p in checkedProjectNames" :key="p" :title="p" icon="passed" />
          <div v-if="checkedProjectNames.length === 0" class="popup-empty-sm">暂无已检查项目</div>
        </div>
        <div class="coverage-section">
          <div class="coverage-label">未检查项目 ({{ uncheckedProjectNames.length }})</div>
          <van-cell v-for="p in uncheckedProjectNames" :key="p" :title="p" icon="todo-list-o" />
          <div v-if="uncheckedProjectNames.length === 0" class="popup-empty-sm">所有项目均已检查</div>
        </div>
      </div>
    </van-action-sheet>

    <!-- 详情弹窗：问题列表 -->
    <van-action-sheet v-model:show="showIssueSheet" :title="'问题列表' + (issueFilter ? ' - ' + issueFilter : '')">
      <div class="popup-scroll">
        <div v-for="iss in filteredIssues" :key="iss.issue_id || iss.id" class="issue-item">
          <div class="issue-item-top">
            <span class="issue-item-title">{{ iss.module_name || '' }}</span>
            <van-tag :type="iss.severity === '严重' ? 'danger' : iss.severity === '一般' ? 'warning' : 'default'" size="medium">{{ iss.severity }}</van-tag>
          </div>
          <div class="issue-item-check">{{ iss.item_name || iss.item_id || '' }}</div>
          <div class="issue-item-desc">{{ iss.description || '' }}</div>
        </div>
        <div v-if="filteredIssues.length === 0" class="popup-empty">暂无问题</div>
      </div>
    </van-action-sheet>

    <!-- 详情弹窗：整改列表 -->
    <van-action-sheet v-model:show="showRectSheet" title="整改记录">
      <div class="popup-scroll">
        <div v-if="rectLoading" class="popup-loading"><van-loading size="20px" /></div>
        <template v-else>
          <div v-for="r in popupRects" :key="r.rectification_id" class="issue-item">
            <div class="issue-item-top">
              <span class="issue-item-title">{{ r.module_name || '' }}</span>
              <van-tag :type="rectStatusTag(r.status)" size="medium">{{ rectStatusText(r.status) }}</van-tag>
            </div>
            <div class="issue-item-check">{{ r.item_name || r.item_id || '' }}</div>
            <div class="issue-item-desc">{{ r.description || '' }}</div>
          </div>
          <div v-if="popupRects.length === 0" class="popup-empty">暂无整改记录</div>
        </template>
      </div>
    </van-action-sheet>

    <!-- 详情弹窗：项目模块得分 -->
    <van-action-sheet v-model:show="showProjectSheet" :title="(selectedProject.project_name || '项目') + ' - 模块得分'">
      <div class="popup-scroll">
        <div v-for="(score, mod) in (selectedProject.modules || {})" :key="mod" class="module-score-row">
          <div class="module-score-top">
            <span class="module-score-name">{{ mod }}</span>
            <span class="module-score-val" :class="scoreTextClass(score)">{{ score != null ? score + '%' : '-' }}</span>
          </div>
          <van-progress :percentage="score || 0" :stroke-width="6" :show-pivot="false"
            :color="getProgressColor(score)" track-color="#ececf0" />
        </div>
        <div v-if="!selectedProject.modules || Object.keys(selectedProject.modules || {}).length === 0" class="popup-empty">暂无评分数据</div>
      </div>
    </van-action-sheet>

    <MobileTabbar />

    <MobileUserSheet v-model:show="showUser" />

    <!-- 通知面板 -->
    <van-popup v-model:show="showNotifications" position="right" class="notification-fullscreen" style="width: 100%; height: 100%">
      <div class="notification-page">
        <van-nav-bar title="通知" left-arrow @click-left="showNotifications = false">
          <template #right>
            <van-button v-if="notifications.length > 0" size="small" type="primary" plain round @click="onMarkAllRead">全部已读</van-button>
          </template>
        </van-nav-bar>
        <div v-if="notifications.length === 0" class="notification-empty">
          <van-empty description="暂无通知" />
        </div>
        <van-list v-else>
          <div v-for="n in notifications" :key="n.notification_id" class="notification-item" :class="{ unread: !n.is_read }" @click="onNotificationClick(n)">
            <div class="notification-icon" :class="getNotifyIconClass(n.notify_type)">
              <van-icon :name="getNotifyIcon(n.notify_type)" size="18" />
            </div>
            <div class="notification-body">
              <div class="notification-title">{{ n.title }}</div>
              <div class="notification-content">{{ n.content }}</div>
              <div class="notification-time">{{ formatTime(n.created_at) }}</div>
            </div>
            <van-badge v-if="!n.is_read" dot />
          </div>
        </van-list>
      </div>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import MobileUserSheet from '../../components/MobileUserSheet.vue'
import MobileTabbar from '../../components/MobileTabbar.vue'
import echarts from '../../utils/echarts'
import { useAuthStore } from '../../stores/auth'
import { getDashboardStats } from '../../api/stats'
import { getNotifications, getUnreadCount, markAsRead, markAllAsRead } from '../../api/notification'
import { getAllRectifications } from '../../api/rectification'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(true)
const summary = ref({})
const projectScores = ref([])
const issueByModule = ref([])
const rectStats = ref([])
const rectChartRef = ref(null)
let rectChart = null
const coverageDetail = ref({ checked_projects: [], unchecked_projects: [] })
const showUser = ref(false)
const showNotifications = ref(false)
const notifications = ref([])
const unreadCount = ref(0)

const userName = computed(() => authStore.user?.real_name || authStore.user?.username || '同事')
const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 12) return '早上好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const topModules = computed(() => [...issueByModule.value].sort((a, b) => b.count - a.count).slice(0, 5))
const maxModuleCount = computed(() => Math.max(1, ...topModules.value.map(m => m.count)))

const moduleCount = (p) => (p.modules ? Object.keys(p.modules).length : '–')

// Popup states - independent refs for reliability
const showTaskSheet = ref(false)
const showCoverageSheet = ref(false)
const showIssueSheet = ref(false)
const showRectSheet = ref(false)
const showProjectSheet = ref(false)
const popupTasks = ref([])
const popupIssues = ref([])
const popupRects = ref([])
const selectedProject = ref({})
const issueFilter = ref('')

// Direct methods called by click handlers
const openTaskSheet = () => {
  showTaskSheet.value = true
}

const openIssueSheet = (filterModule) => {
  issueFilter.value = filterModule || ''
  showIssueSheet.value = true
}

const rectLoading = ref(false)
const openRectSheet = async () => {
  showRectSheet.value = true
  if (popupRects.value.length > 0) return
  rectLoading.value = true
  try {
    const res = await getAllRectifications({})
    popupRects.value = res.items || []
  } catch (e) { console.error('load rects failed', e) }
  finally { rectLoading.value = false }
}

const openProjectDetail = (p) => {
  selectedProject.value = p
  showProjectSheet.value = true
}

// Coverage detail: backend returns objects, extract names
const checkedProjectNames = computed(() => {
  const list = coverageDetail.value.checked_projects || []
  return list.map(p => typeof p === 'string' ? p : (p.project_name || p.name || ''))
})
const uncheckedProjectNames = computed(() => {
  const list = coverageDetail.value.unchecked_projects || []
  return list.map(p => typeof p === 'string' ? p : (p.name || p.project_name || ''))
})

const filteredIssues = computed(() => {
  if (!issueFilter.value) return popupIssues.value
  return popupIssues.value.filter(i => i.module_name === issueFilter.value)
})

const renderRectChart = () => {
  if (!rectChartRef.value || !rectStats.value.length) return
  if (!rectChart) {
    rectChart = echarts.init(rectChartRef.value)
  }
  const data = [...rectStats.value].reverse()
  rectChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: '#ffffff',
      borderColor: '#e4e4e9',
      borderWidth: 1,
      textStyle: { color: '#2c2c38', fontSize: 12 },
      extraCssText: 'box-shadow: 0 4px 16px rgba(22,22,28,.10); border-radius: 8px;',
      formatter: (params) => {
        const name = params[0].name
        const approved = params.find(p => p.seriesName === '已整改')?.value || 0
        const pending = params.find(p => p.seriesName === '未整改')?.value || 0
        const total = approved + pending
        const rate = total > 0 ? ((approved / total) * 100).toFixed(1) : 0
        return `<div style="font-weight:600;margin-bottom:4px">${name}</div>` +
          `<div>已整改：<span style="color:#27945b;font-weight:600">${approved}</span></div>` +
          `<div>未整改：<span style="color:#61616d;font-weight:600">${pending}</span></div>` +
          `<div style="margin-top:4px;border-top:1px solid #ececf0;padding-top:4px">完成率：<b>${rate}%</b></div>`
      }
    },
    legend: {
      data: ['已整改', '未整改'],
      top: 0,
      right: 10,
      textStyle: { fontSize: 11, color: '#474753' },
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 12
    },
    grid: { left: 80, right: 30, top: 30, bottom: 10 },
    xAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#ececf0', type: 'dashed' } },
      axisLabel: { color: '#a4a4af', fontSize: 10 }
    },
    yAxis: {
      type: 'category',
      data: data.map(i => i.project_name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { fontSize: 11, color: '#474753', width: 70, overflow: 'truncate' }
    },
    series: [
      {
        name: '已整改',
        type: 'bar',
        stack: 'total',
        data: data.map(i => i.approved),
        itemStyle: { color: '#27945b' },
        barWidth: 14,
      },
      {
        name: '未整改',
        type: 'bar',
        stack: 'total',
        data: data.map(i => i.pending),
        itemStyle: { color: '#c9c9d1', borderRadius: [0, 4, 4, 0] },
        barWidth: 14,
      }
    ]
  })
}

const fetchStats = async () => {
  loading.value = true
  try {
    const res = await getDashboardStats()
    summary.value = res.summary || {}
    projectScores.value = res.project_latest_scores || []
    issueByModule.value = res.issue_by_module || []
    rectStats.value = res.project_rectification_stats || []
    coverageDetail.value = res.coverage_detail || { checked_projects: [], unchecked_projects: [] }
    popupTasks.value = res.recent_tasks || []
    popupIssues.value = res.issue_list || []
  } catch (e) {
    console.error('获取仪表盘数据失败:', e)
  } finally {
    loading.value = false
    await nextTick()
    renderRectChart()
  }
}

const fetchNotifications = async () => {
  try {
    const [listRes, countRes] = await Promise.all([
      getNotifications({ page: 1, page_size: 20 }),
      getUnreadCount()
    ])
    notifications.value = listRes.items || []
    unreadCount.value = countRes.unread_count || 0
  } catch (e) {
    console.error('获取通知失败:', e)
  }
}

const onNotificationClick = async (n) => {
  if (!n.is_read) {
    await markAsRead(n.notification_id)
    n.is_read = true
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  }
  if (n.ref_type === 'task' && n.ref_id) {
    showNotifications.value = false
    router.push(`/task/${n.ref_id}`)
  }
}

const onMarkAllRead = async () => {
  try {
    await markAllAsRead()
    notifications.value.forEach(n => n.is_read = true)
    unreadCount.value = 0
  } catch (e) {
    console.error('标记全部已读失败:', e)
  }
}

const getNotifyIcon = (type) => {
  const map = {
    task_assigned: 'user-o',
    inspection_complete: 'passed',
    scoring_complete: 'star-o',
    report_ready: 'description',
    rectification_reminder: 'warning-o',
    rectification_approved: 'checked',
    rectification_rejected: 'close'
  }
  return map[type] || 'bell'
}

const getNotifyIconClass = (type) => {
  if (type.includes('approved') || type.includes('complete')) return 'icon-success'
  if (type.includes('rejected') || type.includes('reminder')) return 'icon-danger'
  return 'icon-default'
}

const formatTime = (isoString) => {
  if (!isoString) return ''
  const date = new Date(isoString)
  const now = new Date()
  const diff = now - date
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return `${Math.floor(diff / 86400000)}天前`
}

// 0-100 分制三档（与设计系统 v2 对齐）
const spClass = (score) => {
  if (score == null) return 'sp-na'
  if (score >= 90) return 'sp-hi'
  if (score >= 70) return 'sp-mid'
  return 'sp-lo'
}

const scoreTextClass = (score) => {
  if (score == null) return ''
  if (score >= 90) return 't-hi'
  if (score >= 70) return 't-mid'
  return 't-lo'
}

const getProgressColor = (score) => {
  if (score >= 90) return '#27945b'
  if (score >= 70) return '#b07a12'
  return '#e5484d'
}

const rectStatusTag = (s) => {
  const map = { approved: 'success', pending: 'warning', submitted: 'primary', rejected: 'danger', ai_rejected: 'danger', ai_approved: 'success' }
  return map[s] || 'default'
}

const rectStatusText = (s) => {
  const map = { approved: '已通过', pending: '待整改', submitted: '审核中', rejected: '已驳回', ai_rejected: 'AI驳回', ai_approved: 'AI通过' }
  return map[s] || s
}

onMounted(() => { fetchStats(); fetchNotifications() })
onUnmounted(() => { rectChart?.dispose() })
</script>

<style scoped>
.dashboard-page {
  min-height: 100vh;
  background: var(--bg);
  padding-bottom: 66px;
  width: 100%;
  max-width: 100vw;
  box-sizing: border-box;
  overflow-x: hidden;
  font-family: var(--sans);
}

.loading-center {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 50vh;
}

/* ===== 品牌头 ===== */
.hero {
  background: linear-gradient(150deg, #14a094 0%, #0c7168 78%);
  padding: 18px 16px 20px;
  color: #fff;
}

.hero-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.hero-brand {
  display: flex;
  align-items: center;
  gap: 9px;
}

.brand-mark {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.16);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.22);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
}

.brand-name {
  font-size: 15.5px;
  font-weight: 800;
  letter-spacing: 0.2px;
}

.hero-acts {
  display: flex;
  align-items: center;
  gap: 16px;
}

.hero-greet {
  margin-top: 18px;
}

.greet-line {
  font-size: 19px;
  font-weight: 800;
  letter-spacing: -0.2px;
}

.greet-sub {
  margin-top: 5px;
  font-size: 12.5px;
  opacity: 0.85;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  cursor: pointer;
}

/* ===== KPI 2×2 ===== */
.m-kpi-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 10px;
  padding: 14px 14px 4px;
}

.m-kpi {
  background: var(--bg-card);
  border: 1px solid var(--ink-200);
  border-radius: 12px;
  padding: 13px 14px 11px;
  min-width: 0;
}

.m-kpi .l { font-size: 11.5px; font-weight: 600; color: var(--ink-500); }
.m-kpi .v {
  font-size: 26px;
  font-weight: 700;
  color: var(--ink-900);
  margin-top: 3px;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.5px;
}
.m-kpi .v small { font-size: 13px; font-weight: 600; color: var(--ink-400); }
.m-kpi .v.v-err { color: var(--err-strong); }
.m-kpi .t { display: flex; gap: 5px; margin-top: 7px; flex-wrap: wrap; }

/* ===== 卡片 ===== */
.m-card {
  background: var(--bg-card);
  border: 1px solid var(--ink-200);
  border-radius: 12px;
  margin: 12px 14px 0;
  overflow: hidden;
  min-width: 0;
}

.m-card-h {
  padding: 13px 14px 0;
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

.m-card-t { font-size: 14.5px; font-weight: 700; color: var(--ink-900); }
.m-card-d { font-size: 11.5px; color: var(--ink-400); }

.section-empty {
  font-size: 13px;
  color: var(--ink-400);
  text-align: center;
  padding: 18px 0;
}

/* 项目得分单元格 */
.proj-cell {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  border-bottom: 1px solid var(--ink-100);
}

.proj-cell:last-child { border-bottom: none; }

.proj-ico {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: var(--blue-bg);
  color: var(--brand-ink);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  flex-shrink: 0;
}

.proj-gr { flex: 1; min-width: 0; }
.proj-name { font-size: 14px; font-weight: 600; color: var(--ink-900); }
.proj-sub { font-size: 11.5px; color: var(--ink-400); margin-top: 1px; }

.sp-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 38px;
  height: 22px;
  padding: 0 6px;
  border-radius: 6px;
  font-size: 12.5px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.sp-pill.sp-hi { background: #edf6f0; color: var(--ok-strong); }
.sp-pill.sp-mid { background: #faf5e9; color: var(--warn-strong); }
.sp-pill.sp-lo { background: var(--err-bg); color: var(--err-strong); }
.sp-pill.sp-na { background: transparent; color: var(--ink-300); border: 1px dashed var(--ink-200); }

.proj-arrow { color: var(--ink-300); font-size: 14px; }

/* 模块条形 */
.bar-list { padding: 8px 14px 12px; }

.bar-row {
  display: grid;
  grid-template-columns: 64px 1fr 26px;
  align-items: center;
  gap: 8px;
  padding: 5px 0;
}

.bar-lbl {
  font-size: 12px;
  color: var(--ink-700);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bar-track {
  display: block;
  height: 14px;
  border-radius: 4px;
  background: var(--chart-bar-track);
  overflow: hidden;
}

.bar-fill {
  display: block;
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s var(--ease);
}

.bar-val {
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-700);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* 通知面板 */
.notification-page {
  height: 100vh;
  background: var(--bg);
}

.notification-empty { padding: 60px 0; }

.notification-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--ink-100);
}

.notification-item.unread { background: var(--blue-bg); }

.notification-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.notification-icon.icon-success { background: var(--ok-bg); color: var(--ok-strong); }
.notification-icon.icon-danger { background: var(--err-bg); color: var(--err-strong); }
.notification-icon.icon-default { background: var(--bg-muted); color: var(--ink-500); }

.notification-body { flex: 1; min-width: 0; }

.notification-title { font-size: 15px; font-weight: 500; color: var(--ink-900); margin-bottom: 4px; }
.notification-content {
  font-size: 13px;
  color: var(--ink-600);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.notification-time { font-size: 12px; color: var(--ink-400); margin-top: 4px; }

.clickable { cursor: pointer; transition: transform 0.1s, opacity 0.1s; }
.clickable:active { transform: scale(0.98); opacity: 0.85; }

/* Popup styles */
.popup-scroll { padding: 12px 16px; max-height: 60vh; overflow-y: auto; -webkit-overflow-scrolling: touch; }
.popup-title { font-size: 16px; font-weight: 600; text-align: center; margin-bottom: 12px; color: var(--ink-900); }
.popup-loading { display: flex; justify-content: center; padding: 40px 0; }
.popup-empty { text-align: center; color: var(--ink-400); padding: 40px 0; font-size: 14px; }
.popup-empty-sm { text-align: center; color: var(--ink-400); padding: 12px 0; font-size: 13px; }
.coverage-section { margin-bottom: 12px; }
.coverage-label { font-size: 13px; font-weight: 600; color: var(--ink-700); margin-bottom: 6px; padding-left: 4px; }
.module-score-row { margin-bottom: 12px; }
.module-score-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.module-score-name { font-size: 13px; color: var(--ink-700); }
.module-score-val { font-size: 14px; font-weight: 700; font-variant-numeric: tabular-nums; }
.module-score-val.t-hi { color: var(--ok-strong); }
.module-score-val.t-mid { color: var(--warn-strong); }
.module-score-val.t-lo { color: var(--err-strong); }

/* Issue / Rectification items */
.issue-item { padding: 10px 0; border-bottom: 1px solid var(--ink-100); }
.issue-item:last-child { border-bottom: none; }
.issue-item-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.issue-item-title { font-size: 14px; font-weight: 500; color: var(--ink-900); flex: 1; margin-right: 8px; }
.issue-item-check { font-size: 13px; color: var(--ink-600); margin-bottom: 2px; }
.issue-item-desc { font-size: 12px; color: var(--ink-500); line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
</style>

<!-- 非 scoped 样式：修复 Vant position="right" 弹窗的 translateY(-50%) 导致全屏弹窗内容不可见 -->
<style>
.notification-fullscreen.van-popup--right {
  top: 0 !important;
  bottom: 0 !important;
  transform: translate3d(0, 0, 0) !important;
}
.notification-fullscreen.van-popup-slide-right-enter-from,
.notification-fullscreen.van-popup-slide-right-leave-active {
  transform: translate3d(100%, 0, 0) !important;
}
.notification-fullscreen.van-popup-slide-right-enter-to,
.notification-fullscreen.van-popup-slide-right-leave-from {
  transform: translate3d(0, 0, 0) !important;
}
</style>
