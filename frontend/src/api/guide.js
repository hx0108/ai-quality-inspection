import request from '../utils/request'

// 获取模块检查重点关注项
export function getFocusItems(projectId, moduleName) {
  return request.get(`/guide/focus/${projectId}/${encodeURIComponent(moduleName)}`)
}

// 获取项目所有模块检查概况
export function getProjectModules(projectId) {
  return request.get(`/guide/project-modules/${projectId}`)
}

// 搜索相似历史案例
export function searchSimilarCases(data) {
  return request.post('/guide/similar-cases', data)
}

// 获取拍照建议
export function getPhotoTips(moduleName, itemId) {
  return request.get(`/guide/photo-tips/${encodeURIComponent(moduleName)}/${encodeURIComponent(itemId)}`)
}
