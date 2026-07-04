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
          <!-- User dropdown -->
          <el-dropdown @command="onCommand">
            <div class="user-chip">
              <svg viewBox="0 0 16 16" style="width:14px;height:14px"><circle cx="8" cy="5" r="3.5" /><path d="M1 15c0-3.9 3.1-7 7-7s7 3.1 7 7" /></svg>
              {{ user.real_name || user.username }}
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
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'

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
</script>

<style scoped>
/* ===== Shell ===== */
.shell {
  display: flex;
  height: 100vh;
  font-family: var(--sans);
}

/* ===== Sidebar ===== */
.side {
  width: 220px;
  background: var(--bg-card);
  border-right: 1px solid var(--ink-100);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.side-brand {
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 10px;
  border-bottom: 1px solid var(--ink-100);
}

.side-logo {
  width: 28px;
  height: 28px;
  background: var(--blue);
  border-radius: var(--r-sm);
  display: flex;
  align-items: center;
  justify-content: center;
}

.side-logo svg {
  width: 18px;
  height: 18px;
  stroke: #fff;
  fill: none;
  stroke-width: 2;
}

.side-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink-900);
  letter-spacing: -0.2px;
}

.side-nav {
  flex: 1;
  padding: 8px 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.sn-group {
  margin-bottom: 4px;
}

.sn-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--ink-400);
  padding: 10px 20px 4px;
  letter-spacing: 0.5px;
}

.sn-end {
  margin-top: auto;
  border-top: 1px solid var(--ink-100);
  padding-top: 8px;
}

.sn-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  font-size: 14px;
  font-weight: 500;
  color: #5c6477;
  cursor: pointer;
  transition: all 0.12s var(--ease);
}

.sn-item:hover {
  background: var(--bg-muted);
  color: var(--ink-900);
}

.sn-item.on {
  color: var(--blue);
  font-weight: 600;
  background: var(--blue-bg);
}

.sn-item.on::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 18px;
  background: var(--blue);
  border-radius: 2px;
}

.sn-item svg {
  width: 16px;
  height: 16px;
  stroke: currentColor;
  fill: none;
  stroke-width: 1.8;
  flex-shrink: 0;
  opacity: 0.6;
}

.sn-item.on svg {
  opacity: 1;
}

.sn-badge {
  margin-left: auto;
  font-size: 10px;
  font-weight: 700;
  font-family: var(--mono);
  padding: 1px 6px;
  border-radius: 3px;
  background: var(--err-bg);
  color: var(--err);
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
  height: 56px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--ink-100);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
}

.top-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.top-title {
  font-size: 16px;
  font-weight: 700;
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
  gap: 4px;
  padding: 5px 12px;
  border-radius: var(--r);
  font-size: 13px;
  font-weight: 600;
  color: var(--blue);
  background: var(--blue-bg);
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s;
  border: 1px solid transparent;
}

.proj-chip:hover {
  border-color: var(--blue);
}

.proj-chip svg {
  width: 12px;
  height: 12px;
  stroke: currentColor;
  fill: none;
  stroke-width: 2;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: var(--r);
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-600);
  cursor: pointer;
  transition: all 0.12s;
}

.user-chip:hover {
  background: var(--bg-muted);
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
  padding: 20px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--ink-200) transparent;
}

.cnt::-webkit-scrollbar {
  width: 6px;
}

.cnt::-webkit-scrollbar-thumb {
  background: var(--ink-200);
  border-radius: 3px;
}
</style>
