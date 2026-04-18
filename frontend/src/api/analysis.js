import request from '../utils/request'

// ==================== 综合分析 API ====================

/** 启动综合分析 */
export function startAnalysis(data) {
  return request.post('/analysis/start', data)
}

/** 查询分析进度 */
export function getAnalysisProgress(analysisId) {
  return request.get(`/analysis/${analysisId}/progress`)
}

/** 获取分析结果 */
export function getAnalysisResult(analysisId) {
  return request.get(`/analysis/${analysisId}/result`)
}

/** 获取历史分析记录 */
export function getAnalysisHistory(params) {
  return request.get('/analysis/history', { params })
}

/** 获取有报告的项目列表 */
export function getProjectsWithReports(params) {
  return request.get('/analysis/projects-with-reports', { params })
}

/** 下载分析报告文件 */
export function downloadAnalysisFile(analysisId, fileType = 'word') {
  return request.get(`/analysis/${analysisId}/download`, { params: { file_type: fileType }, responseType: 'blob' })
}

/** 删除分析记录（仅管理员） */
export function deleteAnalysis(analysisId) {
  return request.delete(`/analysis/${analysisId}`)
}
