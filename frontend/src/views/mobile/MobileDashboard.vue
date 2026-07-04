<template>
  <div class="dashboard-page">
    <van-nav-bar title="数据概览">
      <template #left>
        <van-badge v-if="unreadCount > 0" :content="unreadCount > 99 ? '99+' : unreadCount" max="99">
          <van-icon name="bell" size="20" @click="showNotifications = true" />
        </van-badge>
        <van-icon v-else name="bell" size="20" @click="showNotifications = true" />
      </template>
      <template #right>
        <van-icon name="user-o" size="20" @click="showUser = true" />
      </template>
    </van-nav-bar>

    <div v-if="loading" class="loading-center">
      <van-loading size="24px" vertical>加载中...</van-loading>
    </div>

    <template v-else>
      <!-- 统计卡片（用 m-stat-grid 独立命名，避免被全局 design-upgrade.css 的 stat-grid 3列规则覆盖）-->
      <div class="m-stat-grid">
        <div class="stat-card clickable" style="--accent: #2563eb; --accent-light: #EFF6FF" @click="openTaskSheet()">
          <div class="stat-icon" style="background: var(--accent-light); color: var(--accent)">
            <van-icon name="todo-list-o" size="22" />
          </div>
          <div class="stat-body">
            <div class="stat-num">{{ summary.total_tasks || 0 }}</div>
            <div class="stat-label">检查任务</div>
            <div class="stat-tags">
              <span class="stat-tag tag-warn">{{ summary.pending_tasks || 0 }}待处理</span>
              <span class="stat-tag tag-blue">{{ summary.in_progress_tasks || 0 }}进行中</span>
            </div>
          </div>
        </div>
        <div class="stat-card clickable" style="--accent: #059669; --accent-light: #ECFDF5" @click="showCoverageSheet=true">
          <div class="stat-icon" style="background: var(--accent-light); color: var(--accent)">
            <van-icon name="chart-trending-o" size="22" />
          </div>
          <div class="stat-body">
            <div class="stat-num">{{ summary.coverage_rate || 0 }}<span class="stat-unit">%</span></div>
            <div class="stat-label">本月覆盖率</div>
            <div class="stat-tags">
              <span class="stat-tag tag-green">{{ summary.monthly_checked_projects || 0 }}/{{ summary.total_projects || 0 }}项目</span>
            </div>
          </div>
        </div>
        <div class="stat-card clickable" style="--accent: #f59e0b; --accent-light: #FFFBEB" @click="openRectSheet()">
          <div class="stat-icon" style="background: var(--accent-light); color: var(--accent)">
            <van-icon name="clock-o" size="22" />
          </div>
          <div class="stat-body">
            <div class="stat-num">{{ summary.pending_rectifications || 0 }}</div>
            <div class="stat-label">待整改</div>
            <div class="stat-tags">
              <span class="stat-tag tag-warn">已提交 {{ summary.submitted_rectifications || 0 }}</span>
            </div>
          </div>
        </div>
        <div class="stat-card clickable" style="--accent: #dc2626; --accent-light: #FEF2F2" @click="openIssueSheet()">
          <div class="stat-icon" style="background: var(--accent-light); color: var(--accent)">
            <van-icon name="warning-o" size="22" />
          </div>
          <div class="stat-body">
            <div class="stat-num">{{ summary.total_issues || 0 }}</div>
            <div class="stat-label">发现问题</div>
            <div class="stat-tags">
              <span class="stat-tag tag-red">{{ summary.serious_issues || 0 }}严重</span>
              <span class="stat-tag tag-orange">{{ summary.general_issues || 0 }}一般</span>
              <span class="stat-tag tag-gray">{{ summary.minor_issues || 0 }}轻微</span>
            </div>
          </div>
        </div>
        <div class="stat-card clickable" style="--accent: #059669; --accent-light: #ECFDF5" @click="openRectSheet()">
          <div class="stat-icon" style="background: var(--accent-light); color: var(--accent)">
            <van-icon name="passed" size="22" />
          </div>
          <div class="stat-body">
            <div class="stat-num">{{ summary.rectification_rate || 0 }}<span class="stat-unit">%</span></div>
            <div class="stat-label">整改完成率</div>
            <div class="stat-tags">
              <span class="stat-tag tag-green">已通过 {{ summary.approved_rectifications || 0 }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 各项目得分 -->
      <div class="section-card">
        <div class="section-title">各项目得分</div>
        <div v-if="projectScores.length === 0" class="section-empty">暂无数据</div>
        <div v-for="p in projectScores" :key="p.project_name" class="score-row" @click="openProjectDetail(p)">
          <div class="score-row-top">
            <span class="score-name">{{ p.project_name }}</span>
            <span class="score-value" :class="getScoreClass(p.latest_score)">{{ p.latest_score ?? '-' }}</span>
          </div>
          <van-progress :percentage="p.latest_score || 0" :stroke-width="6" :show-pivot="false"
            :color="getProgressColor(p.latest_score)" track-color="#F1F5F9" />
        </div>
      </div>

      <!-- 问题按模块分布 -->
      <div class="section-card">
        <div class="section-title">问题按模块分布</div>
        <div v-if="issueByModule.length === 0" class="section-empty">暂无数据</div>
        <div class="module-grid">
          <div v-for="m in issueByModule" :key="m.module_name" class="module-chip clickable" @click="openIssueSheet(m.module_name)">
            <span class="module-chip-name">{{ m.module_name }}</span>
            <span class="module-chip-count">{{ m.count }}</span>
          </div>
        </div>
      </div>

      <!-- 整改完成率 -->
      <div class="section-card">
        <div class="section-title">各项目整改完成率</div>
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
            <span class="module-score-val" :class="getScoreClass(score)">{{ score != null ? score + '%' : '-' }}</span>
          </div>
          <van-progress :percentage="score || 0" :stroke-width="6" :show-pivot="false"
            :color="getProgressColor(score)" track-color="#F1F5F9" />
        </div>
        <div v-if="!selectedProject.modules || Object.keys(selectedProject.modules || {}).length === 0" class="popup-empty">暂无评分数据</div>
      </div>
    </van-action-sheet>

    <van-tabbar v-model="activeTab" route>
      <van-tabbar-item icon="chart-trending-o" to="/dashboard">概览</van-tabbar-item>
      <van-tabbar-item icon="home-o" to="/tasks">任务</van-tabbar-item>
      <van-tabbar-item icon="todo-list-o" to="/reports">报告</van-tabbar-item>
      <van-tabbar-item icon="shield-o" to="/rectification">整改</van-tabbar-item>
      <van-tabbar-item icon="bar-chart-o" to="/analysis-mobile">分析</van-tabbar-item>
    </van-tabbar>

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
import echarts from '../../utils/echarts'
import { getDashboardStats } from '../../api/stats'
import { getNotifications, getUnreadCount, markAsRead, markAllAsRead } from '../../api/notification'
import { getAllRectifications } from '../../api/rectification'

const router = useRouter()

const loading = ref(true)
const summary = ref({})
const projectScores = ref([])
const issueByModule = ref([])
const rectStats = ref([])
const rectChartRef = ref(null)
let rectChart = null
const coverageDetail = ref({ checked_projects: [], unchecked_projects: [] })
const activeTab = ref(0)
const showUser = ref(false)
const showNotifications = ref(false)
const notifications = ref([])
const unreadCount = ref(0)

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
      backgroundColor: 'rgba(255, 255, 255, 0.96)',
      borderColor: '#E2E8F0',
      borderWidth: 1,
      textStyle: { color: '#18181b', fontSize: 13 },
      extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-radius: 8px;',
      formatter: (params) => {
        const name = params[0].name
        const approved = params.find(p => p.seriesName === '已整改')?.value || 0
        const pending = params.find(p => p.seriesName === '未整改')?.value || 0
        const total = approved + pending
        const rate = total > 0 ? ((approved / total) * 100).toFixed(1) : 0
        return `<div style="font-weight:600;margin-bottom:4px">${name}</div>` +
          `<div>已整改：<span style="color:#16a34a;font-weight:600">${approved}</span></div>` +
          `<div>未整改：<span style="color:#dc2626;font-weight:600">${pending}</span></div>` +
          `<div style="margin-top:4px;border-top:1px solid #eee;padding-top:4px">完成率：<b>${rate}%</b></div>`
      }
    },
    legend: {
      data: ['已整改', '未整改'],
      top: 0,
      right: 10,
      textStyle: { fontSize: 11, color: '#52525b' },
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 12
    },
    grid: { left: 80, right: 30, top: 30, bottom: 10 },
    xAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f4f4f5', type: 'dashed' } },
      axisLabel: { color: '#94A3B8', fontSize: 10 }
    },
    yAxis: {
      type: 'category',
      data: data.map(i => i.project_name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { fontSize: 11, color: '#52525b', width: 70, overflow: 'truncate' }
    },
    series: [
      {
        name: '已整改',
        type: 'bar',
        stack: 'total',
        data: data.map(i => i.approved),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#16a34a' },
            { offset: 1, color: '#34D399' }
          ])
        },
        barWidth: 14,
      },
      {
        name: '未整改',
        type: 'bar',
        stack: 'total',
        data: data.map(i => i.pending),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#F87171' },
            { offset: 1, color: '#FCA5A5' }
          ]),
          borderRadius: [0, 4, 4, 0]
        },
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

