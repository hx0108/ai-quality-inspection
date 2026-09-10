<template>
  <div class="shell">
    <!-- Sidebar -->
    <aside class="side">
      <div class="side-brand">
        <div class="side-logo">
          <svg viewBox="0 0 16 16"><path d="M2 14l4-5 3 3 5-7" /></svg>
        </div>
        <span class="side-title">智能品质检查系统</span>
      </div>
      <nav class="side-nav">
        <!-- 概览 -->
        <div class="sn-group">
          <div class="sn-item" :class="{ on: activeMenu === '/pc/dashboard' }" @click="navigate('/pc/dashboard')">
            <svg viewBox="0 0 16 16"><path d="M2 14l4-5 3 3 5-7" /></svg>
            <span>数据概览</span>
          </div>
        </div>
        <!-- 品质管理 -->
        <div class="sn-group">
          <div class="sn-label">品质管理</div>
          <div class="sn-item" :class="{ on: activeMenu === '/pc/tasks' }" @click="navigate('/pc/tasks')">
            <svg viewBox="0 0 16 16"><path d="M2 4h12M2 8h12M2 12h8" /></svg>
            <span>任务中心</span>
          </div>
          <div class="sn-item" :class="{ on: activeMenu === '/pc/scoring-management' }" @click="navigate('/pc/scoring-management')">
            <svg viewBox="0 0 16 16"><path d="M3 2l10 6-10 6V2z" /></svg>
            <span>评分复核</span>
          </div>
          <div class="sn-item" :class="{ on: activeMenu === '/pc/reports' }" @click="navigate('/pc/reports')">
            <svg viewBox="0 0 16 16"><rect x="2" y="2" width="12" height="12" rx="1" /><path d="M5 6h6M5 8.5h4M5 11h5" /></svg>
            <span>报告管理</span>
          </div>
          <div class="sn-item" :class="{ on: activeMenu === '/pc/rectifications' }" @click="navigate('/pc/rectifications')">
            <svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" /><path d="M8 5v3l2 2" /></svg>
            <span>整改跟踪</span>
          </div>
        </div>
        <!-- 数据中心 -->
        <div class="sn-group">
          <div class="sn-label">数据中心</div>
          <div class="sn-item" :class="{ on: activeMenu === '/pc/analysis' }" @click="navigate('/pc/analysis')">
            <svg viewBox="0 0 16 16"><path d="M2 14l4-5 3 3 5-7" /></svg>
            <span>分析看板</span>
          </div>
        </div>
        <!-- 智能运营 -->
        <div class="sn-group">
          <div class="sn-label">智能运营</div>
          <div class="sn-item" :class="{ on: activeMenu === '/pc/llm-monitor' }" @click="navigate('/pc/llm-monitor')">
            <svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="2" /><path d="M8 1v2.5M8 12.5V15M1 8h2.5M12.5 8H15M3.3 3.3l1.8 1.8M10.9 10.9l1.8 1.8M3.3 12.7l1.8-1.8M10.9 5.1l1.8-1.8" /></svg>
            <span>模型监控</span>
          </div>
          <div class="sn-item" :class="{ on: activeMenu === '/pc/ai-metrics' }" @click="navigate('/pc/ai-metrics')">
            <svg viewBox="0 0 16 16"><path d="M8 1l2.1 4.3 4.7.7-3.4 3.3.8 4.7L8 11.8 3.8 14l.8-4.7L1.2 6l4.7-.7z" /></svg>
            <span>效果评估</span>
          </div>
        </div>
        <!-- 系统设置 (admin only) -->
        <div v-if="authStore.isAdmin" class="sn-group sn-end">
          <div class="sn-item" :class="{ on: activeMenu === '/pc/settings' }" @click="navigate('/pc/settings')">
            <svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" /><path d="M13 8A5 5 0 018 3" /></svg>
            <span>系统设置</span>
          </div>
        </div>
      </nav>
    </aside>

    <!-- Main area -->
    <div class="main">
      <header class="top">
        <div class="top-left">
          <span class="top-crumb">{{ pageGroup }}</span>
          <span class="top-title">{{ pageTitle }}</span>
        </div>
        <div class="top-right">
          <!-- Project switcher -->
          <el-dropdown v-if="authStore.hasMultipleProjects" @command="onProjectSwitch">
            <div class="proj-chip">
              <svg viewBox="0 0 16 16"><path d="M2 4l6-2 6 2v5c0 3-6 5-6 5S2 12 2 9V4z" /></svg>
              {{ authStore.activeProjectName }}
              <svg viewBox="0 0 16 16"><path d="M4 6l4 4 4-4" /></svg>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item
                  v-for="p in authStore.projects"
                  :key="p.id"
                  :command="p.id"
                  :class="{ 'is-active': p.id === authStore.activeProjectId }"
                >
                  {{ p.name }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <!-- 通知铃铛（原型顶栏三件套） -->
          <el-popover placement="bottom-end" :width="340" trigger="click" popper-class="notify-popover" @show="loadNotifications">
            <template #reference>
              <button class="icon-btn" title="通知">
                <svg viewBox="0 0 16 16"><path d="M3.5 11.5h9c-1-1-1.5-2.2-1.5-4a3 3 0 10-6 0c0 1.8-.5 3-1.5 4z" /><path d="M6.8 13.5a1.3 1.3 0 002.4 0" /></svg>
                <span v-if="unreadCount > 0" class="bubble" />
              </button>
            </template>
            <div class="notify-panel">
              <div class="notify-head">
                <span>通知</span>
                <button v-if="notifications.length" class="notify-all" @click="onMarkAllRead">全部已读</button>
              </div>
              <div class="notify-list">
                <div v-for="n in notifications" :key="n.notification_id" class="notify-item" :class="{ unread: !n.is_read }">
                  <span class="notify-dot" />
                  <div class="notify-body">
                    <div class="notify-t">{{ n.title }}</div>
                    <div class="notify-c">{{ n.content }}</div>
                  </div>
                </div>
                <div v-if="!notifications.length" class="notify-empty">暂无通知</div>
              </div>
            </div>
          </el-popover>
          <!-- User dropdown -->
          <el-dropdown @command="onCommand">
            <div class="user-chip">
              <span class="avatar">{{ (user.real_name || user.username || 'U').slice(0, 1) }}</span>
              <b>{{ user.real_name || user.username }}</b>
              <svg viewBox="0 0 16 16"><path d="M4 6l4 4 4-4" /></svg>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-if="isMobile" command="mobile">
                  <el-icon><Iphone /></el-icon> 切换移动端
                </el-dropdown-item>
                <el-dropdown-item command="logout" divided>
                  <el-icon><SwitchButton /></el-icon> 退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <div class="cnt">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { getNotifications, getUnreadCount, markAllAsRead } from '../../api/notification'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const user = computed(() => authStore.user || {})
const isMobile = computed(() => window.innerWidth < 768)

const activeMenu = computed(() => route.path)

const pageTitle = computed(() => {
  const map = {
    '/pc/dashboard': '数据概览',
    '/pc/tasks': '任务中心',
    '/pc/scoring-management': '评分复核',
    '/pc/reports': '报告管理',
    '/pc/rectifications': '整改跟踪',
    '/pc/analysis': '分析看板',
    '/pc/llm-monitor': '模型监控',
    '/pc/ai-metrics': '效果评估',
    '/pc/settings': '系统设置'
  }
  return map[route.path] || '管理后台'
})

const pageGroup = computed(() => {
  const map = {
    '/pc/dashboard': '数据中心',
    '/pc/tasks': '品质管理',
    '/pc/scoring-management': '品质管理',
    '/pc/reports': '品质管理',
    '/pc/rectifications': '品质管理',
    '/pc/analysis': '数据中心',
    '/pc/llm-monitor': '智能运营',
    '/pc/ai-metrics': '智能运营',
    '/pc/settings': '系统'
  }
  return map[route.path] || ''
})

function navigate(path) {
  router.push(path)
}

const onCommand = (cmd) => {
  if (cmd === 'logout') {
    authStore.logout()
  } else if (cmd === 'mobile') {
    router.push('/tasks')
  }
}

const onProjectSwitch = (projectId) => {
  authStore.setActiveProject(projectId)
}

// ===== 通知铃铛 =====
const notifications = ref([])
const unreadCount = ref(0)

const loadNotifications = async () => {
  try {
    const res = await getNotifications({ page: 1, page_size: 15 })
    notifications.value = res.items || []
  } catch (e) { /* 静默：通知属辅助功能 */ }
}

const onMarkAllRead = async () => {
  try {
    await markAllAsRead()
    notifications.value.forEach(n => { n.is_read = true })
    unreadCount.value = 0
  } catch (e) { /* ignore */ }
}

onMounted(async () => {
  try {
    const res = await getUnreadCount()
    unreadCount.value = res.unread_count || 0
  } catch (e) { /* ignore */ }
})
</script>

<style scoped>
/* ===== Shell ===== */
.shell {
  display: flex;
  height: 100vh;
  font-family: var(--sans);
}

/* ===== Sidebar（深色） ===== */
.side {
  width: 216px;
  background: var(--side-bg);
  border-right: 1px solid var(--side-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.side-brand {
  height: 52px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 9px;
  border-bottom: 1px solid var(--side-border);
  flex-shrink: 0;
}

.side-logo {
  width: 26px;
  height: 26px;
  background: linear-gradient(135deg, #2bb8aa 0%, #0c7168 100%);
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.14);
  flex-shrink: 0;
}

.side-logo svg {
  width: 15px;
  height: 15px;
  stroke: #fff;
  fill: none;
  stroke-width: 2;
}

.side-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--side-text-strong);
  letter-spacing: 0.2px;
}

.side-nav {
  flex: 1;
  padding: 10px 10px 16px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.side-nav::-webkit-scrollbar { width: 5px; }
.side-nav::-webkit-scrollbar-thumb { background: #2c2c36; border-radius: 3px; }

.sn-group {
  margin-bottom: 4px;
}

.sn-label {
  font-size: 10.5px;
  font-weight: 600;
  color: #5d5d6a;
  padding: 14px 10px 5px;
  letter-spacing: 0.8px;
}

.sn-end {
  margin-top: auto;
  border-top: 1px solid var(--side-border);
  padding-top: 8px;
}

.sn-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 9px;
  height: 32px;
  padding: 0 10px;
  border-radius: var(--r);
  font-size: 13px;
  font-weight: 500;
  color: var(--side-text);
  cursor: pointer;
  transition: background 0.12s var(--ease), color 0.12s var(--ease);
  margin-bottom: 1px;
}

.sn-item:hover {
  background: var(--side-hover);
  color: var(--side-text-strong);
}

.sn-item.on {
  color: #c8ece7;
  font-weight: 600;
  background: var(--side-active-bg);
}

.sn-item.on::before {
  content: '';
  position: absolute;
  left: -10px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 16px;
  border-radius: 0 2px 2px 0;
  background: var(--side-active-line);
}

.sn-item svg {
  width: 15px;
  height: 15px;
  stroke: currentColor;
  fill: none;
  stroke-width: 1.7;
  flex-shrink: 0;
  opacity: 0.75;
}

.sn-item.on svg {
  opacity: 1;
}

.sn-badge {
  margin-left: auto;
  font-size: 10px;
  font-weight: 700;
  font-family: var(--mono);
  padding: 0 5px;
  height: 15px;
  line-height: 15px;
  border-radius: 8px;
  background: var(--err);
  color: #fff;
}

/* ===== Main area ===== */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ===== Top header ===== */
.top {
  height: 52px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--ink-200);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
}

.top-left {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.top-crumb {
  font-size: 12px;
  color: var(--ink-400);
}

.top-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink-900);
}

