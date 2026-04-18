import { defineStore } from 'pinia'
import { login as loginApi, getMe } from '../api/auth'
import router from '../router'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || '{}'),
    activeProjectId: localStorage.getItem('activeProjectId')
      ? parseInt(localStorage.getItem('activeProjectId'))
      : null
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    isAdmin: (state) => state.user.role === 'admin',
    isInspector: (state) => state.user.role === 'inspector',
    isFieldSupervisor: (state) => state.user.role === 'field_supervisor',
    isProjectStaff: (state) => state.user.role === 'project_staff',
    canManage: (state) => ['admin', 'field_supervisor'].includes(state.user.role),
    needChangePwd: (state) => !!state.user.must_change_pwd,
    // 用户关联的所有项目列表
    projects: (state) => state.user.projects || [],
    // 是否有多个项目（需要显示切换器）
    hasMultipleProjects: (state) => (state.user.projects || []).length > 1,
    // 当前活跃项目名称
    activeProjectName(state) {
      if (!state.activeProjectId) return state.user.project_name || ''
      const p = (state.user.projects || []).find(p => p.id === state.activeProjectId)
      return p ? p.name : (state.user.project_name || '')
    }
  },

  actions: {
    _clearAllState() {
      localStorage.clear()
      this.token = ''
      this.user = {}
      this.activeProjectId = null
    },

    async login(account, password) {
      this._clearAllState()
      const res = await loginApi({ account, password })
      this.token = res.access_token
      this.user = res.user
      localStorage.setItem('token', res.access_token)
      localStorage.setItem('user', JSON.stringify(res.user))

      // 自动设置活跃项目
      if (res.user.projects && res.user.projects.length > 0) {
        this.activeProjectId = res.user.projects[0].id
        localStorage.setItem('activeProjectId', String(this.activeProjectId))
      }

      return res
    },

    async fetchUser() {
      if (!this.token) return
      try {
        const res = await getMe()
        this.user = res
        localStorage.setItem('user', JSON.stringify(res))

        // 如果还没有活跃项目，设置第一个
        if (!this.activeProjectId && res.projects && res.projects.length > 0) {
          this.activeProjectId = res.projects[0].id
          localStorage.setItem('activeProjectId', String(this.activeProjectId))
        }
      } catch (e) {
        this.logout()
      }
    },

    setActiveProject(projectId) {
      this.activeProjectId = projectId
      localStorage.setItem('activeProjectId', String(projectId))
      // 刷新当前页面以加载新项目的数据
      router.go(0)
    },

    logout() {
      this._clearAllState()
      router.push('/login')
    }
  }
})
