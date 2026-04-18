<template>
  <el-container class="pc-layout">
    <el-aside width="220px" class="sidebar">
      <div class="logo">
        <div class="logo-icon-wrap">
          <el-icon size="20" color="#2563eb"><DataAnalysis /></el-icon>
        </div>
        <div class="logo-text">
          <span class="logo-title">品质检查系统</span>
        </div>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="transparent"
        text-color="#5c6477"
        active-text-color="#2563eb"
      >
        <el-menu-item index="/pc/dashboard">
          <el-icon><DataLine /></el-icon>
          <span>数据概览</span>
        </el-menu-item>
        <el-menu-item index="/pc/tasks">
          <el-icon><List /></el-icon>
          <span>巡检任务</span>
        </el-menu-item>
        <el-menu-item index="/pc/reports">
          <el-icon><Document /></el-icon>
          <span>品质报告</span>
        </el-menu-item>
        <el-menu-item index="/pc/rectifications">
          <el-icon><CircleCheck /></el-icon>
          <span>整改闭环</span>
        </el-menu-item>
        <el-menu-item index="/pc/analysis">
          <el-icon><TrendCharts /></el-icon>
          <span>综合分析</span>
        </el-menu-item>
        <el-menu-item index="/pc/llm-monitor">
          <el-icon><Cpu /></el-icon>
          <span>LLM监控</span>
        </el-menu-item>
        <el-menu-item v-if="authStore.isAdmin" index="/pc/settings">
          <el-icon><Setting /></el-icon>
          <span>系统配置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <span class="page-title">{{ pageTitle }}</span>
        </div>
        <div class="header-right">
          <el-dropdown v-if="authStore.hasMultipleProjects" @command="onProjectSwitch" class="project-switcher">
            <span class="project-switcher-label">
              <el-icon size="14"><OfficeBuilding /></el-icon>
              {{ authStore.activeProjectName }}
              <el-icon class="el-icon--right" size="10"><ArrowDown /></el-icon>
            </span>
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
          <el-dropdown @command="onCommand">
            <span class="user-info">
              <span class="user-avatar">{{ (user.real_name || user.username || '?')[0] }}</span>
              <span class="user-name">{{ user.real_name || user.username }}</span>
              <el-icon class="el-icon--right" size="12"><ArrowDown /></el-icon>
            </span>
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
      </el-header>

      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
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
    '/pc/tasks': '巡检任务',
    '/pc/reports': '品质报告',
    '/pc/analysis': '综合分析',
    '/pc/rectifications': '整改闭环',
    '/pc/llm-monitor': 'LLM监控',
    '/pc/settings': '系统配置'
  }
  return map[route.path] || '管理后台'
})

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
/* ===== 全局布局 ===== */
.pc-layout {
  height: 100vh;
  font-family: system-ui, -apple-system, "SF Pro Text", "PingFang SC", "Microsoft YaHei", sans-serif;
}

/* ===== 侧边栏 ===== */
.sidebar {
  background: #ffffff;
  overflow-y: auto;
  position: relative;
  border-right: 1px solid #e5e7eb;
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 12px;
  border-bottom: 1px solid #e5e7eb;
}

.logo-icon-wrap {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(37, 99, 235, 0.08);
  border-radius: 8px;
}

.logo-title {
  font-size: 15px;
  font-weight: 700;
  color: #1a1d26;
  letter-spacing: 0.5px;
}

/* 侧边栏菜单 */
.sidebar :deep(.el-menu) {
  border-right: none;
  padding: 8px 12px;
}

.sidebar :deep(.el-menu-item) {
  border-radius: 6px;
  margin-bottom: 2px;
  height: 44px;
  line-height: 44px;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.15s;
  position: relative;
}

.sidebar :deep(.el-menu-item:hover) {
  background-color: #f5f7fa !important;
  color: #1a1d26 !important;
}

.sidebar :deep(.el-menu-item.is-active) {
  background: #eff6ff !important;
  color: #2563eb !important;
}

.sidebar :deep(.el-menu-item.is-active::before) {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  background: #2563eb;
  border-radius: 0 2px 2px 0;
}

/* ===== 顶部导航栏 ===== */
.header {
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 56px;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1d26;
  position: relative;
  padding-left: 14px;
}

.page-title::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 16px;
  background: #2563eb;
  border-radius: 2px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.project-switcher {
  cursor: pointer;
}

.project-switcher-label {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: #eff6ff;
  border-radius: 8px;
  font-size: 13px;
  color: #2563eb;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.project-switcher-label:hover {
  background: #dbeafe;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 10px;
  border-radius: 6px;
  transition: background 0.15s;
}

.user-info:hover {
  background: #f5f7fa;
}

.user-avatar {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #eff6ff;
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
}

.user-name {
  color: #5c6477;
  font-size: 13px;
}

.user-info .el-icon {
  color: #9ba3af;
}

/* ===== 主内容区 ===== */
.main-content {
  background: #f5f7fa;
  padding: 20px;
  overflow-y: auto;
}
</style>