const getScoreClass = (score) => {
  if (score >= 90) return 'score-good'
  if (score >= 70) return 'score-warn'
  return 'score-bad'
}

const getProgressColor = (score) => {
  if (score >= 90) return '#059669'
  if (score >= 70) return '#d97706'
  return '#dc2626'
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
  background: #f5f7fa;
  padding-bottom: 60px;
  width: 100%;
  max-width: 100vw;
  box-sizing: border-box;
  overflow-x: hidden;       /* 兜底：防止图表/长文本撑出横向滚动条；统计卡片由 minmax(0,1fr) 保证在屏内，不会被裁 */
}

.loading-center {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 50vh;
}

/* 统计卡片（移动端独立命名，避免命中全局 design-upgrade.css 的 .stat-grid repeat(3,1fr)!important）*/
.m-stat-grid {
  display: grid;
  /* 严格2列：minmax(0,1fr) 允许卡片收缩到内容以下，防止横向溢出；
     配合 .stat-card 的 min-width:0 才能真正生效 */
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 10px;
  padding: 12px;
}

/* 不再让最后一张卡片占整行：保证每行严格只有2张卡片（第5张单独在最后一行左侧） */

.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 14px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  min-width: 0;   /* 关键：grid子元素默认min-width:auto会撑大轨道，必须置0才能让卡片收缩到列宽内 */
}

