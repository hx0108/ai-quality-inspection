import request from '../utils/request'

// 获取待整改列表
export function getPendingRectifications() {
  return request.get('/rectifications/pending')
}

// 获取任务下所有整改记录
export function getTaskRectifications(taskId) {
  return request.get(`/rectifications/task/${taskId}`)
}

// 获取所有整改记录（支持筛选）
export function getAllRectifications({ statusFilter, projectName, moduleName, keyword } = {}) {
  const params = {}
  if (statusFilter) params.status_filter = statusFilter
  if (projectName) params.project_name = projectName
  if (moduleName) params.module_name = moduleName
  if (keyword) params.keyword = keyword
  return request.get('/rectifications/all', { params })
}

// 获取整改详情
export function getRectificationDetail(rectificationId) {
  return request.get(`/rectifications/${rectificationId}`)
}

// 提交整改（触发AI核查）
export function submitRectification(rectificationId, data) {
  return request.post(`/rectifications/${rectificationId}/submit`, data)
}

// 上传整改照片（含水印元数据）
export function uploadRectificationPhoto(rectificationId, file, metadata = {}) {
  const formData = new FormData()
  formData.append('file', file)
  if (metadata && Object.keys(metadata).length > 0) {
    formData.append('metadata', JSON.stringify(metadata))
  }
  return request.post(`/rectifications/${rectificationId}/photos`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 删除整改照片
export function deleteRectificationPhoto(rectificationId, photoId) {
  return request.delete(`/rectifications/${rectificationId}/photos/${photoId}`)
}

// 管理员审核整改
export function reviewRectification(rectificationId, data) {
  return request.put(`/rectifications/${rectificationId}/review`, data)
}

// 重新AI核查
export function recheckRectification(rectificationId) {
  return request.post(`/rectifications/${rectificationId}/recheck`)
}

// 项目人员申诉
export function appealRectification(rectificationId, data) {
  return request.post(`/rectifications/${rectificationId}/appeal`, data)
}

// 导出整改记录Excel
export function exportRectificationsExcel({ statusFilter, projectName, moduleName, keyword } = {}) {
  const params = {}
  if (statusFilter) params.status_filter = statusFilter
  if (projectName) params.project_name = projectName
  if (moduleName) params.module_name = moduleName
  if (keyword) params.keyword = keyword
  return request.get('/rectifications/export/excel', { params, responseType: 'blob' })
}
