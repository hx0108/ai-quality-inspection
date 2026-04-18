import { createRouter, createWebHistory } from 'vue-router'
import { closeToast } from 'vant'
import { forceOverlayCleanup } from '../utils/overlayGuard'

const routes = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/mobile/Login.vue')
  },
  {
    path: '/change-password',
    name: 'ChangePassword',
    component: () => import('../views/mobile/ChangePassword.vue'),
    meta: { requiresAuth: true }
  },

  // ==================== 移动端路由 ====================
  {
    path: '/dashboard',
    name: 'MobileDashboard',
    component: () => import('../views/mobile/MobileDashboard.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/tasks',
    name: 'TaskList',
    component: () => import('../views/mobile/TaskList.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/task/:taskId',
    name: 'TaskDetail',
    component: () => import('../views/mobile/TaskDetail.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/inspection/:recordId',
    name: 'Inspection',
    component: () => import('../views/mobile/Inspection.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/inspection-card/:recordId',
    name: 'InspectionCard',
    component: () => import('../views/mobile/InspectionCard.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/scoring/:taskId',
    name: 'Scoring',
    component: () => import('../views/mobile/Scoring.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/reports',
    name: 'ReportList',
    component: () => import('../views/mobile/ReportList.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/report/:taskId',
    name: 'Report',
    component: () => import('../views/mobile/Report.vue'),
    meta: { requiresAuth: true }
  },

  // ==================== 移动端整改路由 ====================
  {
    path: '/rectification',
    name: 'RectificationList',
    component: () => import('../views/mobile/Rectification.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/analysis-mobile',
    name: 'MobileAnalysis',
    component: () => import('../views/mobile/MobileAnalysis.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/rectification/:id',
    name: 'RectificationSubmit',
    component: () => import('../views/mobile/RectificationSubmit.vue'),
    meta: { requiresAuth: true }
  },

  // ==================== PC 端路由 ====================
  {
    path: '/pc',
    redirect: '/pc/dashboard',
    component: () => import('../views/pc/PcLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: 'tasks',
        name: 'PcTasks',
        component: () => import('../views/pc/Tasks.vue'),
        meta: { requiresAuth: true, title: '任务管理' }
      },
      {
        path: 'dashboard',
        name: 'PcDashboard',
        component: () => import('../views/pc/Dashboard.vue'),
        meta: { requiresAuth: true, title: '数据概览' }
      },
      {
        path: 'reports',
        name: 'PcReports',
        component: () => import('../views/pc/Report.vue'),
        meta: { requiresAuth: true, title: '报告管理' }
      },
      {
        path: 'settings',
        name: 'PcSettings',
        component: () => import('../views/pc/Settings.vue'),
        meta: { requiresAuth: true, title: '系统设置', roles: ['admin'] }
      },
      {
        path: 'analysis',
        name: 'PcAnalysis',
        component: () => import('../views/pc/Analysis.vue'),
        meta: { requiresAuth: true, title: '综合分析' }
      },
      {
        path: 'rectifications',
        name: 'PcRectifications',
        component: () => import('../views/pc/Rectifications.vue'),
        meta: { requiresAuth: true, title: '整改管理' }
      },
      {
        path: 'llm-monitor',
        name: 'PcLlmMonitor',
        component: () => import('../views/pc/LlmMonitor.vue'),
        meta: { requiresAuth: true, title: 'LLM监控' }
      },
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  // 使用 Vant API 正确关闭弹窗
  closeToast()
  // 强制清理所有遮罩层残留
  forceOverlayCleanup()
  // Element Plus 遮罩清理（PC端）
  document.querySelectorAll('.el-loading-mask, .el-overlay').forEach(el => el.remove())

  const token = localStorage.getItem('token')

  // 前端检查 JWT 过期：解码 payload 中的 exp 字段
  if (token && isTokenExpired(token)) {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('auth_state')
    next('/login')
    return
  }

  const user = JSON.parse(localStorage.getItem('user') || '{}')

  // 登录页始终可访问
  if (to.path === '/login' || to.path === '/') {
    if (token && !user.must_change_pwd) {
      // 已登录且无需改密，跳转首页
      next(isMobile() ? '/dashboard' : '/pc/dashboard')
    } else {
      next()
    }
  } else if (to.path === '/change-password') {
    // 改密页需要 token
    if (!token) {
      next('/login')
    } else {
      next()
    }
  } else if (!token) {
    next('/login')
  } else if (user.must_change_pwd) {
    next('/change-password')
  } else if (to.meta.roles && !to.meta.roles.includes(user.role)) {
    next(isMobile() ? '/dashboard' : '/pc/tasks')
  } else {
    next()
  }
})

/**
 * 检查 JWT token 是否已过期
 * 解码 payload 中的 exp 字段（秒级时间戳），提前 60 秒判定过期
 */
function isTokenExpired(token) {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return true
    const payload = JSON.parse(atob(parts[1]))
    if (!payload.exp) return false // 无 exp 字段不强制过期
    // 提前 60 秒判定，避免请求途中过期
    return Date.now() >= (payload.exp - 60) * 1000
  } catch {
    return true // 解码失败视为过期
  }
}

function isMobile() {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
    || window.innerWidth < 768
}

export default router
