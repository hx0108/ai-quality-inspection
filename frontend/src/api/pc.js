import request from '../utils/request'

// ==================== 用户管理 ====================
export function getUsers(params) {
  return request.get('/users', { params })
}

export function createUser(data) {
  return request.post('/users', data)
}

export function updateUser(userId, data) {
  return request.put(`/users/${userId}`, data)
}

export function deleteUser(userId) {
  return request.delete(`/users/${userId}`)
}

export function getUserRoles() {
  return request.get('/users/roles')
}

// ==================== 项目管理 ====================
export function getProjects(params) {
  return request.get('/projects', { params })
}

export function getAllProjects() {
  return request.get('/projects/all')
}

export function createProject(data) {
  return request.post('/projects', data)
}

export function updateProject(projectId, data) {
  return request.put(`/projects/${projectId}`, data)
}

export function deleteProject(projectId) {
  return request.delete(`/projects/${projectId}`)
}

// ==================== 任务管理 ====================
export function getTasks(params) {
  return request.get('/tasks', { params })
}

export function createTask(data) {
  return request.post('/tasks', data)
}

export function createTaskBatch(data) {
  return request.post('/tasks/batch', data)
}

export function getTaskDetail(taskId) {
  return request.get(`/tasks/${taskId}`)
}

export function getAssignments(taskId) {
  return request.get(`/tasks/${taskId}/assignments`)
}

export function assignModule(taskId, data) {
  return request.post(`/tasks/${taskId}/assign`, data)
}

export function createTaskAssignBatch(data) {
  return request.post('/tasks/assign/batch', data)
}

export function getStandardTypes() {
  return request.get('/tasks/standard-types')
}