.top-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.proj-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 10px;
  border: 1px solid var(--ink-200);
  border-radius: var(--r);
  background: var(--bg-card);
  font-size: 12.5px;
  font-weight: 600;
  color: var(--ink-800);
  cursor: pointer;
  transition: border-color 0.12s, background 0.12s;
}

.proj-chip:hover {
  border-color: var(--ink-300);
  background: var(--bg-hover);
}

.proj-chip svg {
  width: 12px;
  height: 12px;
  stroke: currentColor;
  fill: none;
  stroke-width: 2;
}

.icon-btn {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: var(--r);
  background: transparent;
  color: var(--ink-600);
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
  position: relative;
}
.icon-btn:hover { background: var(--bg-hover); color: var(--ink-900); }
.icon-btn svg { width: 16px; height: 16px; stroke: currentColor; fill: none; stroke-width: 1.7; }
.icon-btn .bubble {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--err);
  border: 1.5px solid var(--bg-card);
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 7px;
  height: 34px;
  padding: 0 10px 0 4px;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.12s;
}

.user-chip:hover {
  background: var(--bg-hover);
}

.user-chip .avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--blue-bg);
  color: var(--brand-ink);
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.user-chip b {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--ink-800);
}

.user-chip svg {
  width: 12px;
  height: 12px;
  stroke: currentColor;
  fill: none;
  stroke-width: 2;
}

