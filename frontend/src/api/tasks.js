import request from '../utils/request'

// 获取项目列表
export function getProjects() {
  return request.get('/tasks/projects')
}

// 创建检查任务
export function createTask(data) {
  return request.post('/tasks', data)
}

// 获取任务列表
export function getTasks(params) {
  return request.get('/tasks', { params })
}

// 获取任务详情
export function getTaskDetail(taskId) {
  return request.get(`/tasks/${taskId}`)
}

// 分配模块
export function assignModule(taskId, data) {
  return request.post(`/tasks/${taskId}/assign`, data)
}

// 获取我的任务
export function getMyTasks() {
  return request.get('/tasks/my-tasks/list')
}

// 获取模块检查项模板
export function getModuleTemplate(moduleName, standardType = 'diecheng') {
  return request.get(`/tasks/module-template/${encodeURIComponent(moduleName)}`, {
    params: { standard_type: standardType }
  })
}

// 获取检查标准类型列表
export function getStandardTypes() {
  return request.get('/tasks/standard-types')
}

// 获取检查员列表
export function getInspectors() {
  return request.get('/auth/inspectors')
}
