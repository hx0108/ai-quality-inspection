import request from '../utils/request'
import { getAuthToken } from '../utils/authStorage'

// 开始评分
export function startScoring(taskId) {
  return request.post(`/scoring/start/${taskId}`)
}

// 获取评分状态
export function getScoringStatus(taskId) {
  return request.get(`/scoring/status/${taskId}`)
}

// 获取每个模块的检查+评分状态
export function getModuleScoringStatus(taskId) {
  return request.get(`/scoring/module-status/${taskId}`)
}

// 获取评分摘要（轻量，~1KB，秒返回）— 含总分+各模块得分
export function getScoringSummary(taskId) {
  return request.get(`/scoring/results-summary/${taskId}`)
}

// 别名：getScoringResults 也调用 summary 端点
export function getScoringResults(taskId) {
  return request.get(`/scoring/results-summary/${taskId}`)
}

// 获取单个模块的检查项详情（按需加载，展开模块时调用）
export function getModuleDetail(taskId, moduleName) {
  return request.get(`/scoring/module-detail/${taskId}/${encodeURIComponent(moduleName)}`)
}

// 修改单项评分
export function editScore(scoringId, data) {
  return request.put(`/scoring/items/${scoringId}`, data)
}

// 重新评分某个模块
export function rescoreModule(taskId, moduleName) {
  return request.put(`/scoring/modules/${taskId}/${encodeURIComponent(moduleName)}/rescore`)
}

// 导出评分结果Excel
export function exportScoringExcel(taskId) {
  const token = getAuthToken()
  const url = `/api/v1/scoring/export/${taskId}`
  return fetch(url, {
    headers: { Authorization: `Bearer ${token}` }
  }).then(res => {
    if (!res.ok) throw new Error('导出失败')
    return res.blob()
  })
}

// 评分复核：获取待复核列表
export function getAllPendingReviews(params) {
  return request.get('/scoring/review-queue', { params })
}
