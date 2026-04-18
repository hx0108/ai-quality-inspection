import request from '../utils/request'

// 创建检查记录
export function createRecord(data) {
  return request.post('/records', data)
}

// 获取检查记录详情
export function getRecordDetail(recordId) {
  return request.get(`/records/${recordId}`)
}

// 记录问题
export function createIssue(recordId, data) {
  return request.post(`/records/${recordId}/issues`, data)
}

// 上传照片（含水印元数据）
export function uploadPhoto(recordId, issueId, file, metadata = {}) {
  const formData = new FormData()
  formData.append('file', file)
  // 如果有水印元数据，序列化为 JSON 字符串
  if (metadata && Object.keys(metadata).length > 0) {
    formData.append('metadata', JSON.stringify(metadata))
  }
  return request.post(`/records/${recordId}/issues/${issueId}/photos`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 更新检查项状态
export function updateItemStatus(recordId, itemId, data) {
  return request.put(`/records/${recordId}/items/${itemId}`, data)
}

// 批量更新检查项状态
export function batchUpdateItems(recordId, data) {
  return request.put(`/records/${recordId}/items/batch`, data)
}

// 更新问题描述
export function updateIssue(recordId, issueId, data) {
  return request.put(`/records/${recordId}/issues/${issueId}`, data)
}

// 删除问题（含照片）
export function deleteIssue(recordId, issueId) {
  return request.delete(`/records/${recordId}/issues/${issueId}`)
}

// 删除单张照片
export function deletePhoto(recordId, issueId, photoId) {
  return request.delete(`/records/${recordId}/issues/${issueId}/photos/${photoId}`)
}

// 完成检查
export function completeRecord(recordId) {
  return request.put(`/records/${recordId}/complete`)
}

// 退回模块（管理员）
export function recallModule(recordId) {
  return request.put(`/records/${recordId}/recall`)
}