.stat-icon {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-body {
  flex: 1;
  min-width: 0;
}

.stat-num {
  font-size: 22px;
  font-weight: 700;
  color: #1a1d26;
  line-height: 1.2;
  min-width: 0;
  overflow-wrap: break-word;
}

.stat-unit {
  font-size: 13px;
  font-weight: 400;
  color: #9ba3af;
}

.stat-label {
  font-size: 12px;
  color: #9ba3af;
  margin-top: 2px;
}

.stat-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.stat-tag {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  white-space: nowrap;
}

.tag-warn { background: #FEF3C7; color: #92400E; }
.tag-blue { background: #DBEAFE; color: #1E40AF; }
.tag-green { background: #D1FAE5; color: #065F46; }
.tag-red { background: #FEE2E2; color: #991B1B; }
.tag-orange { background: #FFEDD5; color: #9A3412; }
.tag-gray { background: #F1F5F9; color: #475569; }

/* 区块卡片 */
.section-card {
  background: #fff;
  border-radius: 12px;
  margin: 0 12px 12px;
  padding: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  overflow: hidden;         /* 图表/模块标签等内部内容不溢出卡片 */
  min-width: 0;             /* 允许在flex/grid中收缩 */
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1d26;
  margin-bottom: 12px;
}

.section-empty {
  font-size: 13px;
  color: #9ba3af;
  text-align: center;
  padding: 16px 0;
}

/* 得分行 */
.score-row {
  margin-bottom: 14px;
}

.score-row:last-child {
  margin-bottom: 0;
}

.score-row-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  min-width: 0;             /* 允许score-name收缩并触发ellipsis */
}

.score-name {
  font-size: 14px;
  font-weight: 500;
  color: #1a1d26;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.score-value {
  font-size: 15px;
  font-weight: 700;
  font-family: "SF Mono", Consolas, monospace;
}

.score-good { color: #059669; }
.score-warn { color: #d97706; }
.score-bad { color: #dc2626; }

/* 模块分布网格 */
.module-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.module-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  padding: 6px 12px;
}

.module-chip-name {
  font-size: 13px;
  color: #334155;
  max-width: 7em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.module-chip-count {
  font-size: 14px;
  font-weight: 700;
  color: #2563eb;
}

/* 通知面板 */
.notification-page {
  height: 100vh;
  background: #f5f7fa;
}

.notification-empty {
  padding: 60px 0;
}

.notification-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  background: white;
  border-bottom: 1px solid #f1f5f9;
}

.notification-item.unread {
  background: #f8fbff;
}

.notification-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.notification-icon.icon-success { background: #ecfdf5; color: #059669; }
.notification-icon.icon-danger { background: #fef2f2; color: #dc2626; }
.notification-icon.icon-default { background: #f5f7fa; color: #64748b; }

.notification-body {
  flex: 1;
  min-width: 0;
}

.notification-title {
  font-size: 15px;
  font-weight: 500;
  color: #1a1d26;
  margin-bottom: 4px;
}

.notification-content {
  font-size: 13px;
  color: #64748b;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.notification-time {
  font-size: 12px;
  color: #9ba3af;
  margin-top: 4px;
}

.clickable { cursor: pointer; transition: transform 0.1s; }
.clickable:active { transform: scale(0.97); opacity: 0.85; }
.stat-card.clickable { position: relative; }
.stat-card.clickable::after {
  content: ''; position: absolute; right: 10px; bottom: 10px;
  width: 0; height: 0; border-left: 5px solid transparent; border-right: 5px solid transparent;
  border-top: 5px solid #c0c4cc;
}
.module-chip.clickable { position: relative; }

/* Popup styles */
.popup-scroll { padding: 12px 16px; max-height: 60vh; overflow-y: auto; -webkit-overflow-scrolling: touch; }
.popup-title { font-size: 16px; font-weight: 600; text-align: center; margin-bottom: 12px; color: #1f2937; }
.popup-loading { display: flex; justify-content: center; padding: 40px 0; }
.popup-empty { text-align: center; color: #9ca3af; padding: 40px 0; font-size: 14px; }
.popup-empty-sm { text-align: center; color: #9ca3af; padding: 12px 0; font-size: 13px; }
.coverage-section { margin-bottom: 12px; }
.coverage-label { font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 6px; padding-left: 4px; }
.module-score-row { margin-bottom: 12px; }
.module-score-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.module-score-name { font-size: 13px; color: #374151; }
.module-score-val { font-size: 14px; font-weight: 600; }
.module-score-val.score-good { color: #059669; }
.module-score-val.score-warn { color: #d97706; }
.module-score-val.score-bad { color: #dc2626; }

/* Issue / Rectification items */
.issue-item { padding: 10px 0; border-bottom: 1px solid #f1f5f9; }
.issue-item:last-child { border-bottom: none; }
.issue-item-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.issue-item-title { font-size: 14px; font-weight: 500; color: #1f2937; flex: 1; margin-right: 8px; }
.issue-item-check { font-size: 13px; color: #64748b; margin-bottom: 2px; }
.issue-item-desc { font-size: 12px; color: #94a3b8; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
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