/* ===== Content area ===== */
.cnt {
  flex: 1;
  background: var(--bg);
  padding: 22px 24px 32px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--ink-200) transparent;
}

/* 原型：内容限宽居中 */
.cnt > * {
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
}

.cnt::-webkit-scrollbar {
  width: 6px;
}

.cnt::-webkit-scrollbar-thumb {
  background: var(--ink-200);
  border-radius: 3px;
}

/* ===== 通知面板（非 scoped 不生效，此处经 el-popover 挂 body，用 :global 语义） ===== */
</style>

<style>
/* 通知面板（popover 挂在 body 下，需非 scoped） */
.notify-popover {
  padding: 0 !important;
  border-radius: var(--r-lg) !important;
  border: 1px solid var(--ink-200) !important;
  box-shadow: var(--shadow-overlay) !important;
}
.notify-panel { font-family: var(--sans); }
.notify-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 11px 14px;
  border-bottom: 1px solid var(--ink-100);
  font-size: 13.5px;
  font-weight: 700;
  color: var(--ink-900);
}
.notify-all {
  border: none;
  background: none;
  font-size: 12px;
  color: var(--blue);
  cursor: pointer;
  font-family: var(--sans);
  font-weight: 600;
}
.notify-list { max-height: 360px; overflow-y: auto; }
.notify-item {
  display: flex;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--ink-100);
}
.notify-item:last-child { border-bottom: none; }
.notify-item.unread .notify-dot { background: var(--err); }
.notify-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--ink-300);
  margin-top: 6px;
  flex-shrink: 0;
}
.notify-body { flex: 1; min-width: 0; }
.notify-t { font-size: 13px; font-weight: 600; color: var(--ink-900); }
.notify-c {
  font-size: 12px;
  color: var(--ink-500);
  margin-top: 2px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.notify-empty { text-align: center; color: var(--ink-400); font-size: 13px; padding: 36px 0; }
</style>
