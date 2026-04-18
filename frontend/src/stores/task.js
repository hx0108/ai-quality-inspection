import { defineStore } from 'pinia'
import { getMyTasks, getTaskDetail, getProjects, createTask, assignModule } from '../api/tasks'

export const useTaskStore = defineStore('task', {
  state: () => ({
    tasks: [],
    currentTask: null,
    projects: []
  }),

  actions: {
    async fetchProjects() {
      const res = await getProjects()
      this.projects = res.items || []
      return this.projects
    },

    async fetchMyTasks() {
      const res = await getMyTasks()
      this.tasks = res.items || []
      return this.tasks
    },

    async fetchTaskDetail(taskId) {
      const res = await getTaskDetail(taskId)
      this.currentTask = res
      return res
    },

    async createTask(data) {
      return await createTask(data)
    },

    async assignModule(taskId, data) {
      return await assignModule(taskId, data)
    }
  }
})
