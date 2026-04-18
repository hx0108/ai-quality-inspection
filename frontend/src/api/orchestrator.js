import request from '../utils/request'

/**
 * Orchestrator API - 一键执行完整流程
 * 串联 Agent 2 → Agent 3 → Agent 4
 */

// 一键执行完整流程
export function runFullPipeline(taskId) {
  return request.post('/orchestrator/run', { task_id: taskId })
}

// 获取流水线状态
export function getPipelineStatus(taskId) {
  return request.get(`/orchestrator/status/${taskId}`)
}

// 仅执行评分
export function runScoringOnly(taskId) {
  return request.post('/orchestrator/scoring-only', null, { params: { task_id: taskId } })
}

// 仅执行报告生成
export function runReportOnly(taskId) {
  return request.post('/orchestrator/report-only', null, { params: { task_id: taskId } })
}
